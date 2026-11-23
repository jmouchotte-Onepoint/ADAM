import json

from support import DatabaseTest


class AttributeEquivalenceTests(DatabaseTest):
    def test_targeted_wrapper_matches_view_for_local_and_inherited_constraints(self) -> None:
        permission = self.admin.execute(
            "SELECT id FROM permissions WHERE parent_relation_id=%s AND relation='can_read'",
            (self.seed,),
        ).fetchone()[0]
        profession = json.dumps([{"key": "profession", "operator": "IS", "value": ["nurse"]}])
        emergency = json.dumps([{"key": "emergency", "operator": "IS", "value": ["true"]}])

        def compare(attributes: dict, expected: bool) -> None:
            row = self.app.execute(
                """SELECT
                   NOT EXISTS (SELECT 1 FROM view_all_access_attributes a
                               WHERE a.id=%s AND a.relation_type='permissions'
                               AND fn_check_attributes(%s::jsonb,a.attribute) IS NOT TRUE),
                   fn_check_all_attributes_from_view(%s,'permissions',%s::jsonb) IS TRUE""",
                (permission, json.dumps(attributes), permission, json.dumps(attributes)),
            ).fetchone()
            self.assertEqual(row, (expected, expected))

        compare({}, True)
        self.admin.execute(
            "INSERT INTO permissions_attributes(permission_id,attribute) VALUES (%s,%s::jsonb)",
            (permission, profession),
        )
        compare({}, False)
        compare({"profession": "nurse"}, True)
        self.admin.execute(
            "INSERT INTO relations_attributes(relation_id,is_inheritable,attribute) "
            "VALUES (%s,FALSE,%s::jsonb)", (self.seed, emergency)
        )
        compare({"profession": "nurse"}, True)
        self.admin.execute(
            "UPDATE relations_attributes SET is_inheritable=TRUE WHERE relation_id=%s", (self.seed,)
        )
        compare({"profession": "nurse"}, False)
        compare({"profession": "nurse", "emergency": True}, True)
        compare({"profession": "doctor", "emergency": True}, False)
