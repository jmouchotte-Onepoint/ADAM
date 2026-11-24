"""Audit OWASP A01:2021 du coeur SQL ADAM, avant et après correction.

Le script installe deux bases dans le même serveur :

  baseline   changelog complet privé du changeset 2026-owasp-a01-hardening
  hardened   changelog complet

Les mêmes sondes sont exécutées sur les deux bases depuis un rôle PostgreSQL
non privilégié (NOSUPERUSER, NOBYPASSRLS) disposant uniquement des droits d'un
rôle applicatif de tenant. Une sonde renvoie True lorsque l'attaque aboutit.
La suite test_owasp_a01.py est ensuite exécutée sur la base corrigée.

    python check_owasp_a01.py --output ../Results/owasp-a01
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run import BENCH, CHANGELOG, FIXTURE, RLS_POLICY, ROOT, sql_files, tests


AUDIT_TRAIL = ROOT / "ADAM/6_AUDIT_TRAIL"
# Les correctifs A01 sont dans les fichiers de référence des couches 0 à 3 : la
# base « avant correction » est donc obtenue en rejouant les définitions
# publiées par-dessus une installation à jour. Tout le reste est identique.
REVERT = Path(__file__).resolve().parent / "A01-REVERT-HARDENING.sql"


def is_audit_trail(path: Path) -> bool:
    return AUDIT_TRAIL in path.parents
POSTGRES_IMAGE = "postgres:18.6"

RECORDS = {
    "parcours-a01-own": ("tenantA", "nurse"),
    "parcours-a01-other": ("tenantA", "other-user"),
    "parcours-a01-foreign": ("tenantB", "doctorB"),
    "parcours-a01-foreign-meta": ("tenantB", "doctorB"),
    "parcours-a01-attribute": ("tenantA", "nurse"),
    "parcours-a01-rule": ("tenantA", "nurse"),
}


def admin(dsn: str) -> psycopg.Connection:
    connection = psycopg.connect(dsn, user="postgres", autocommit=True,
                                 options="-c search_path=adam,public")
    connection.execute(
        "SELECT set_config('app.adam.user_id','postgres',false), "
        "set_config('app.adam.tenant_id','tenantA',false), "
        "set_config('app.adam.user_attributes','{}',false)"
    )
    return connection


def application(dsn: str, role: str = "read_validation") -> psycopg.Connection:
    return psycopg.connect(dsn, user=role, autocommit=True,
                           options="-c search_path=adam,public")


def context(db: psycopg.Connection, user_id: str, tenant: str = "tenantA",
            attributes: str = "{}") -> None:
    db.execute("SELECT set_config('app.adam.user_id',%s,false), "
               "set_config('app.adam.tenant_id',%s,false), "
               "set_config('app.adam.user_attributes',%s,false)",
               (user_id, tenant, attributes))


def readable(db: psycopg.Connection, record: str) -> bool:
    return bool(db.execute("SELECT id FROM protected_records WHERE id = %s", (record,)).fetchall())


def install(dsn: str, files: list[Path], *, revert: bool = False) -> None:
    with psycopg.connect(dsn, user="postgres", autocommit=True) as db:
        db.execute("CREATE SCHEMA adam; SET search_path TO adam, public")
        for path in files:
            db.execute(path.read_text())
        if revert:
            db.execute(REVERT.read_text())
        db.execute(FIXTURE.read_text())
        db.execute(RLS_POLICY.read_text())


def seed(dsn: str) -> None:
    with admin(dsn) as db:
        # Le rôle applicatif est rattaché aux deux tenants : seule la variable de
        # session distingue encore tenantA de tenantB.
        db.execute("INSERT INTO tenants_per_users(tenant_id, pg_user) "
                   "VALUES ('tenantB','read_validation') ON CONFLICT DO NOTHING")
        for record, (tenant, subject) in RECORDS.items():
            db.execute("INSERT INTO parcours.etapes(id, tenant_id) VALUES (%s,%s)", (record, tenant))
            db.execute("INSERT INTO protected_records(id, tenant_id) VALUES (%s,%s)", (record, tenant))
            db.execute(
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                "VALUES ('users',%s,'assigned','etapes',%s,%s)", (subject, record, tenant))

        db.execute("""INSERT INTO permissions_attributes(permission_id, attribute)
                      SELECT id, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb
                      FROM permissions WHERE object_id = 'parcours-a01-attribute'
                        AND relation = 'can_read'""")
        db.execute("""INSERT INTO permissions_attributes(permission_id, attribute)
                      SELECT id, '[{"key":"tenantB_secret","operator":"IS","value":["confidential"]}]'::jsonb
                      FROM permissions WHERE object_id = 'parcours-a01-foreign-meta'
                        AND relation = 'can_read'""")

        rule = db.execute("INSERT INTO dynamic_rules(description, rule, params) "
                          "VALUES ('owasp-a01-deny','SELECT FALSE',ARRAY[]::text[]) "
                          "RETURNING id").fetchone()[0]
        db.execute("INSERT INTO permissions_rules(permission_id, rule_id) "
                   "SELECT id, %s FROM permissions WHERE object_id = 'parcours-a01-rule' "
                   "AND relation = 'can_read'", (rule,))

        db.execute("DO $$ BEGIN "
                   "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='deleterevil') THEN "
                   "    CREATE ROLE deleterevil LOGIN NOSUPERUSER NOBYPASSRLS; "
                   "  END IF; END $$;")
        db.execute("GRANT USAGE ON SCHEMA adam TO deleterevil")
        db.execute("GRANT SELECT ON ALL TABLES IN SCHEMA adam TO deleterevil")
        db.execute("GRANT DELETE ON permissions_rules TO deleterevil")
        db.execute("INSERT INTO tenants_per_users(tenant_id, pg_user) "
                   "VALUES ('tenantA','deleterevil') ON CONFLICT DO NOTHING")

        # A01-9 : rôle applicatif disposant des droits d'écriture du déploiement
        # livré (ADAM/5_DEV_TEST/DEV-0004), pour viser la dérivation du graphe.
        db.execute("DO $$ BEGIN "
                   "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='grapheditor') THEN "
                   "    CREATE ROLE grapheditor LOGIN NOSUPERUSER NOBYPASSRLS; "
                   "  END IF; END $$;")
        db.execute("GRANT USAGE ON SCHEMA adam TO grapheditor")
        db.execute("GRANT SELECT ON ALL TABLES IN SCHEMA adam TO grapheditor")
        db.execute("GRANT INSERT ON relations, roles, permissions TO grapheditor")
        db.execute("INSERT INTO tenants_per_users(tenant_id, pg_user) "
                   "VALUES ('tenantA','grapheditor') ON CONFLICT DO NOTHING")


def probe(dsn: str) -> dict:
    """Renvoie, pour chaque sonde, True si l'attaque aboutit."""
    result: dict = {}

    with application(dsn) as db:
        context(db, "nurse")
        result["reference_authorized_read"] = readable(db, "parcours-a01-own")

    with application(dsn) as db:
        context(db, "other-user")
        result["A01-1_subject_forgery"] = readable(db, "parcours-a01-other")

    with application(dsn) as db:
        context(db, "doctorB", tenant="tenantB")
        result["A01-2_tenant_switch"] = readable(db, "parcours-a01-foreign")

    with application(dsn) as db:
        context(db, "nurse", attributes="{}")
        denied = not readable(db, "parcours-a01-attribute")
        context(db, "nurse", attributes='{"profession":"nurse"}')
        result["A01-3_attribute_self_assertion"] = denied and readable(db, "parcours-a01-attribute")

    with application(dsn) as db:
        context(db, "nurse")
        denied = not readable(db, "parcours-a01-rule")
        db.execute("CREATE TEMP VIEW view_all_access_rules AS "
                   "SELECT NULL::text AS relation_type, NULL::uuid AS id, "
                   "NULL::uuid AS rule_id, NULL::jsonb AS params WHERE false")
        result["A01-4_rule_view_shadowing"] = denied and readable(db, "parcours-a01-rule")

    with application(dsn) as db:
        context(db, "nurse")
        denied = not readable(db, "parcours-a01-rule")
        db.execute("CREATE TEMP TABLE dynamic_rules(id uuid, rule text, params text[], "
                   "description text, creation_date timestamptz)")
        db.execute("INSERT INTO dynamic_rules "
                   "SELECT id,'SELECT TRUE',params,description,creation_date FROM adam.dynamic_rules")
        result["A01-5_dynamic_rules_shadowing"] = denied and readable(db, "parcours-a01-rule")

    with application(dsn, role="deleterevil") as db:
        context(db, "deleterevil")
        result["A01-6_role_prefix_wildcard"] = db.execute(
            "DELETE FROM permissions_rules WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE object_id = 'parcours-a01-rule')"
        ).rowcount > 0

    with application(dsn) as db:
        context(db, "nurse")
        result["A01-7_cross_tenant_metadata"] = db.execute(
            "SELECT count(*) FROM view_all_access_attributes "
            "WHERE attribute::text LIKE '%tenantB_secret%'").fetchone()[0] > 0

    # A01-9 : les fonctions de dérivation résolvent `model` sans schéma. Une
    # table temporaire du même nom, portant un identifiant réel pour satisfaire
    # les clés étrangères, fait matérialiser une permission absente du modèle.
    derived = "parcours-a01-derivation"
    with application(dsn, role="grapheditor") as db:
        context(db, "intruder")
        model_id = db.execute("SELECT id FROM model WHERE relation = 'can_read' "
                              "AND relation_type = 'PERMISSIONS'").fetchone()[0]
        db.execute("CREATE TEMP TABLE model (LIKE adam.model INCLUDING DEFAULTS)")
        for relation_type, relation in (("RELATIONS", "assigned"),
                                        ("PERMISSIONS", "can_exfiltrate")):
            db.execute("INSERT INTO model(id, relation_type, relation_source, user_type, "
                       "relation, object_type) VALUES (%s,%s,'assigned','users',%s,'etapes')",
                       (model_id, relation_type, relation))
        try:
            db.execute("INSERT INTO relations(user_type,user_id,relation,object_type,"
                       "object_id,tenant_id) VALUES "
                       "('users','intruder','assigned','etapes',%s,'tenantA')", (derived,))
        except psycopg.Error:
            pass

    with admin(dsn) as db:
        result["A01-9_derivation_model_shadowing"] = db.execute(
            "SELECT count(*) FROM permissions WHERE object_id = %s "
            "AND relation = 'can_exfiltrate'", (derived,)).fetchone()[0] > 0

    with admin(dsn) as db:
        db.execute("DO $$ BEGIN "
                   "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='graph_owner') THEN "
                   "    CREATE ROLE graph_owner LOGIN NOSUPERUSER NOBYPASSRLS; "
                   "  END IF; END $$;")
        db.execute("GRANT USAGE ON SCHEMA adam TO graph_owner")
        db.execute("ALTER TABLE adam.permissions OWNER TO graph_owner")
    try:
        with application(dsn, role="graph_owner") as db:
            result["A01-8_table_owner_bypass"] = db.execute(
                "SELECT count(DISTINCT tenant_id) FROM adam.permissions").fetchone()[0] > 1
        # La détection est évaluée pendant que le rôle est encore propriétaire.
        with admin(dsn) as db:
            detectable = db.execute(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'adam' AND p.proname = 'fn_check_runtime_role'").fetchone()[0] == 1
            result["A01-8_invariant_is_verifiable"] = detectable
            if detectable:
                result["A01-8_invariant_violations_for_owner"] = sorted(
                    kind for (kind,) in
                    db.execute("SELECT violation FROM fn_check_runtime_role('graph_owner')").fetchall())
                result["A01-8_invariant_violations_for_application_role"] = sorted(
                    kind for (kind,) in
                    db.execute("SELECT violation FROM fn_check_runtime_role('read_validation')").fetchall())
    finally:
        with admin(dsn) as db:
            db.execute("ALTER TABLE adam.permissions OWNER TO postgres")
            db.execute("REVOKE ALL ON SCHEMA adam FROM graph_owner")
            db.execute("DROP ROLE IF EXISTS graph_owner")

    return result


def wait_ready(name: str) -> None:
    deadline = time.monotonic() + 60
    while subprocess.run(
        ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode:
        if time.monotonic() > deadline:
            raise TimeoutError("PostgreSQL did not become ready")
        time.sleep(.5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.output / "results.json").exists():
        parser.error("output already contains an audit; choose a new directory")
    args.output.mkdir(parents=True, exist_ok=True)

    files = sql_files(CHANGELOG)
    if not REVERT.exists():
        raise RuntimeError(f"{REVERT.name} is missing")
    if not any(is_audit_trail(path) for path in files):
        raise RuntimeError("the audit trail is not referenced by the changelog")

    report: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    # Les rôles PostgreSQL sont partagés par toutes les bases d'un même serveur :
    # chaque variante reçoit donc son propre conteneur.
    containers: list[str] = []
    try:
        for variant, revert in (("baseline", True), ("hardened", False)):
            name = f"adam-owasp-a01-{variant}-" + uuid4().hex[:8]
            subprocess.run([
                "docker", "run", "--detach", "--name", name, "--cpus=2", "--memory=1g",
                "--publish", "127.0.0.1::5432", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                "--env", "POSTGRES_DB=validation", POSTGRES_IMAGE,
            ], check=True, stdout=subprocess.DEVNULL)
            containers.append(name)
            port = subprocess.check_output(
                ["docker", "port", name, "5432/tcp"], text=True).strip().rsplit(":", 1)[1]
            wait_ready(name)
            dsn = f"host=127.0.0.1 port={port} dbname=validation"
            install(dsn, files, revert=revert)
            seed(dsn)
            report[variant] = probe(dsn)
            if variant == "hardened":
                report["server_version"] = subprocess.check_output(
                    ["docker", "exec", name, "postgres", "--version"], text=True).strip()
                report["docker_image"] = subprocess.check_output(
                    ["docker", "inspect", name, "--format", "{{.Image}}"], text=True).strip()
                os.environ["ADAM_VALIDATION_DSN"] = dsn
                report["regression_tests"] = tests("test_owasp_a01.py")

        report["source_sha256"] = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files + [FIXTURE, RLS_POLICY, REVERT,
                                 BENCH / "owasp/test_owasp_a01.py"]
        }

        exploited = {key for key, value in report["baseline"].items()
                     if key.startswith("A01-") and value is True}
        remaining = {key for key, value in report["hardened"].items()
                     if key.startswith("A01-") and value is True
                     and key != "A01-8_invariant_is_verifiable"}
        report["exploited_before"] = sorted(exploited)
        report["remaining_after"] = sorted(remaining)
        report["overall"] = (
            "PASS" if exploited and remaining == {"A01-8_table_owner_bypass"}
            and not report["regression_tests"]["exit_code"]
            and report["hardened"]["reference_authorized_read"] else "FAIL"
        )
        (args.output / "results.json").write_text(json.dumps(report, indent=2))
        print(json.dumps({"overall": report["overall"],
                          "exploited_before": report["exploited_before"],
                          "remaining_after": report["remaining_after"],
                          "output": str(args.output)}, indent=2))
        return 1 if report["overall"] == "FAIL" else 0
    finally:
        for name in containers:
            subprocess.run(["docker", "rm", "--force", name], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())
