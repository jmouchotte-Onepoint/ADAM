"""Coût du durcissement et du journal d'audit, une variable à la fois.

Trois installations du même changelog, dans des conteneurs distincts et mesurées
l'une après l'autre sur le même hôte :

  baseline   ni durcissement A01 ni journal
  hardened   durcissement seul
  audited    changelog complet

hardened/baseline isole le durcissement, audited/hardened isole le journal. Les
temps sont ceux d'EXPLAIN ANALYZE, comme dans run.py.

    python compare_audit_cost.py --output ../Results/local/audit-cost
"""
import sys
from pathlib import Path

# Les modules du harnais forment un espace de noms unique à la racine de
# Benchmark-AI : on l'ajoute pour que ce script reste exécutable directement.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

import psycopg

from owasp.check_owasp_a01 import POSTGRES_IMAGE, install, is_audit_trail, wait_ready
from run import CHANGELOG, server_execution_ms, sql_files, summarize

SEEDS = 300
MEASURED_READS = 100
WARMUP = 20


def measure(dsn: str, variant: str) -> dict:
    result: dict = {"variant": variant}
    records = [f"cost-{i}" for i in range(SEEDS)]

    with psycopg.connect(dsn, user="postgres", autocommit=True,
                         options="-c search_path=adam,public") as admin:
        admin.execute("SELECT set_config('app.adam.user_id','postgres',false), "
                      "set_config('app.adam.tenant_id','tenantA',false), "
                      "set_config('app.adam.user_attributes','{}',false)")
        # La profession exigée par la contrainte ABAC passe par la délégation là
        # où elle existe, par la variable de session avant le durcissement.
        if admin.execute("SELECT to_regclass('users_per_pg_user')").fetchone()[0] is not None:
            admin.execute(
                "INSERT INTO users_per_pg_user(pg_user, user_id, tenant_id, user_attributes) "
                "VALUES ('read_validation','nurse','tenantA','{\"profession\":\"nurse\"}'::jsonb) "
                "ON CONFLICT (pg_user, tenant_id, user_id) "
                "DO UPDATE SET user_attributes = EXCLUDED.user_attributes")
        admin.execute(
            "INSERT INTO protected_records(id, tenant_id) SELECT 'cost-' || i, 'tenantA' "
            "FROM generate_series(0, %s) i", (SEEDS - 1,))

        insertion: list[float] = []
        start = time.perf_counter()
        for record in records:
            insertion.append(server_execution_ms(
                admin,
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,"
                "tenant_id) VALUES ('users','nurse','assigned','etapes',%s,'tenantA') RETURNING id",
                (record,)))
        result["graph_insert"] = summarize(insertion, time.perf_counter() - start)

        admin.execute(
            """INSERT INTO permissions_attributes(permission_id, attribute)
            SELECT id, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb
            FROM permissions WHERE object_id LIKE 'cost-%' AND relation IN ('can_read','can_write')""")
        admin.execute("ANALYZE")

        if admin.execute("SELECT to_regclass('audit_log')").fetchone()[0] is not None:
            result["audit_entries"] = admin.execute("SELECT count(*) FROM audit_log").fetchone()[0]
            result["audit_bytes"] = admin.execute(
                "SELECT pg_total_relation_size('audit_log')").fetchone()[0]
            result["permissions_bytes"] = admin.execute(
                "SELECT pg_total_relation_size('permissions')").fetchone()[0]

    with psycopg.connect(dsn, user="read_validation", autocommit=True,
                         options="-c search_path=adam,public") as app:
        app.execute("SELECT set_config('app.adam.user_id','nurse',false), "
                    "set_config('app.adam.tenant_id','tenantA',false), "
                    """set_config('app.adam.user_attributes','{"profession":"nurse"}',false)""")
        query, params = "SELECT id FROM protected_records WHERE id = %s", (records[0],)
        for _ in range(WARMUP):
            if not app.execute(query, params).fetchall():
                raise RuntimeError(f"{variant}: protected read was not authorized")
        reads = [server_execution_ms(app, query, params) for _ in range(MEASURED_READS)]
        result["protected_read"] = summarize(reads, sum(reads) / 1000)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.output / "results.json").exists():
        parser.error("output already contains a measurement; choose a new directory")
    args.output.mkdir(parents=True, exist_ok=True)

    files = sql_files(CHANGELOG)
    # Une variable à la fois : la base de référence est l'installation durcie
    # sur laquelle on rejoue les définitions publiées.
    variants = {
        "baseline": ([p for p in files if not is_audit_trail(p)], True),
        "hardened": ([p for p in files if not is_audit_trail(p)], False),
        "audited": (files, False),
    }

    report: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "seeds": SEEDS, "measured_reads": MEASURED_READS,
                    "measurement": "PostgreSQL EXPLAIN ANALYZE Execution Time; TIMING OFF"}
    for variant, (selected, revert) in variants.items():
        name = f"adam-audit-cost-{variant}-" + uuid4().hex[:8]
        subprocess.run([
            "docker", "run", "--detach", "--name", name, "--cpus=1", "--memory=1g",
            "--publish", "127.0.0.1::5432", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
            "--env", "POSTGRES_DB=validation", POSTGRES_IMAGE,
        ], check=True, stdout=subprocess.DEVNULL)
        try:
            port = subprocess.check_output(
                ["docker", "port", name, "5432/tcp"], text=True).strip().rsplit(":", 1)[1]
            wait_ready(name)
            dsn = f"host=127.0.0.1 port={port} dbname=validation"
            install(dsn, selected, revert=revert)
            report[variant] = measure(dsn, variant)
        finally:
            subprocess.run(["docker", "rm", "--force", name], check=True, stdout=subprocess.DEVNULL)

    for operation in ("graph_insert", "protected_read"):
        report.setdefault("ratios", {})[operation] = {
            "hardening": round(report["hardened"][operation]["p50_ms"]
                               / report["baseline"][operation]["p50_ms"], 3),
            "audit": round(report["audited"][operation]["p50_ms"]
                           / report["hardened"][operation]["p50_ms"], 3),
        }
    (args.output / "results.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"ratios": report["ratios"],
                      "p50": {v: {o: report[v][o]["p50_ms"] for o in ("graph_insert", "protected_read")}
                              for v in variants},
                      "audit_entries": report["audited"].get("audit_entries"),
                      "audit_bytes": report["audited"].get("audit_bytes")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
