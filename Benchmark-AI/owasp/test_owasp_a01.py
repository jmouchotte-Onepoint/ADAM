"""Contrôles d'accès rompus (OWASP A01:2021) sur le coeur SQL.

Chaque test rejoue une attaque qui réussissait sur l'installation antérieure à
les corrections A01 des couches 0 à 3 et 7. Les attaques sont menées depuis un
rôle PostgreSQL non privilégié (NOSUPERUSER, NOBYPASSRLS) ne disposant que des
droits d'un rôle applicatif de tenant. Les résultats avant correction sont
consignés dans Results/owasp-a01/.

Un test de référence accompagne chaque refus afin qu'aucun refus ne soit obtenu
par un déni généralisé.
"""
import json
import os

import psycopg

from support import DatabaseTest, connect


class BrokenAccessControlTests(DatabaseTest):
    # ---------------------------------------------------------------- A01-1
    def test_session_setting_cannot_forge_a_subject(self) -> None:
        other = self.record + "-other"
        self.admin.execute(
            "INSERT INTO protected_records(id, tenant_id) VALUES (%s, 'tenantA')", (other,)
        )
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','other-user','assigned','etapes',%s,'tenantA')", (other,)
        )
        try:
            # Référence : le sujet délégué accède bien à son propre dossier.
            self.assertTrue(self.visible())

            self.app.execute("SELECT set_config('app.adam.user_id','other-user',false)")
            self.assertEqual(
                self.app.execute("SELECT id FROM protected_records WHERE id = %s", (other,)).fetchall(),
                [],
            )
            # L'identité revendiquée n'étant pas déléguée, aucune identité n'est
            # résolue : le dossier légitime devient lui aussi inaccessible.
            self.assertIsNone(
                self.app.execute("SELECT get_current_user_id()").fetchone()[0]
            )
            self.assertFalse(self.visible())
        finally:
            self.admin.execute("DELETE FROM roles WHERE object_id = %s", (other,))
            self.admin.execute("DELETE FROM relations WHERE object_id = %s", (other,))
            self.admin.execute("DELETE FROM protected_records WHERE id = %s", (other,))

    # ---------------------------------------------------------------- A01-2
    def test_session_setting_cannot_switch_tenant(self) -> None:
        cross = self.record + "-tenantB"
        self.admin.execute(
            "INSERT INTO protected_records(id, tenant_id) VALUES (%s, 'tenantB')", (cross,)
        )
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantB')", (cross,)
        )
        mapped = self.admin.execute(
            "SELECT count(*) FROM tenants_per_users "
            "WHERE tenant_id='tenantB' AND pg_user='read_validation'"
        ).fetchone()[0] > 0
        self.admin.execute(
            "DELETE FROM tenants_per_users WHERE tenant_id='tenantB' AND pg_user='read_validation'"
        )
        try:
            # Le rôle n'est rattaché à aucun tenant B : la variable de session
            # ne résout aucun tenant.
            self.app.execute("SELECT set_config('app.adam.tenant_id','tenantB',false)")
            self.assertIsNone(self.app.execute("SELECT get_current_tenant_id()").fetchone()[0])
            self.assertEqual(
                self.app.execute("SELECT id FROM protected_records WHERE id = %s", (cross,)).fetchall(),
                [],
            )

            # Rattachement au tenant B, mais sans délégation du sujet 'nurse' :
            # le tenant se résout, pas l'identité.
            self.admin.execute(
                "INSERT INTO tenants_per_users(tenant_id,pg_user) VALUES ('tenantB','read_validation')"
            )
            self.assertEqual(
                self.app.execute("SELECT get_current_tenant_id()").fetchone()[0], "tenantB"
            )
            self.assertIsNone(self.app.execute("SELECT get_current_user_id()").fetchone()[0])
            self.assertEqual(
                self.app.execute("SELECT id FROM protected_records WHERE id = %s", (cross,)).fetchall(),
                [],
            )
        finally:
            self.admin.execute("DELETE FROM roles WHERE object_id = %s", (cross,))
            self.admin.execute("DELETE FROM relations WHERE object_id = %s", (cross,))
            self.admin.execute("DELETE FROM protected_records WHERE id = %s", (cross,))
            self.admin.execute(
                "DELETE FROM tenants_per_users WHERE tenant_id='tenantB' AND pg_user='read_validation'"
            )
            if mapped:
                self.admin.execute(
                    "INSERT INTO tenants_per_users(tenant_id,pg_user) "
                    "VALUES ('tenantB','read_validation')"
                )

    # ---------------------------------------------------------------- A01-3
    def test_session_setting_cannot_declare_attributes(self) -> None:
        permission = self.admin.execute(
            "SELECT id FROM permissions WHERE object_id = %s AND relation = 'can_read'",
            (self.record,),
        ).fetchone()[0]
        self.admin.execute(
            "INSERT INTO permissions_attributes(permission_id, attribute) VALUES (%s, %s::jsonb)",
            (permission, json.dumps([{"key": "profession", "operator": "IS", "value": ["nurse"]}])),
        )
        self.assertFalse(self.visible())

        self.app.execute(
            "SELECT set_config('app.adam.user_attributes', %s, false)",
            (json.dumps({"profession": "nurse"}),),
        )
        self.assertEqual(self.app.execute("SELECT get_current_user_attributes()").fetchone()[0], {})
        self.assertFalse(self.visible())

        # Référence : le même attribut, enregistré comme délégation, autorise l'accès.
        self.delegate("nurse", attributes={"profession": "nurse"})
        self.assertTrue(self.visible())

    # ---------------------------------------------------------------- A01-4
    def test_temporary_object_cannot_shadow_rule_evaluation(self) -> None:
        rule = self._attach_denying_rule()
        try:
            self.assertFalse(self.visible())
            self.app.execute(
                "CREATE TEMP VIEW view_all_access_rules AS "
                "SELECT NULL::text AS relation_type, NULL::uuid AS id, "
                "NULL::uuid AS rule_id, NULL::jsonb AS params WHERE false"
            )
            self.assertFalse(self.visible())
        finally:
            self._detach_rule(rule)

    # ---------------------------------------------------------------- A01-5
    def test_temporary_object_cannot_shadow_dynamic_rules(self) -> None:
        rule = self._attach_denying_rule()
        try:
            self.assertFalse(self.visible())
            self.app.execute(
                "CREATE TEMP TABLE dynamic_rules(id uuid, rule text, params text[], "
                "description text, creation_date timestamptz)"
            )
            self.app.execute(
                "INSERT INTO dynamic_rules SELECT id,'SELECT TRUE',params,description,creation_date "
                "FROM adam.dynamic_rules"
            )
            self.assertFalse(self.visible())
        finally:
            self._detach_rule(rule)

    # ---------------------------------------------------------------- A01-6
    def test_role_prefix_check_is_literal(self) -> None:
        self.admin.execute("DROP ROLE IF EXISTS deletewildcard")
        self.admin.execute("DROP ROLE IF EXISTS delete_wildcard")
        self.admin.execute("CREATE ROLE deletewildcard NOSUPERUSER NOBYPASSRLS")
        self.admin.execute("CREATE ROLE delete_wildcard NOSUPERUSER NOBYPASSRLS")
        self.admin.execute("GRANT USAGE ON SCHEMA adam TO deletewildcard, delete_wildcard")
        try:
            # 'deletewildcard' satisfaisait LIKE 'delete_%', où '_' est un joker.
            self.assertTrue(self.admin.execute("SELECT 'deletewildcard' LIKE 'delete_%'").fetchone()[0])
            for role, expected in (("deletewildcard", False), ("delete_wildcard", True)):
                with self.subTest(role=role):
                    self.admin.execute(f"SET ROLE {role}")
                    try:
                        self.assertEqual(
                            self.admin.execute("SELECT is_allow('delete')").fetchone()[0], expected
                        )
                    finally:
                        self.admin.execute("RESET ROLE")
        finally:
            self.admin.execute("REVOKE ALL ON SCHEMA adam FROM deletewildcard, delete_wildcard")
            self.admin.execute("DROP ROLE IF EXISTS deletewildcard")
            self.admin.execute("DROP ROLE IF EXISTS delete_wildcard")

    # ---------------------------------------------------------------- A01-7
    def test_policy_metadata_is_not_readable_across_tenants(self) -> None:
        foreign = self.record + "-tenantB"
        self.admin.execute(
            "INSERT INTO protected_records(id, tenant_id) VALUES (%s, 'tenantB')", (foreign,)
        )
        self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','doctorB','assigned','etapes',%s,'tenantB')", (foreign,)
        )
        self.admin.execute(
            """INSERT INTO permissions_attributes(permission_id, attribute)
               SELECT id, '[{"key":"tenantB_secret","operator":"IS","value":["confidential"]}]'::jsonb
               FROM permissions WHERE object_id = %s AND relation = 'can_read'""",
            (foreign,),
        )
        try:
            for relation in ("view_all_access_attributes", "permissions_attributes"):
                with self.subTest(relation=relation):
                    self.assertEqual(
                        self.app.execute(
                            f"SELECT count(*) FROM {relation} "
                            "WHERE attribute::text LIKE '%tenantB_secret%'"
                        ).fetchone()[0],
                        0,
                    )
            # Référence : les métadonnées du tenant du sujet restent lisibles.
            own = self.admin.execute(
                "SELECT id FROM permissions WHERE object_id = %s AND relation = 'can_read'",
                (self.record,),
            ).fetchone()[0]
            self.admin.execute(
                """INSERT INTO permissions_attributes(permission_id, attribute)
                   VALUES (%s, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb)""",
                (own,),
            )
            self.assertEqual(
                self.app.execute(
                    "SELECT count(*) FROM view_all_access_attributes WHERE id = %s", (own,)
                ).fetchone()[0],
                1,
            )
        finally:
            self.admin.execute("DELETE FROM roles WHERE object_id = %s", (foreign,))
            self.admin.execute("DELETE FROM relations WHERE object_id = %s", (foreign,))
            self.admin.execute("DELETE FROM protected_records WHERE id = %s", (foreign,))

    # ---------------------------------------------------------------- A01-8
    def test_runtime_role_invariant_is_verifiable(self) -> None:
        def violations(role: str) -> set[str]:
            return {
                kind for (kind,) in
                self.admin.execute("SELECT violation FROM fn_check_runtime_role(%s)", (role,)).fetchall()
            }

        self.assertEqual(violations("read_validation"), set())
        self.assertEqual(violations("no_such_role"), {"unknown_role"})
        self.assertIn("superuser", violations("postgres"))

        self.admin.execute("DROP ROLE IF EXISTS graph_owner")
        self.admin.execute("CREATE ROLE graph_owner NOSUPERUSER NOBYPASSRLS")
        self.admin.execute("GRANT USAGE ON SCHEMA adam TO graph_owner")
        self.admin.execute("ALTER TABLE adam.permissions OWNER TO graph_owner")
        try:
            self.assertIn("owns_rls_table", violations("graph_owner"))
        finally:
            self.admin.execute("ALTER TABLE adam.permissions OWNER TO postgres")
            self.admin.execute("REVOKE ALL ON SCHEMA adam FROM graph_owner")
            self.admin.execute("DROP ROLE IF EXISTS graph_owner")

    # ------------------------------------------------------------------ util
    def _attach_denying_rule(self) -> str:
        rule = self.admin.execute(
            "INSERT INTO dynamic_rules(description, rule, params) "
            "VALUES ('owasp-a01-deny','SELECT FALSE',ARRAY[]::text[]) RETURNING id"
        ).fetchone()[0]
        self.admin.execute(
            "INSERT INTO permissions_rules(permission_id, rule_id) "
            "SELECT id, %s FROM permissions WHERE object_id = %s AND relation = 'can_read'",
            (rule, self.record),
        )
        return rule

    def _detach_rule(self, rule: str) -> None:
        self.admin.execute("DELETE FROM permissions_rules WHERE rule_id = %s", (rule,))
        self.admin.execute("DELETE FROM dynamic_rules WHERE id = %s", (rule,))


class DerivationShadowingTests(DatabaseTest):
    """A01-9 : la dérivation du graphe doit suivre le modèle configuré.

    Les fonctions de trigger résolvaient `model` sans schéma. Un rôle applicatif
    disposant des droits d'écriture du déploiement livré pouvait donc substituer
    sa propre table `model` et faire matérialiser des permissions absentes du
    modèle. Les clés étrangères ne contraignent que la valeur de model_id.
    """

    def setUp(self) -> None:
        super().setUp()
        self.admin.execute("DROP ROLE IF EXISTS graphwriter")
        self.admin.execute("CREATE ROLE graphwriter LOGIN NOSUPERUSER NOBYPASSRLS")
        self.admin.execute("GRANT USAGE ON SCHEMA adam TO graphwriter")
        self.admin.execute("GRANT SELECT ON ALL TABLES IN SCHEMA adam TO graphwriter")
        self.admin.execute("GRANT INSERT ON relations, roles, permissions TO graphwriter")
        self.admin.execute(
            "INSERT INTO tenants_per_users(tenant_id, pg_user) VALUES ('tenantA','graphwriter') "
            "ON CONFLICT DO NOTHING"
        )
        self.target = self.record + "-derivation"

    def tearDown(self) -> None:
        self.admin.execute("DELETE FROM permissions WHERE object_id = %s", (self.target,))
        self.admin.execute("DELETE FROM roles WHERE object_id = %s", (self.target,))
        self.admin.execute("DELETE FROM relations WHERE object_id = %s", (self.target,))
        self.admin.execute("DELETE FROM tenants_per_users WHERE pg_user = 'graphwriter'")
        self.admin.execute("REVOKE ALL ON ALL TABLES IN SCHEMA adam FROM graphwriter")
        self.admin.execute("REVOKE ALL ON SCHEMA adam FROM graphwriter")
        self.admin.execute("DROP ROLE IF EXISTS graphwriter")
        super().tearDown()

    def _writer(self) -> psycopg.Connection:
        connection = psycopg.connect(
            os.environ["ADAM_VALIDATION_DSN"], user="graphwriter", autocommit=True,
            options="-c search_path=adam,public",
        )
        connection.execute(
            "SELECT set_config('app.adam.user_id','intruder',false), "
            "set_config('app.adam.tenant_id','tenantA',false), "
            "set_config('app.adam.user_attributes','{}',false)"
        )
        return connection

    def _insert_relation(self, connection: psycopg.Connection) -> None:
        connection.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','intruder','assigned','etapes',%s,'tenantA')", (self.target,)
        )

    def _derived(self, relation: str | None = None) -> int:
        query = "SELECT count(*) FROM permissions WHERE object_id = %s"
        parameters: tuple = (self.target,)
        if relation is not None:
            query += " AND relation = %s"
            parameters += (relation,)
        return self.admin.execute(query, parameters).fetchone()[0]

    def test_temporary_model_cannot_add_an_unmodelled_permission(self) -> None:
        model_id = self.admin.execute(
            "SELECT id FROM model WHERE relation = 'can_read' AND relation_type = 'PERMISSIONS'"
        ).fetchone()[0]
        self.assertEqual(
            self.admin.execute(
                "SELECT count(*) FROM model WHERE relation = 'can_exfiltrate'").fetchone()[0], 0
        )
        with self._writer() as writer:
            writer.execute("CREATE TEMP TABLE model (LIKE adam.model INCLUDING DEFAULTS)")
            for relation_type, relation in (("RELATIONS", "assigned"),
                                            ("PERMISSIONS", "can_exfiltrate")):
                writer.execute(
                    "INSERT INTO model(id, relation_type, relation_source, user_type, relation, "
                    "object_type) VALUES (%s,%s,'assigned','users',%s,'etapes')",
                    (model_id, relation_type, relation),
                )
            self._insert_relation(writer)

        # Référence : la dérivation conforme au modèle a bien eu lieu.
        self.assertGreater(self._derived(), 0)
        self.assertEqual(self._derived("can_exfiltrate"), 0)

    def test_modelled_derivation_is_unaffected(self) -> None:
        expected = self.admin.execute(
            "SELECT count(*) FROM model WHERE relation_source = 'assigned' "
            "AND object_type = 'etapes' AND relation_type = 'PERMISSIONS'"
        ).fetchone()[0]
        with self._writer() as writer:
            self._insert_relation(writer)
        self.assertEqual(self._derived(), expected)


class UnboundPrincipalTests(DatabaseTest):
    """Un rôle sans délégation agit sous son propre nom, jamais sous celui demandé."""

    def test_principal_without_delegation_acts_under_its_own_name(self) -> None:
        self.admin.execute("DELETE FROM users_per_pg_user WHERE pg_user = 'read_validation'")
        with connect(application=True) as app:
            app.execute("SELECT set_config('app.adam.user_id','nurse',false)")
            self.assertEqual(
                app.execute("SELECT get_current_user_id()").fetchone()[0], "read_validation"
            )
            self.assertFalse(self.visible(app))
