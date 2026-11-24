import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
import unittest
from uuid import uuid4
import xml.etree.ElementTree as ET

import psycopg

from support import connect, delegate


ROOT = Path(__file__).resolve().parents[1]
# Dossier de ce harnais : évite de coder son nom en dur dans les chemins
BENCH = Path(__file__).resolve().parent
CHANGELOG = BENCH / "sql/changelog.xml"
FIXTURE = BENCH / "sql/fixture.sql"
RLS_POLICY = ROOT / "ADAM/4_INSERT/INSERT-RLS-POLICY.sql"


def sql_files(changelog: Path) -> list[Path]:
    files: list[Path] = []
    for node in ET.parse(changelog).getroot():
        if node.tag.endswith("include"):
            files.extend(sql_files((changelog.parent / node.attrib["file"]).resolve()))
        elif node.tag.endswith("changeSet"):
            files.extend(
                (changelog.parent / child.attrib["path"]).resolve()
                for child in node if child.tag.endswith("sqlFile")
            )
    return files


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed: list[str] = []

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.passed.append(test.id())


def tests(pattern: str) -> dict:
    suite = unittest.defaultTestLoader.discover(str(BENCH), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(suite)
    return {
        "exit_code": 0 if result.wasSuccessful() else 1,
        "run": result.testsRun,
        "passed": result.passed,
        "failures": [{"test": test.id(), "traceback": trace} for test, trace in result.failures],
        "errors": [{"test": test.id(), "traceback": trace} for test, trace in result.errors],
    }


def quantile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def summarize(values: list[float], elapsed: float) -> dict:
    return {
        "samples": len(values), "p50_ms": quantile(values, .5),
        "p95_ms": quantile(values, .95), "p99_ms": quantile(values, .99),
        "wall_seconds": elapsed, "operations_per_second": len(values) / elapsed,
    }


def server_execution_ms(connection: psycopg.Connection, query: str, params: tuple) -> float:
    plan = connection.execute(
        "EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON) " + query, params
    ).fetchone()[0][0]
    if plan["Plan"]["Actual Rows"] != 1:
        raise RuntimeError("Measured SQL operation did not return exactly one row")
    return plan["Execution Time"]


def benchmark(output: Path, count: int, *, server_timing: bool = False) -> dict:
    rows: list[dict] = []
    samples: list[dict] = []
    with connect() as admin:
        # Depuis la correction A01, les attributs d'une décision proviennent de la
        # délégation enregistrée, plus de la variable de session : la profession
        # exigée par la contrainte ABAC posée plus bas doit donc être déclarée ici.
        delegate(admin, "nurse", "tenantA", {"profession": "nurse"})
        ids = ["bench-" + str(i) for i in range(count)]
        admin.execute(
            "INSERT INTO protected_records(id, tenant_id) SELECT 'bench-' || i, 'tenantA' "
            "FROM generate_series(0, %s) i", (count - 1,)
        )
        insertion: list[float] = []
        start = time.perf_counter()
        for record in ids:
            before = time.perf_counter_ns()
            query = (
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                "VALUES ('users','nurse','assigned','etapes',%s,'tenantA')"
            )
            if server_timing:
                insertion.append(server_execution_ms(admin, query + " RETURNING id", (record,)))
            else:
                admin.execute(query, (record,))
                insertion.append((time.perf_counter_ns() - before) / 1e6)
        rows.append({"operation": "seed_insert_26_tuples", "clients": 1,
                     **summarize(insertion, time.perf_counter() - start)})
        samples.extend({"operation": "seed_insert_26_tuples", "clients": 1, "ms": ms} for ms in insertion)
        admin.execute(
            """INSERT INTO permissions_attributes(permission_id, attribute)
            SELECT id, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb
            FROM permissions WHERE object_id LIKE 'bench-%' AND relation IN ('can_read','can_write')"""
        )
        dynamic = admin.execute(
            "INSERT INTO dynamic_rules(description,rule,params) VALUES "
            "('validation-benchmark','SELECT TRUE',ARRAY[]::text[]) RETURNING id"
        ).fetchone()[0]
        admin.execute(
            "INSERT INTO permissions_rules(permission_id,rule_id) "
            "SELECT id, %s FROM permissions WHERE object_id LIKE 'bench-%%' "
            "AND relation IN ('can_read','can_write')", (dynamic,)
        )
        admin.execute("ANALYZE")

    def worker(operation: str, worker_id: int) -> list[float]:
        timings: list[float] = []
        with connect(application=True) as connection:
            connection.execute(
                """SELECT set_config('app.adam.user_attributes', '{"profession":"nurse"}', false)"""
            )
            record = ids[worker_id % count]
            statements = {
                "protected_read": ("SELECT id FROM protected_records WHERE id = %s", (record,)),
                "protected_write": ("UPDATE protected_records SET value = value + 1 WHERE id = %s", (record,)),
                "permission_lookup": (
                    "SELECT EXISTS(SELECT 1 FROM permissions WHERE user_id = get_current_user_id() "
                    "AND object_id = %s AND tenant_id = get_current_tenant_id() AND relation = 'can_read')",
                    (record,),
                ),
            }
            query, params = statements[operation]
            for _ in range(20):
                cursor = connection.execute(query, params)
                if operation == "protected_write":
                    if cursor.rowcount != 1:
                        raise RuntimeError("Benchmark warm-up write was not authorized")
                else:
                    data = cursor.fetchall()
                    if not data or (operation == "permission_lookup" and data[0][0] is not True):
                        raise RuntimeError("Benchmark warm-up query was not authorized")
            for _ in range(100 if server_timing else 300):
                if server_timing:
                    measured_query = query + " RETURNING id" if operation == "protected_write" else query
                    timings.append(server_execution_ms(connection, measured_query, params))
                    continue
                before = time.perf_counter_ns()
                cursor = connection.execute(query, params)
                if operation == "protected_write":
                    if cursor.rowcount != 1:
                        raise RuntimeError("Benchmark write was not authorized")
                else:
                    data = cursor.fetchall()
                    if not data or (operation == "permission_lookup" and data[0][0] is not True):
                        raise RuntimeError("Benchmark query was not authorized")
                timings.append((time.perf_counter_ns() - before) / 1e6)
        return timings

    for clients in (1, 4):
        for repeat in range(1, 4):
            for operation in ("permission_lookup", "protected_read", "protected_write"):
                start = time.perf_counter()
                with ThreadPoolExecutor(max_workers=clients) as pool:
                    values = [ms for batch in pool.map(
                        lambda i: worker(operation, i), range(clients)
                    ) for ms in batch]
                rows.append({"operation": operation, "clients": clients, "repeat": repeat,
                             **summarize(values, time.perf_counter() - start)})
                samples.extend({"operation": operation, "clients": clients, "repeat": repeat, "ms": ms}
                               for ms in values)
    with connect() as admin:
        revoke: list[float] = []
        start = time.perf_counter()
        for record in ids[:min(100, count)]:
            before = time.perf_counter_ns()
            if server_timing:
                revoke.append(server_execution_ms(
                    admin, "DELETE FROM relations WHERE object_id = %s RETURNING id", (record,)
                ))
            else:
                admin.execute("DELETE FROM relations WHERE object_id = %s", (record,))
                revoke.append((time.perf_counter_ns() - before) / 1e6)
        rows.append({"operation": "cascade_revocation_26_tuples", "clients": 1,
                     **summarize(revoke, time.perf_counter() - start)})
        samples.extend({"operation": "cascade_revocation_26_tuples", "clients": 1, "ms": ms} for ms in revoke)
        plans = {}
        for name, query in [
            ("permission_lookup", "SELECT id FROM permissions WHERE user_id='nurse' AND object_id='bench-999'"),
            ("protected_read", "SELECT id FROM protected_records WHERE id='bench-999'"),
        ]:
            connection = connect(application=True)
            try:
                connection.execute(
                    """SELECT set_config('app.adam.user_attributes', '{"profession":"nurse"}', false)"""
                )
                plans[name] = connection.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0]
            finally:
                connection.close()
    (output / "latencies.json").write_text(json.dumps(samples, indent=2))
    (output / "plans.json").write_text(json.dumps(plans, indent=2))
    return {"rows": rows, "seed_count": count, "tuples_per_seed": 26,
            "attributes_per_permission": 1, "rules_per_permission": 1,
            "measurement": (
                "PostgreSQL EXPLAIN ANALYZE Execution Time; TIMING OFF; includes triggers; excludes planning and commit"
                if server_timing else "client execute and result consumption"
            ),
            "samples_per_client_per_repeat": 100 if server_timing else 300,
            "throughput_scope": "instrumented wall-clock including connections and 20 warm-up requests per worker",
            "scope": "existing SQL core + experimental protected_records RLS adapter; no HTTP/JWT/vault"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=1000)
    parser.add_argument("--server-timing", action="store_true")
    args = parser.parse_args()
    if args.seeds < 1000:
        parser.error("--seeds must be at least 1000")
    if any((args.output / name).exists() for name in ("results.json", "latencies.json", "plans.json")):
        parser.error("output already contains benchmark results; choose a new directory")
    args.output.mkdir(parents=True, exist_ok=True)
    name = "adam-validation-" + uuid4().hex[:12]
    subprocess.run([
        "docker", "run", "--detach", "--name", name, "--cpus=1", "--memory=1g",
        "--publish", "127.0.0.1::5432",
        "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_DB=validation",
        "postgres:18.6",
    ], check=True)
    report: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        port = subprocess.check_output(["docker", "port", name, "5432/tcp"], text=True).strip().split(":")[-1]
        os.environ["ADAM_VALIDATION_DSN"] = f"host=127.0.0.1 port={port} dbname=validation"
        deadline = time.monotonic() + 60
        while subprocess.run(
            ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "postgres", "-d", "validation"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            if time.monotonic() > deadline:
                raise TimeoutError("PostgreSQL did not become ready")
            time.sleep(.5)
        files = sql_files(CHANGELOG)
        with psycopg.connect(os.environ["ADAM_VALIDATION_DSN"], user="postgres", autocommit=True) as admin:
            admin.execute("CREATE SCHEMA adam; SET search_path TO adam, public")
            for path in files:
                admin.execute(path.read_text())
            admin.execute((FIXTURE).read_text())
            admin.execute((RLS_POLICY).read_text())
            report["server_version"] = admin.execute("SELECT version()").fetchone()[0]
            report["settings"] = dict(admin.execute(
                "SELECT name, setting FROM pg_settings WHERE name IN "
                "('shared_buffers','work_mem','max_connections','fsync','synchronous_commit')"
            ).fetchall())
        report["source_sha256"] = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files + [FIXTURE, RLS_POLICY]
        }
        report["docker_image"] = subprocess.check_output(
            ["docker", "inspect", name, "--format", "{{.Image}}"], text=True
        ).strip()
        report["adapter_tests"] = tests("test_protected_access.py")
        report["lifecycle_tests"] = tests("test_lifecycle.py")
        report["concurrency_tests"] = tests("test_concurrency.py")
        report["repository_claim_tests"] = tests("test_repository_claims.py")
        report["clinical_tests"] = tests("test_clinical_replay.py")
        report["eventb_sql_tests"] = tests("test_eventb_sql_correspondence.py")
        report["attribute_equivalence_tests"] = tests("test_attribute_equivalence.py")
        report["benchmark"] = benchmark(args.output, args.seeds, server_timing=args.server_timing)
        report["overall"] = "FAIL" if any(
            report[key]["exit_code"] for key in
            ("adapter_tests", "lifecycle_tests", "concurrency_tests", "repository_claim_tests",
             "clinical_tests", "eventb_sql_tests", "attribute_equivalence_tests")
        ) else "PASS"
        (args.output / "results.json").write_text(json.dumps(report, indent=2))
        print(json.dumps({"overall": report["overall"], "output": str(args.output)}, indent=2))
        return 1 if report["overall"] == "FAIL" else 0
    finally:
        subprocess.run(["docker", "rm", "--force", name], check=True)


if __name__ == "__main__":
    raise SystemExit(main())
