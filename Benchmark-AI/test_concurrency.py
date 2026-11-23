import psycopg

from support import DatabaseTest, connect


class ConcurrencyTests(DatabaseTest):
    def test_read_committed_observes_committed_revocation(self) -> None:
        with connect(autocommit=False) as writer:
            writer.execute("DELETE FROM relations WHERE id = %s", (self.seed,))
            self.assertTrue(self.visible())
            writer.commit()
        self.assertFalse(self.visible())

    def test_repeatable_read_keeps_old_snapshot(self) -> None:
        with connect(application=True) as reader:
            reader.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            self.assertTrue(self.visible(reader))
            self.admin.execute("DELETE FROM relations WHERE id = %s", (self.seed,))
            self.assertFalse(self.visible())
            self.assertTrue(self.visible(reader))
            reader.execute("COMMIT")
            self.assertFalse(self.visible(reader))

    def test_consent_withdrawal_is_visible_after_commit_in_read_committed(self) -> None:
        with connect(autocommit=False) as writer:
            writer.execute("UPDATE protected_records SET consent = FALSE WHERE id = %s", (self.record,))
            self.assertTrue(self.visible())
            writer.commit()
        self.assertFalse(self.visible())
        self.assertEqual(
            self.app.execute("UPDATE protected_records SET value = 9 WHERE id = %s", (self.record,)).rowcount, 0
        )

    def test_consent_withdrawal_keeps_snapshot_but_blocks_stale_write(self) -> None:
        with connect(application=True) as reader:
            reader.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            self.assertTrue(self.visible(reader))
            self.admin.execute("UPDATE protected_records SET consent = FALSE WHERE id = %s", (self.record,))
            self.assertFalse(self.visible())
            self.assertTrue(self.visible(reader))
            with self.assertRaises(psycopg.errors.SerializationFailure):
                reader.execute("UPDATE protected_records SET value = 9 WHERE id = %s", (self.record,))
            reader.execute("ROLLBACK")
            self.assertFalse(self.visible(reader))
