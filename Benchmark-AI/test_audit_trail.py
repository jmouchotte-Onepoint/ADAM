"""Journal d'audit des changements d'autorisation (DR5).

Trois propriétés : la couverture (y compris les écritures indirectes des triggers
de dérivation et des cascades), l'ajout seul, et la détection par la chaîne de
hachage. L'identité enregistrée vient du serveur, pas des variables de session.
"""
import json

import psycopg

from support import DatabaseTest


class AuditCoverageTests(DatabaseTest):
    def _entries(self, **criteria) -> list:
        clauses = " AND ".join(f"{column} = %s" for column in criteria)
        return self.admin.execute(
            "SELECT id, tenant_id, principal, subject, session_role, operation, "
            "object_table, row_id, before_row, after_row FROM audit_log"
            + (f" WHERE {clauses}" if criteria else "") + " ORDER BY id",
            tuple(criteria.values()),
        ).fetchall()

    def test_registered_coverage_is_complete_and_still_attached(self) -> None:
        """Le registre est rempli depuis le catalogue, et chaque entrée tient."""
        registered = {name for (name,) in self.admin.execute(
            "SELECT table_name FROM audit_coverage").fetchall()}
        self.assertIn("relations", registered)
        self.assertIn("permissions", registered)
        self.assertIn("model", registered)
        self.assertIn("users_per_pg_user", registered)
        self.assertGreaterEqual(len(registered), 10)

        detached = self.admin.execute(
            """
            SELECT coverage.table_name
              FROM audit_coverage AS coverage
              JOIN pg_class AS c ON c.relname = coverage.table_name
              JOIN pg_namespace AS n ON n.oid = c.relnamespace AND n.nspname = 'adam'
             WHERE NOT EXISTS (
                   SELECT 1 FROM pg_trigger AS t
                    WHERE t.tgrelid = c.oid AND NOT t.tgisinternal
                      AND t.tgname = 'trg_audit_' || coverage.table_name)
             ORDER BY 1
            """
        ).fetchall()
        self.assertEqual(detached, [])

    def test_tables_created_after_the_changeset_are_not_covered(self) -> None:
        """La couverture vaut à l'instant de la migration.

        Le harnais crée `protected_records` après le changelog : données
        applicatives, aucun état d'autorisation, donc pas journalisée.
        """
        uncovered = {name for (name,) in self.admin.execute(
            """
            SELECT c.relname
              FROM pg_class AS c
              JOIN pg_namespace AS n ON n.oid = c.relnamespace
             WHERE n.nspname = 'adam' AND c.relkind = 'r'
               AND c.relname NOT LIKE 'audit\\_%'
               AND c.relname NOT IN (SELECT table_name FROM audit_coverage)
            """
        ).fetchall()}
        self.assertEqual(uncovered, {"protected_records"})

    def test_direct_write_and_derived_rows_share_one_transaction(self) -> None:
        """Une insertion de relation et les lignes dérivées sont journalisées."""
        target = self.record + "-audit"
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantA')", (target,)
        )
        tables = {
            table: count for table, count in self.admin.execute(
                "SELECT object_table, count(*) FROM audit_log "
                "WHERE operation = 'INSERT' AND after_row ->> 'object_id' = %s "
                "GROUP BY object_table", (target,)
            ).fetchall()
        }
        self.assertEqual(tables.get("relations"), 1)
        self.assertGreater(tables.get("roles", 0), 0)
        self.assertGreater(tables.get("permissions", 0), 0)

        transactions = self.admin.execute(
            "SELECT count(DISTINCT transaction_id) FROM audit_log "
            "WHERE after_row ->> 'object_id' = %s", (target,)
        ).fetchone()[0]
        self.assertEqual(transactions, 1)

    def test_cascade_deletion_is_recorded(self) -> None:
        target = self.record + "-cascade"
        relation = self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantA') RETURNING id", (target,)
        ).fetchone()[0]
        derived = self.admin.execute(
            "SELECT count(*) FROM permissions WHERE object_id = %s", (target,)
        ).fetchone()[0]
        self.assertGreater(derived, 0)

        self.admin.execute("DELETE FROM relations WHERE id = %s", (relation,))
        deleted = self.admin.execute(
            "SELECT count(*) FROM audit_log WHERE operation = 'DELETE' "
            "AND object_table = 'permissions' AND before_row ->> 'object_id' = %s", (target,)
        ).fetchone()[0]
        self.assertEqual(deleted, derived)

    def test_update_keeps_both_versions(self) -> None:
        permission = self.admin.execute(
            "SELECT id FROM permissions WHERE object_id = %s LIMIT 1", (self.record,)
        ).fetchone()[0]
        self.admin.execute("UPDATE permissions SET allow_deny = FALSE WHERE id = %s", (permission,))
        entry = self.admin.execute(
            "SELECT before_row ->> 'allow_deny', after_row ->> 'allow_deny' FROM audit_log "
            "WHERE operation = 'UPDATE' AND object_table = 'permissions' AND row_id = %s "
            "ORDER BY id DESC LIMIT 1", (str(permission),)
        ).fetchone()
        self.assertEqual(entry, ("true", "false"))


class AuditIntegrityTests(DatabaseTest):
    def test_application_role_cannot_alter_the_log(self) -> None:
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantA')", (self.record + "-keep",)
        )
        for statement in ("DELETE FROM audit_log",
                          "UPDATE audit_log SET subject = 'rewritten'",
                          "INSERT INTO audit_log(tenant_id, occurred_at, transaction_id, "
                          "principal, session_role, operation, object_table, previous_hash, "
                          "entry_hash) VALUES ('tenantA', now(), 1, 'x', 'x', 'INSERT', 'y', "
                          "'\\x00'::bytea, '\\x00'::bytea)"):
            with self.subTest(statement=statement.split()[0]):
                with self.assertRaises(psycopg.Error):
                    self.app.execute(statement)

    def test_owner_modification_is_refused_by_the_append_only_trigger(self) -> None:
        with self.assertRaises(psycopg.errors.RaiseException):
            self.admin.execute("UPDATE audit_log SET subject = 'rewritten' WHERE id = "
                               "(SELECT min(id) FROM audit_log)")

    def test_chain_verification_locates_a_tampered_entry(self) -> None:
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantA')", (self.record + "-chain",)
        )
        self.assertEqual(
            [status for (_, _, _, status) in self.admin.execute(
                "SELECT * FROM fn_verify_audit_chain('tenantA')").fetchall()],
            ["intact"],
        )

        # Le propriétaire retire la protection puis altère : c'est le scénario que
        # la chaîne doit rendre détectable.
        target, original = self.admin.execute(
            "SELECT id, subject FROM audit_log WHERE tenant_id = 'tenantA' ORDER BY id LIMIT 1"
        ).fetchone()
        self.admin.execute("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_log_append_only_row")
        try:
            self.admin.execute("UPDATE audit_log SET subject = 'rewritten' WHERE id = %s", (target,))
            tenant, entries, broken_at, status = self.admin.execute(
                "SELECT * FROM fn_verify_audit_chain('tenantA')").fetchone()
            self.assertEqual((tenant, status, broken_at), ("tenantA", "broken", target))
            self.assertGreater(entries, 0)

            self.admin.execute("UPDATE audit_log SET subject = %s WHERE id = %s", (original, target))
            self.assertEqual(
                self.admin.execute(
                    "SELECT status FROM fn_verify_audit_chain('tenantA')").fetchone()[0],
                "intact",
            )
        finally:
            self.admin.execute("ALTER TABLE audit_log ENABLE TRIGGER trg_audit_log_append_only_row")


class AuditIdentityTests(DatabaseTest):
    def test_recorded_identity_comes_from_the_server(self) -> None:
        """Une identité revendiquée mais non déléguée n'est pas enregistrée."""
        self.app.execute("SELECT set_config('app.adam.user_id','ghost',false)")
        with self.assertRaises(psycopg.Error):
            # Sans identité résolue, la politique d'insertion refuse l'écriture.
            self.app.execute(
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,"
                "tenant_id) VALUES ('users','ghost','assigned','etapes',%s,'tenantA')",
                (self.record + "-ghost",),
            )
        self.assertEqual(
            self.admin.execute(
                "SELECT count(*) FROM audit_log WHERE subject = 'ghost'").fetchone()[0], 0
        )

    def test_entries_are_visible_only_within_their_tenant(self) -> None:
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantB')", (self.record + "-b",)
        )
        try:
            self.assertGreater(
                self.admin.execute(
                    "SELECT count(*) FROM audit_log WHERE tenant_id = 'tenantB'").fetchone()[0], 0
            )
            self.assertEqual(
                self.app.execute(
                    "SELECT count(*) FROM audit_log WHERE tenant_id <> 'tenantA'").fetchone()[0], 0
            )
            # Les entrées globales ('*', par exemple le modèle) restent invisibles.
            self.assertEqual(
                self.app.execute(
                    "SELECT count(*) FROM audit_log WHERE tenant_id = '*'").fetchone()[0], 0
            )
        finally:
            self.admin.execute("DELETE FROM roles WHERE object_id = %s", (self.record + "-b",))
            self.admin.execute("DELETE FROM relations WHERE object_id = %s", (self.record + "-b",))

    def test_decision_hook_records_without_allowing_forgery(self) -> None:
        entry = self.app.execute(
            "SELECT fn_log_decision('etapes', %s, 'read', TRUE, %s::jsonb)",
            (self.record, json.dumps({"rule": "test"})),
        ).fetchone()[0]
        recorded = self.admin.execute(
            "SELECT tenant_id, principal, subject, operation, object_table, row_id, details "
            "FROM audit_log WHERE id = %s", (entry,)
        ).fetchone()
        self.assertEqual(recorded[0], "tenantA")
        self.assertEqual(recorded[1], "read_validation")
        self.assertEqual(recorded[2], "nurse")
        self.assertEqual(recorded[3], "DECISION")
        self.assertEqual((recorded[4], recorded[5]), ("etapes", self.record))
        self.assertTrue(recorded[6]["allowed"])

        # L'appelant ne peut pas atteindre l'ajout générique.
        with self.assertRaises(psycopg.Error):
            self.app.execute(
                "SELECT fn_audit_append('tenantA','INSERT','permissions','forged',"
                "NULL,NULL,NULL)")
