import hashlib
import shutil
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import psycopg

from run import CHANGELOG, FIXTURE, ROOT


HISTORICAL_ARCHIVE = ROOT / "Benchmark-AI/fixtures/adam-fe473fc.tar"
HISTORICAL_SHA256 = "ee091f6cff928fb99150eea9080b78ad4a4a9e043dc63bd96f3afbb42047a26b"
POSTGRES_IMAGE = "postgres:18.6"
LIQUIBASE_IMAGE = "liquibase/liquibase:4.32.0"


def baseline_changelog(destination: Path) -> None:
    tree = ET.parse(CHANGELOG)
    root = tree.getroot()
    # L'installation consolidée précède le journal d'audit et le figeage du
    # search_path : ces deux couches sont ce que la montée de version ajoute.
    for layer in ("6_AUDIT_TRAIL/changelog.xml", "7_SECURITY/changelog.xml"):
        node = next(n for n in root if n.attrib.get("file", "").endswith(layer))
        root.remove(node)
    ET.register_namespace("", "http://www.liquibase.org/xml/ns/dbchangelog")
    target = destination / "Benchmark-AI/sql/changelog.xml"
    target.parent.mkdir(parents=True)
    tree.write(target, encoding="utf-8", xml_declaration=True)


def update(root: Path, port: str, database: str, *, succeeds: bool = True) -> str:
    command = [
        "docker", "run", "--rm", "--mount", f"type=bind,src={root},dst=/work,readonly",
        LIQUIBASE_IMAGE, "--search-path=/work",
        f"--url=jdbc:postgresql://host.docker.internal:{port}/{database}?currentSchema=adam",
        "--username=postgres", "--changelog-file=Benchmark-AI/sql/changelog.xml", "update",
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    output = result.stdout + result.stderr
    if succeeds and result.returncode:
        raise RuntimeError(f"Liquibase update failed:\n{output}")
    if not succeeds and (result.returncode == 0 or "is duplicated" not in output.lower()):
        raise RuntimeError(f"Expected a duplicate-key migration failure:\n{output}")
    return output


def check_legacy(port: str, baseline: Path) -> None:
    update(baseline, port, "legacy")
    dsn = f"host=127.0.0.1 port={port} dbname=legacy user=postgres options='-c search_path=adam,public'"
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute("SELECT set_config('app.adam.user_id', 'postgres', false)")
        db.execute(FIXTURE.read_text())
        db.execute("INSERT INTO protected_records(id, tenant_id) VALUES ('migration-test', 'tenantA')")
        db.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes','migration-test','tenantA')"
        )
        db.execute("UPDATE roles SET parent_relation_id = NULL WHERE object_id = 'migration-test'")
        db.execute("UPDATE permissions SET parent_relation_id = NULL WHERE object_id = 'migration-test'")
        duplicate_role = db.execute(
            "INSERT INTO roles(user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
            "parent_relation_id,is_auto_generated) "
            "SELECT user_type,user_id,relation,object_type,object_id,tenant_id,model_id,NULL,TRUE "
            "FROM roles WHERE object_id = 'migration-test' AND relation = 'role_1' RETURNING id"
        ).fetchone()[0]
        duplicate_permission = db.execute(
            "INSERT INTO permissions(user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
            "parent_relation_id,is_auto_generated) "
            "SELECT user_type,user_id,relation,object_type,object_id,tenant_id,model_id,NULL,TRUE "
            "FROM permissions WHERE object_id = 'migration-test' AND relation = 'can_read' RETURNING id"
        ).fetchone()[0]

        def assert_rolled_back() -> None:
            indexes = db.execute(
                "SELECT indexrelid::regclass::text, indnullsnotdistinct FROM pg_index "
                "WHERE indexrelid IN ('idx_uniq_roles'::regclass, 'idx_uniq_permissions'::regclass)"
            ).fetchall()
            if len(indexes) != 2 or any(flag for _, flag in indexes):
                raise AssertionError(f"Index changes were not rolled back: {indexes}")
            if db.execute(
                "SELECT count(*) FROM databasechangelog WHERE id='2026-authorization-integrity'"
            ).fetchone()[0]:
                raise AssertionError("Failed migration was recorded as applied")
            counts = db.execute(
                "SELECT (SELECT count(*) FROM roles WHERE object_id='migration-test'), "
                "(SELECT count(*) FROM permissions WHERE object_id='migration-test')"
            ).fetchone()
            if counts != (5, 22):
                raise AssertionError(f"Migration changed test data: {counts}")

        update(ROOT, port, "legacy", succeeds=False)
        assert_rolled_back()
        db.execute("DELETE FROM roles WHERE id = %s", (duplicate_role,))
        update(ROOT, port, "legacy", succeeds=False)
        indexes = db.execute(
            "SELECT indnullsnotdistinct FROM pg_index "
            "WHERE indexrelid IN ('idx_uniq_roles'::regclass, 'idx_uniq_permissions'::regclass)"
        ).fetchall()
        if len(indexes) != 2 or any(flag for (flag,) in indexes):
            raise AssertionError(f"Permission failure did not roll back both indexes: {indexes}")
        if db.execute("SELECT count(*) FROM permissions WHERE object_id='migration-test'").fetchone()[0] != 22:
            raise AssertionError("Permission failure changed test data")
        db.execute("DELETE FROM permissions WHERE id = %s", (duplicate_permission,))
        update(ROOT, port, "legacy")
        update(ROOT, port, "legacy")
        flags = db.execute(
            "SELECT indnullsnotdistinct FROM pg_index "
            "WHERE indexrelid IN ('idx_uniq_roles'::regclass, 'idx_uniq_permissions'::regclass)"
        ).fetchall()
        if len(flags) != 2 or not all(flag for (flag,) in flags):
            raise AssertionError(f"Corrected indexes missing: {flags}")
        counts = db.execute(
            "SELECT (SELECT count(*) FROM roles WHERE object_id='migration-test'), "
            "(SELECT count(*) FROM permissions WHERE object_id='migration-test')"
        ).fetchone()
        if counts != (4, 21):
            raise AssertionError(f"Unexpected data after migration: {counts}")
        definition = db.execute(
            "SELECT pg_get_functiondef('fn_check_all_attributes_from_view(uuid,text,jsonb)'::regprocedure)"
        ).fetchone()[0]
        if "v_record.attribute" not in definition or "Unsupported relation type" not in definition:
            raise AssertionError("Corrected attribute wrapper missing")
    print("PASS: historical upgrade rejects duplicates atomically, preserves data and is repeatable", flush=True)


def main() -> None:
    name = "adam-migration-test-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        historical = directory / "historical"
        consolidated = directory / "consolidated"
        historical.mkdir()
        consolidated.mkdir()
        if hashlib.sha256(HISTORICAL_ARCHIVE.read_bytes()).hexdigest() != HISTORICAL_SHA256:
            raise RuntimeError("Historical migration fixture checksum mismatch")
        subprocess.run(["tar", "-xf", str(HISTORICAL_ARCHIVE), "-C", str(historical)], check=True)
        shutil.copytree(ROOT / "ADAM", consolidated / "ADAM")
        baseline_changelog(historical)
        baseline_changelog(consolidated)
        subprocess.run([
            "docker", "run", "-d", "--name", name, "--cpus=1", "--memory=1g",
            "-p", "127.0.0.1::5432", "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e", "POSTGRES_DB=validation", POSTGRES_IMAGE,
        ], check=True, stdout=subprocess.DEVNULL)
        try:
            port = subprocess.check_output(["docker", "port", name, "5432/tcp"], text=True).strip().rsplit(":", 1)[1]
            deadline = time.monotonic() + 60
            while subprocess.run(
                ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            ).returncode:
                if time.monotonic() > deadline:
                    raise TimeoutError("PostgreSQL not ready")
                time.sleep(.5)
            with psycopg.connect(f"host=127.0.0.1 port={port} dbname=validation user=postgres", autocommit=True) as db:
                for database in ("legacy", "consolidated", "fresh"):
                    db.execute(f"CREATE DATABASE {database}")
            for database in ("legacy", "consolidated", "fresh"):
                with psycopg.connect(
                    f"host=127.0.0.1 port={port} dbname={database} user=postgres", autocommit=True
                ) as db:
                    db.execute("CREATE SCHEMA adam")
            check_legacy(port, historical)
            update(consolidated, port, "consolidated")
            update(ROOT, port, "consolidated")
            update(ROOT, port, "consolidated")
            print("PASS: consolidated-install upgrade and re-execution", flush=True)
            update(ROOT, port, "fresh")
            update(ROOT, port, "fresh")
            print("PASS: fresh installation and re-execution", flush=True)
        finally:
            subprocess.run(["docker", "rm", "--force", name], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
