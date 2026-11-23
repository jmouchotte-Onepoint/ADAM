import psycopg

from support import DatabaseTest


class LifecycleTests(DatabaseTest):
    def test_materialization_and_cascade(self) -> None:
        self.assertEqual(
            self.admin.execute("SELECT count(*) FROM roles WHERE object_id = %s", (self.record,)).fetchone()[0], 4
        )
        self.assertEqual(
            self.admin.execute("SELECT count(*) FROM permissions WHERE object_id = %s", (self.record,)).fetchone()[0], 21
        )
        self.admin.execute("DELETE FROM relations WHERE id = %s", (self.seed,))
        self.assertFalse(self.visible())
        self.assertEqual(
            self.admin.execute("SELECT count(*) FROM permissions WHERE object_id = %s", (self.record,)).fetchone()[0], 0
        )

    def test_duplicate_seed_rejected(self) -> None:
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.admin.execute(
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                "VALUES ('users','nurse','assigned','etapes',%s,'tenantA')", (self.record,)
            )
        self.assertTrue(self.visible())

    def test_unknown_model_rejected(self) -> None:
        with self.assertRaises(psycopg.Error):
            self.app.execute(
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                "VALUES ('users','nurse','unknown-model','etapes',%s,'tenantA')", (self.record,)
            )
        self.assertTrue(self.visible())
