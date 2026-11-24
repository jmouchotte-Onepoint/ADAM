from uuid import UUID

from psycopg import sql

from support import DatabaseTest, connect


class ClinicalReplayTests(DatabaseTest):
    def test_synthetic_pathway_and_negative_controls(self) -> None:
        records = {name: f"{self.record}-{name}" for name in ("med", "clinical", "psych", "discharge")}
        phase_table = sql.Identifier("case_phase_" + self.record.removeprefix("parcours-"))
        try:
            self.admin.execute(sql.SQL("CREATE TABLE {} (state TEXT NOT NULL)").format(phase_table))
            self.admin.execute(sql.SQL("INSERT INTO {} VALUES ('inpatient')").format(phase_table))
            for record in records.values():
                self.admin.execute(
                    "INSERT INTO protected_records(id,tenant_id) VALUES (%s,'tenantA')", (record,)
                )

            def identity(subject: str, attributes: dict | None = None) -> None:
                # Le sujet et ses attributs sont enregistrés comme délégation du
                # rôle PostgreSQL ; la variable de session ne fait que désigner
                # laquelle de ces identités la requête utilise.
                self.delegate(subject, attributes=attributes)
                self.app.execute(
                    "SELECT set_config('app.adam.user_id',%s,false)", (subject,)
                )

            def grant(subject: str, record: str) -> UUID:
                return self.admin.execute(
                    "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                    "VALUES ('users',%s,'assigned','etapes',%s,'tenantA') RETURNING id",
                    (subject, record),
                ).fetchone()[0]

            def visible(record: str) -> bool:
                return bool(self.app.execute(
                    "SELECT id FROM protected_records WHERE id=%s", (record,)
                ).fetchall())

            def update(record: str) -> bool:
                return self.app.execute(
                    "UPDATE protected_records SET value=value+1 WHERE id=%s", (record,)
                ).rowcount == 1

            identity("case-nurse")
            self.assertFalse(update(records["med"]))
            delegation = grant("case-nurse", records["med"])
            self.admin.execute(
                "UPDATE relations SET expires_at=statement_timestamp()+interval '1 hour' WHERE id=%s",
                (delegation,),
            )
            self.assertTrue(update(records["med"]))

            grant("case-emergency", records["clinical"])
            self.admin.execute(
                "DELETE FROM permissions WHERE object_id=%s AND relation='can_write'",
                (records["clinical"],),
            )
            self.admin.execute(
                """INSERT INTO permissions_attributes(permission_id,attribute)
                   SELECT id, '[{"key":"emergency","operator":"IS","value":["true"]}]'::jsonb
                   FROM permissions WHERE object_id=%s AND relation='can_read'""",
                (records["clinical"],),
            )
            identity("case-emergency", {"emergency": False})
            self.assertFalse(visible(records["clinical"]))
            identity("case-emergency", {"emergency": True})
            self.assertTrue(visible(records["clinical"]))
            self.assertFalse(update(records["clinical"]))

            grant("case-rehab", records["psych"])
            identity("case-rehab")
            self.assertTrue(visible(records["psych"]))
            self.admin.execute("UPDATE protected_records SET consent=FALSE WHERE id=%s", (records["psych"],))
            self.assertFalse(visible(records["psych"]))

            identity("case-nurse")
            self.admin.execute(
                "UPDATE relations SET expires_at=statement_timestamp()-interval '1 second' WHERE id=%s",
                (delegation,),
            )
            self.assertFalse(update(records["med"]))
            self.assertGreater(self.admin.execute(
                "SELECT count(*) FROM permissions WHERE parent_relation_id=%s", (delegation,)
            ).fetchone()[0], 0)

            identity("case-coordinator")
            self.assertFalse(update(records["discharge"]))
            with connect(autocommit=False) as transaction:
                transaction.execute(sql.SQL("UPDATE {} SET state='home-follow-up'").format(phase_table))
                transaction.execute(
                    "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                    "VALUES ('users','case-coordinator','assigned','etapes',%s,'tenantA')",
                    (records["discharge"],),
                )
                self.assertFalse(update(records["discharge"]))
                self.assertEqual(self.admin.execute(
                    sql.SQL("SELECT state FROM {}").format(phase_table)).fetchone()[0], "inpatient")
                transaction.commit()
                self.assertEqual(self.admin.execute(
                    sql.SQL("SELECT state FROM {}").format(phase_table)).fetchone()[0], "home-follow-up")
                self.assertTrue(update(records["discharge"]))
        finally:
            for record in records.values():
                self.admin.execute("DELETE FROM roles WHERE object_id=%s", (record,))
                self.admin.execute("DELETE FROM relations WHERE object_id=%s", (record,))
                self.admin.execute("DELETE FROM protected_records WHERE id=%s", (record,))
            self.admin.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(phase_table))
