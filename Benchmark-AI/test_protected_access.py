import json

from support import DatabaseTest


class ProtectedAccessTests(DatabaseTest):
    def test_read_write_and_persistence(self) -> None:
        self.assertTrue(self.visible())
        self.app.execute("UPDATE protected_records SET value = 7 WHERE id = %s", (self.record,))
        self.assertEqual(
            self.admin.execute("SELECT value FROM protected_records WHERE id = %s", (self.record,)).fetchone()[0],
            7,
        )
        self.admin.execute(
            "DELETE FROM permissions WHERE object_id = %s AND relation = 'can_write'", (self.record,)
        )
        self.assertEqual(
            self.app.execute("UPDATE protected_records SET value = 8 WHERE id = %s", (self.record,)).rowcount,
            0,
        )

    def test_wrong_subject_missing_identity_and_wrong_tenant(self) -> None:
        self.assertTrue(self.visible())
        for key, value in [
            ("app.adam.user_id", "other-user"),
            ("app.adam.user_id", ""),
            ("app.adam.tenant_id", "tenantB"),
        ]:
            with self.subTest(key=key, value=value):
                self.app.execute("SELECT set_config(%s, %s, false)", (key, value))
                self.assertFalse(self.visible())
                self.app.execute(
                    "SELECT set_config('app.adam.user_id','nurse',false), "
                    "set_config('app.adam.tenant_id','tenantA',false)"
                )

    def test_attribute_required_at_read_time(self) -> None:
        permission = self.admin.execute(
            "SELECT id FROM permissions WHERE object_id = %s AND relation = 'can_read'", (self.record,)
        ).fetchone()[0]
        rule = [{"key": "profession", "operator": "IS", "value": ["nurse"]}]
        self.admin.execute(
            "INSERT INTO permissions_attributes(permission_id, attribute) VALUES (%s, %s::jsonb)",
            (permission, json.dumps(rule)),
        )
        self.assertFalse(self.visible())
        # L'attribut provient de la délégation enregistrée, pas d'une déclaration
        # faite par la session : voir test_owasp_a01.py pour le contre-exemple.
        self.delegate("nurse", attributes={"profession": "nurse"})
        self.assertTrue(self.visible())

    def test_consent_and_expiration_without_cleanup(self) -> None:
        self.assertTrue(self.visible())
        self.admin.execute("UPDATE protected_records SET consent = FALSE WHERE id = %s", (self.record,))
        self.assertFalse(self.visible())
        self.admin.execute("UPDATE protected_records SET consent = TRUE WHERE id = %s", (self.record,))
        self.admin.execute(
            "UPDATE relations SET expires_at = statement_timestamp() - interval '1 second' WHERE id = %s",
            (self.seed,),
        )
        self.assertFalse(self.visible())
        self.assertEqual(
            self.admin.execute("SELECT count(*) FROM permissions WHERE object_id = %s", (self.record,)).fetchone()[0],
            21,
        )
