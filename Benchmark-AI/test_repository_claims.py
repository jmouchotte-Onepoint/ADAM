from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import psycopg
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Examples.generator.models import init_model
from support import DatabaseTest, connect


class RepositoryClaimTests(DatabaseTest):
    def test_generated_policy_allows_only_the_target_record(self) -> None:
        other = self.record + "-other"
        self.admin.execute("INSERT INTO parcours.etapes(id, tenant_id) VALUES (%s, 'tenantA')", (other,))
        try:
            rows = self.app.execute(
                "SELECT id FROM parcours.etapes WHERE id IN (%s, %s)", (self.record, other)
            ).fetchall()
            self.assertEqual(rows, [(self.record,)])
        finally:
            self.admin.execute("DELETE FROM parcours.etapes WHERE id = %s", (other,))

    def test_generator_produces_a_working_policy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "Examples/Woodgrove/init-models.yml").read_text()
        model = yaml.safe_load(source.replace("type ", "").replace("define ", ""))["models"]
        with TemporaryDirectory() as directory:
            paths = [str(Path(directory) / f"{name}.sql") for name in ("model", "rules", "rls")]
            init_model(model, *paths)
            generated_policy = Path(paths[2]).read_text()
            self.admin.execute("DROP POLICY adam_policy_select_parcours_etapes ON parcours.etapes")
            try:
                self.admin.execute(generated_policy)
                self.admin.execute(generated_policy)
                self.assertEqual(
                    self.app.execute("SELECT id FROM parcours.etapes WHERE id = %s", (self.record,)).fetchall(),
                    [(self.record,)],
                )
                self.app.execute("SELECT set_config('app.adam.user_id','other-user',false)")
                self.assertEqual(
                    self.app.execute("SELECT id FROM parcours.etapes WHERE id = %s", (self.record,)).fetchall(),
                    [],
                )
                self.app.execute("SELECT set_config('app.adam.user_id','nurse',false)")
                self.admin.execute(
                    "UPDATE permissions SET expires_at = statement_timestamp() - interval '1 second' "
                    "WHERE object_id = %s", (self.record,)
                )
                self.assertEqual(
                    self.app.execute("SELECT id FROM parcours.etapes WHERE id = %s", (self.record,)).fetchall(),
                    [],
                )
            finally:
                self.admin.execute("DROP POLICY IF EXISTS adam_policy_select_parcours_etapes ON parcours.etapes")
                self.admin.execute((root / "ADAM/4_INSERT/INSERT-RLS-POLICY.sql").read_text())

    def test_generated_policy_rejects_another_subject(self) -> None:
        self.app.execute("SELECT set_config('app.adam.user_id','unrelated-user',false)")
        self.assertEqual(
            self.app.execute("SELECT id FROM parcours.etapes WHERE id = %s", (self.record,)).fetchall(), []
        )

    def test_generated_policy_rejects_expired_permission(self) -> None:
        self.admin.execute(
            "UPDATE permissions SET expires_at = statement_timestamp() - interval '1 second' "
            "WHERE object_id = %s", (self.record,)
        )
        self.assertEqual(
            self.app.execute("SELECT id FROM parcours.etapes WHERE id = %s", (self.record,)).fetchall(), []
        )

    def test_unique_index_rejects_duplicate_null_parent(self) -> None:
        self.admin.execute(
            "UPDATE roles SET parent_relation_id = NULL WHERE object_id = %s", (self.record,)
        )
        self.admin.execute(
            "INSERT INTO roles(user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
            "parent_relation_id,is_auto_generated) "
            "SELECT user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
            "NULL,TRUE FROM roles WHERE object_id = %s ON CONFLICT DO NOTHING", (self.record,)
        )
        self.assertEqual(
            self.admin.execute("SELECT count(*) FROM roles WHERE object_id = %s", (self.record,)).fetchone()[0], 4
        )

    def test_unique_index_preserves_distinct_parent_paths(self) -> None:
        other_seed = self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','other-user','assigned','etapes',%s,'tenantA') RETURNING id", (self.record,)
        ).fetchone()[0]
        self.admin.execute(
            "INSERT INTO roles(user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
            "parent_relation_id,is_auto_generated) "
            "SELECT user_type,user_id,relation,object_type,object_id,tenant_id,model_id,%s,TRUE "
            "FROM roles WHERE object_id = %s AND user_id = 'nurse' AND relation = 'role_1'",
            (other_seed, self.record),
        )
        self.assertEqual(
            self.admin.execute(
                "SELECT count(*) FROM roles WHERE object_id = %s AND user_id = 'nurse' AND relation = 'role_1'",
                (self.record,),
            ).fetchone()[0], 2
        )

    def test_permission_index_rejects_duplicate_null_parent(self) -> None:
        self.admin.execute("UPDATE permissions SET parent_relation_id = NULL WHERE object_id = %s", (self.record,))
        self.admin.execute(
            "INSERT INTO permissions(user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
            "parent_relation_id,is_auto_generated) "
            "SELECT user_type,user_id,relation,object_type,object_id,tenant_id,model_id,NULL,TRUE "
            "FROM permissions WHERE object_id = %s ON CONFLICT DO NOTHING", (self.record,)
        )
        self.assertEqual(
            self.admin.execute("SELECT count(*) FROM permissions WHERE object_id = %s", (self.record,)).fetchone()[0],
            21,
        )

    def test_index_rejects_duplicate_null_parent_roles(self) -> None:
        with connect(autocommit=False) as transaction:
            transaction.execute("UPDATE roles SET parent_relation_id = NULL WHERE object_id = %s", (self.record,))
            with self.assertRaises(psycopg.errors.UniqueViolation):
                transaction.execute(
                    "INSERT INTO roles(user_type,user_id,relation,object_type,object_id,tenant_id,model_id,"
                    "parent_relation_id,is_auto_generated) "
                    "SELECT user_type,user_id,relation,object_type,object_id,tenant_id,model_id,NULL,TRUE "
                    "FROM roles WHERE object_id = %s", (self.record,)
                )
            transaction.rollback()

    def test_attribute_wrapper_evaluates_declared_constraint(self) -> None:
        permission = self.admin.execute(
            "SELECT id FROM permissions WHERE object_id = %s AND relation = 'can_read'", (self.record,)
        ).fetchone()[0]
        self.admin.execute(
            """INSERT INTO permissions_attributes(permission_id, attribute)
            VALUES (%s, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb)""",
            (permission,),
        )
        self.assertIs(
            self.app.execute(
                "SELECT fn_check_all_attributes_from_view(%s, 'permissions', '{}'::jsonb)", (permission,)
            ).fetchone()[0],
            False,
        )
        self.assertIs(
            self.app.execute(
                "SELECT fn_check_all_attributes_from_view(%s, 'PERMISSIONS', %s::jsonb)",
                (permission, '{"profession":"nurse"}'),
            ).fetchone()[0],
            True,
        )
        with self.assertRaises(psycopg.errors.RaiseException):
            self.app.execute(
                "SELECT fn_check_all_attributes_from_view(%s, 'invalid', '{}'::jsonb)", (permission,)
            )
