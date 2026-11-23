import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

import psycopg

from compare_authorization import IMAGES, setup_postgres, start_container
from run import FIXTURE, ROOT, server_execution_ms, summarize, tests
from support import connect


OLD = """NOT EXISTS (
              SELECT 1 FROM view_all_access_attributes a
              WHERE a.id = p.id AND a.relation_type = 'permissions'
                AND fn_check_attributes(get_current_user_attributes(), a.attribute) IS NOT TRUE
          )"""
NEW = "fn_check_all_attributes_from_view(p.id, 'permissions', get_current_user_attributes()) IS TRUE"


def install_candidate(admin: psycopg.Connection) -> None:
    policies = FIXTURE.read_text().split("CREATE POLICY validation_select", 1)[1]
    policies = "CREATE POLICY validation_select" + policies
    if policies.count(OLD) != 2:
        raise RuntimeError("The baseline policies no longer match the expected attribute predicate")
    admin.execute("DROP POLICY validation_select ON protected_records")
    admin.execute("DROP POLICY validation_update ON protected_records")
    admin.execute(policies.replace(OLD, NEW))


def sample(operation: str, clients: int, n: int) -> list[float]:
    def worker(index: int) -> list[float]:
        record = f"parcours-{index}"
        query = ("SELECT id FROM protected_records WHERE id = %s" if operation == "read"
                 else "UPDATE protected_records SET value = value + 1 WHERE id = %s RETURNING id")
        with connect(application=True) as db:
            db.execute("SELECT set_config('app.adam.user_attributes', %s, false)",
                       ('{"profession":"nurse"}',))
            for _ in range(10):
                if len(db.execute(query, (record,)).fetchall()) != 1:
                    raise AssertionError(f"{operation} warm-up denied")
            return [server_execution_ms(db, query, (record,)) for _ in range(n)]

    with ThreadPoolExecutor(max_workers=clients) as pool:
        return [v for values in pool.map(worker, range(clients)) for v in values]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=10000)
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()
    if args.seeds < 4 or args.samples < 1:
        parser.error("at least four seeds and one sample are required")
    if any((args.output / name).exists() for name in ("results.json", "latencies.json", "plans.json")):
        parser.error("output already contains results")
    args.output.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    name = "adam-attribute-ab-" + uuid4().hex[:12]
    started: list[str] = []
    try:
        port = start_container(name, 5432, IMAGES["postgresql"], started,
                               options=("--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                                        "--env", "POSTGRES_DB=validation"))
        deadline = time.monotonic() + 60
        while subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1",
                              "-U", "postgres", "-d", "validation"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            if time.monotonic() >= deadline:
                raise TimeoutError("PostgreSQL did not become ready")
            time.sleep(.5)
        os.environ["ADAM_VALIDATION_DSN"] = f"host=127.0.0.1 port={port} dbname=validation"
        version, files = setup_postgres(args.seeds)
        with connect() as admin:
            admin.execute("INSERT INTO protected_records(id,tenant_id) SELECT id,tenant_id FROM parcours.etapes")
            admin.execute(
                """INSERT INTO permissions_attributes(permission_id,attribute)
                   SELECT id, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb
                   FROM permissions WHERE relation IN ('can_read','can_write')"""
            )
            rule = admin.execute(
                "INSERT INTO dynamic_rules(description,rule,params) "
                "VALUES ('attribute-plan-comparison','SELECT TRUE',ARRAY[]::text[]) RETURNING id"
            ).fetchone()[0]
            admin.execute(
                "INSERT INTO permissions_rules(permission_id,rule_id) "
                "SELECT id,%s FROM permissions WHERE relation IN ('can_read','can_write')", (rule,)
            )
            admin.execute("ANALYZE")
        rows, raw, plans, checks = [], [], {}, {}
        for variant in ("baseline", "targeted-wrapper"):
            if variant == "targeted-wrapper":
                with connect() as admin:
                    install_candidate(admin)
            checks[variant] = {pattern: tests(pattern) for pattern in (
                "test_protected_access.py", "test_concurrency.py", "test_repository_claims.py")}
            if any(result["exit_code"] for result in checks[variant].values()):
                raise RuntimeError(f"{variant} regression tests failed: {checks[variant]}")
            with connect(application=True) as db:
                db.execute("SELECT set_config('app.adam.user_attributes', %s, false)",
                           ('{"profession":"nurse"}',))
                plans[variant] = db.execute(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
                    "SELECT id FROM protected_records WHERE id = %s",
                    (f"parcours-{min(999, args.seeds - 1)}",),
                ).fetchone()[0]
            for clients in (1, 4):
                for operation in ("read", "write"):
                    for repeat in range(1, 4):
                        begin = time.perf_counter()
                        values = sample(operation, clients, args.samples)
                        rows.append({"variant": variant, "clients": clients, "operation": operation,
                                     "repeat": repeat, **summarize(values, time.perf_counter() - begin)})
                        raw.extend({"variant": variant, "clients": clients, "operation": operation,
                                    "repeat": repeat, "ms": v} for v in values)
        report = {
            "started_at_utc": started_at,
            "postgres_version": version, "seeds": args.seeds,
            "samples_per_client_per_repeat": args.samples,
            "protocol": "sequential A/B, same database; 10 warmups; 3 repetitions; EXPLAIN ANALYZE TIMING OFF",
            "scope": "experimental RLS adapter; always-true dynamic rule; no commit/network time",
            "checks": checks, "rows": rows,
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in files + [Path(__file__).resolve(),
                                                ROOT / "Benchmark-AI/run.py",
                                                ROOT / "Benchmark-AI/support.py",
                                                ROOT / "Benchmark-AI/compare_authorization.py"]},
            "image_id": subprocess.check_output(
                ["docker", "inspect", name, "--format", "{{.Image}}"], text=True).strip(),
        }
        for filename, data in (("results.json", report), ("latencies.json", raw), ("plans.json", plans)):
            (args.output / filename).write_text(json.dumps(data, indent=2) + "\n")
        print(f"PASS: baseline and targeted-wrapper; results in {args.output}")
    finally:
        for container in reversed(started):
            subprocess.run(["docker", "rm", "--force", container], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
