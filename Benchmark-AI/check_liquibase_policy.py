from pathlib import Path
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

import psycopg

from run import CHANGELOG, FIXTURE, RLS_POLICY, ROOT, sql_files


def main() -> None:
    name = "adam-liquibase-test-" + uuid.uuid4().hex[:12]
    subprocess.run([
        "docker", "run", "--detach", "--name", name, "--cpus=1", "--memory=1g",
        "--publish", "127.0.0.1::5432", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
        "--env", "POSTGRES_DB=validation", "postgres:18.6",
    ], check=True, stdout=subprocess.DEVNULL)
    try:
        port = subprocess.check_output(
            ["docker", "port", name, "5432/tcp"], text=True
        ).strip().rsplit(":", 1)[1]
        deadline = time.monotonic() + 60
        while subprocess.run(
            ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "postgres", "-d", "validation"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            if time.monotonic() > deadline:
                raise TimeoutError("PostgreSQL not ready")
            time.sleep(.5)
        dsn = f"host=127.0.0.1 port={port} dbname=validation"
        with psycopg.connect(dsn, user="postgres", autocommit=True) as db:
            db.execute("CREATE SCHEMA adam; SET search_path TO adam, public")
            for path in sql_files(CHANGELOG):
                db.execute(path.read_text())
            db.execute((FIXTURE).read_text())
            # Le scénario oppose deux sujets délégués au même rôle PostgreSQL :
            # il mesure la politique, pas la résolution d'identité.
            db.execute(
                "INSERT INTO users_per_pg_user(pg_user, user_id, tenant_id) "
                "VALUES ('read_validation','other-user','tenantA') ON CONFLICT DO NOTHING"
            )
            db.execute("INSERT INTO parcours.etapes(id, tenant_id) VALUES ('parcours-liquibase', 'tenantA')")
            db.execute(
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                "VALUES ('users','nurse','assigned','etapes','parcours-liquibase','tenantA')"
            )

        namespace = "http://www.liquibase.org/xml/ns/dbchangelog"
        ET.register_namespace("", namespace)
        source = ET.parse(ROOT / "ADAM/4_INSERT/changelog.xml").getroot()
        changeset = next(node for node in source if node.attrib.get("id") == "INSERT-RLS-POLICY")
        corrected = (RLS_POLICY).read_text()
        historical = corrected.replace(
            "DROP POLICY IF EXISTS adam_policy_select_parcours_etapes ON parcours.etapes;\n\n", ""
        ).replace(
            "    USING (\n", "    USING (\n"
            "        EXISTS (SELECT 1 FROM permissions AS rrp "
            "WHERE rrp.tenant_id = get_current_tenant_id() AND is_allow('read')) OR\n"
        ).replace(
            "            AND (rrp.expires_at IS NULL OR rrp.expires_at > statement_timestamp())\n", ""
        )
        if historical == corrected or "AND is_allow('read')" not in historical:
            raise RuntimeError("Failed to reconstruct the historical policy")

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = directory / "INSERT-RLS-POLICY.sql"
            changelog = directory / "changelog.xml"

            def write_changelog(run_on_change: bool) -> None:
                node = ET.fromstring(ET.tostring(changeset))
                if not run_on_change:
                    node.attrib.pop("runOnChange", None)
                parent = ET.Element(f"{{{namespace}}}databaseChangeLog", dict(source.attrib))
                parent.append(node)
                ET.ElementTree(parent).write(changelog, encoding="utf-8", xml_declaration=True)

            def update() -> None:
                subprocess.run([
                    "docker", "run", "--rm", "--mount", f"type=bind,src={directory},dst=/work,readonly",
                    "liquibase/liquibase:4.32.0", "--search-path=/work",
                    f"--url=jdbc:postgresql://host.docker.internal:{port}/validation?currentSchema=adam",
                    "--username=postgres", "--changelog-file=changelog.xml", "update",
                ], check=True)

            policy.write_text(historical)
            write_changelog(False)
            update()
            with psycopg.connect(
                dsn, user="read_validation", autocommit=True, options="-c search_path=adam,public"
            ) as app:
                app.execute("SELECT set_config('app.adam.user_id','other-user',false), "
                            "set_config('app.adam.tenant_id','tenantA',false)")
                if app.execute("SELECT id FROM parcours.etapes").fetchall() != [("parcours-liquibase",)]:
                    raise AssertionError("Historical bypass was not reproduced")
                policy.write_text(corrected)
                write_changelog(True)
                update()
                if app.execute("SELECT id FROM parcours.etapes").fetchall() != []:
                    raise AssertionError("Updated policy did not block the unrelated subject")
                app.execute("SELECT set_config('app.adam.user_id','nurse',false)")
                if app.execute("SELECT id FROM parcours.etapes").fetchall() != [("parcours-liquibase",)]:
                    raise AssertionError("Updated policy denied the authorized subject")
            with psycopg.connect(
                dsn, user="postgres", autocommit=True, options="-c search_path=adam,public"
            ) as db:
                status = db.execute(
                    "SELECT exectype FROM databasechangelog WHERE id='INSERT-RLS-POLICY'"
                ).fetchone()[0]
                if status != "RERAN":
                    raise AssertionError(f"Expected RERAN; got {status}")
        print("PASS: Liquibase reapplied the corrected policy; subject checks passed")
    finally:
        subprocess.run(["docker", "rm", "--force", name], check=True)


if __name__ == "__main__":
    main()
