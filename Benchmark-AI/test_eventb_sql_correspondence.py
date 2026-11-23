from itertools import product

from support import DatabaseTest


class EventBSQLCorrespondenceTests(DatabaseTest):
    def test_finite_instances_with_subject_metadata_and_tenant_scope(self) -> None:
        subjects = {"model-alice": "tenantA", "model-bob": "tenantA",
                    "model-carol": "tenantB", "model-dave": "tenantB"}
        records = {f"{self.record}-{tenant}-{i}": tenant for tenant, i in
                   product(("tenantA", "tenantB"), range(2))}
        grant_pairs = {("model-alice", f"{self.record}-tenantA-0"),
                       ("model-bob", f"{self.record}-tenantA-1"),
                       ("model-carol", f"{self.record}-tenantB-0")}
        try:
            self.admin.execute(
                "INSERT INTO tenants_per_users(tenant_id,pg_user) VALUES ('tenantB','read_validation')"
            )
            for record, tenant in records.items():
                self.admin.execute(
                    "INSERT INTO protected_records(id,tenant_id) VALUES (%s,%s)", (record, tenant)
                )
            for subject, record in grant_pairs:
                self.admin.execute(
                    "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                    "VALUES ('users',%s,'assigned','etapes',%s,%s)",
                    (subject, record, records[record]),
                )
            self.admin.execute(
                "DELETE FROM permissions WHERE user_id='model-bob' AND object_id=%s AND relation='can_write'",
                (f"{self.record}-tenantA-1",),
            )
            write_pairs = grant_pairs - {("model-bob", f"{self.record}-tenantA-1")}
            for subject, record, operation in product(subjects, records, ("read", "write")):
                tenant = subjects[subject]
                self.app.execute(
                    "SELECT set_config('app.adam.user_id',%s,false), "
                    "set_config('app.adam.tenant_id',%s,false)", (subject, tenant)
                )
                if operation == "read":
                    observed = bool(self.app.execute(
                        "SELECT id FROM protected_records WHERE id=%s", (record,)
                    ).fetchall())
                else:
                    observed = self.app.execute(
                        "UPDATE protected_records SET value=value+1 WHERE id=%s", (record,)
                    ).rowcount == 1
                # Empty data metadata; auth metadata contains the grant subject.
                read_allowed = records[record] == tenant and (subject, record) in grant_pairs
                expected = read_allowed and (operation == "read" or (subject, record) in write_pairs)
                with self.subTest(subject=subject, record=record, operation=operation):
                    self.assertEqual(observed, expected)

            subject, record = "model-alice", f"{self.record}-tenantA-0"
            self.admin.execute("DELETE FROM relations WHERE user_id=%s AND object_id=%s", (subject, record))
            self.app.execute(
                "SELECT set_config('app.adam.user_id',%s,false), "
                "set_config('app.adam.tenant_id','tenantA',false)", (subject,)
            )
            self.assertFalse(self.app.execute(
                "SELECT id FROM protected_records WHERE id=%s", (record,)
            ).fetchall())
        finally:
            for record in records:
                self.admin.execute("DELETE FROM roles WHERE object_id=%s", (record,))
                self.admin.execute("DELETE FROM relations WHERE object_id=%s", (record,))
                self.admin.execute("DELETE FROM protected_records WHERE id=%s", (record,))
            self.admin.execute(
                "DELETE FROM tenants_per_users WHERE tenant_id='tenantB' AND pg_user='read_validation'"
            )
