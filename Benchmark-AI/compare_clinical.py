import json
from uuid import UUID

import psycopg

from compare_authorization import API
from support import connect


def replay(fga: API, spice: API) -> list[dict]:
    store = fga.post("/stores", {"name": "adam-clinical-replay"})["id"]
    relations = {name: {"this": {}} for name in ("reader", "writer")}
    metadata = {name: {"directly_related_user_types": [{"type": "user"}]}
                for name in relations}
    model = fga.post(f"/stores/{store}/authorization-models", {
        "schema_version": "1.1",
        "type_definitions": [{"type": "user"}, {"type": "record", "relations": relations,
                                                  "metadata": {"relations": metadata}}],
    })["authorization_model_id"]
    spice.post("/v1/schema/write", {
        "schema": "definition user {}\n"
                  "definition record {\n"
                  " relation assigned: user\n relation reader: user\n relation writer: user\n"
                  " permission can_read = assigned\n"
                  " permission case_read = reader\n permission case_write = writer\n}\n",
    })
    records = {name: f"case-{name}" for name in ("med", "clinical", "psych", "discharge")}
    results: list[dict] = []

    def tuple_for(user: str, record: str, operation: str) -> dict:
        return {"user": f"user:{user}", "relation": "reader" if operation == "read" else "writer",
                "object": f"record:{record}"}

    def relationship(user: str, record: str, operation: str) -> dict:
        return {"resource": {"objectType": "record", "objectId": record},
                "relation": "reader" if operation == "read" else "writer",
                "subject": {"object": {"objectType": "user", "objectId": user}}}

    def service_grant(user: str, record: str, operation: str, grant: bool) -> None:
        key = "writes" if grant else "deletes"
        fga.post(f"/stores/{store}/write", {
            "authorization_model_id": model,
            key: {"tuple_keys": [tuple_for(user, record, operation)]},
        })
        spice.post("/v1/relationships/write", {"updates": [{
            "operation": "OPERATION_CREATE" if grant else "OPERATION_DELETE",
            "relationship": relationship(user, record, operation),
        }]})

    def sql_grant(admin: psycopg.Connection, user: str, record: str) -> UUID:
        return admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users',%s,'assigned','etapes',%s,'tenantA') RETURNING id",
            (user, record),
        ).fetchone()[0]

    def check(label: str, user: str, record: str, operation: str, expected: bool,
              attributes: dict | None = None) -> None:
        with connect(application=True) as db:
            db.execute("SELECT set_config('app.adam.user_id',%s,false), "
                       "set_config('app.adam.user_attributes',%s,false)",
                       (user, json.dumps(attributes or {})))
            if operation == "read":
                actual = bool(db.execute(
                    "SELECT id FROM protected_records WHERE id=%s", (record,)
                ).fetchall())
            else:
                actual = db.execute(
                    "UPDATE protected_records SET value=value+1 WHERE id=%s", (record,)
                ).rowcount == 1
        fga_result = fga.post(f"/stores/{store}/check", {
            "authorization_model_id": model, "tuple_key": tuple_for(user, record, operation),
            "consistency": "HIGHER_CONSISTENCY",
        })["allowed"]
        spice_result = spice.post("/v1/permissions/check", {
            "consistency": {"fullyConsistent": True},
            "resource": {"objectType": "record", "objectId": record},
            "permission": "case_read" if operation == "read" else "case_write",
            "subject": {"object": {"objectType": "user", "objectId": user}},
        })["permissionship"]
        if spice_result not in ("PERMISSIONSHIP_HAS_PERMISSION", "PERMISSIONSHIP_NO_PERMISSION"):
            raise RuntimeError(f"Unexpected SpiceDB permissionship: {spice_result}")
        observed = (actual, fga_result, spice_result == "PERMISSIONSHIP_HAS_PERMISSION")
        if observed != (expected, expected, expected):
            raise AssertionError(f"{label}: expected {expected}, got {observed}")
        results.append({"case": label, "subject": user, "record": record, "operation": operation,
                        "expected": expected, "adam": actual, "openfga": fga_result,
                        "spicedb": observed[2]})

    with connect() as admin:
        for record in records.values():
            admin.execute("INSERT INTO protected_records(id,tenant_id) VALUES (%s,'tenantA')", (record,))

        check("T0 before delegation", "case-nurse", records["med"], "write", False)
        delegation = sql_grant(admin, "case-nurse", records["med"])
        admin.execute("UPDATE relations SET expires_at=statement_timestamp()+interval '1 hour' WHERE id=%s",
                      (delegation,))
        for op in ("read", "write"):
            service_grant("case-nurse", records["med"], op, True)
        check("T0 active delegation", "case-nurse", records["med"], "write", True)

        sql_grant(admin, "case-emergency", records["clinical"])
        admin.execute("DELETE FROM permissions WHERE object_id=%s AND relation='can_write'",
                      (records["clinical"],))
        admin.execute(
            """INSERT INTO permissions_attributes(permission_id,attribute)
               SELECT id, '[{"key":"emergency","operator":"IS","value":["true"]}]'::jsonb
               FROM permissions WHERE object_id=%s AND relation='can_read'""", (records["clinical"],))
        check("T1 emergency inactive", "case-emergency", records["clinical"], "read", False,
              {"emergency": False})
        service_grant("case-emergency", records["clinical"], "read", True)
        check("T1 emergency active", "case-emergency", records["clinical"], "read", True,
              {"emergency": True})
        check("T1 write not granted", "case-emergency", records["clinical"], "write", False,
              {"emergency": True})

        sql_grant(admin, "case-rehab", records["psych"])
        service_grant("case-rehab", records["psych"], "read", True)
        check("T2 before withdrawal", "case-rehab", records["psych"], "read", True)
        admin.execute("UPDATE protected_records SET consent=FALSE WHERE id=%s", (records["psych"],))
        service_grant("case-rehab", records["psych"], "read", False)
        check("T2 after withdrawal", "case-rehab", records["psych"], "read", False)

        admin.execute("UPDATE relations SET expires_at=statement_timestamp()-interval '1 second' WHERE id=%s",
                      (delegation,))
        for op in ("read", "write"):
            service_grant("case-nurse", records["med"], op, False)
        check("T3 expired delegation", "case-nurse", records["med"], "write", False)

        check("T4 before transition", "case-coordinator", records["discharge"], "write", False)
        sql_grant(admin, "case-coordinator", records["discharge"])
        for op in ("read", "write"):
            service_grant("case-coordinator", records["discharge"], op, True)
        check("T4 after transition", "case-coordinator", records["discharge"], "write", True)
        check("T4 unrelated subject", "case-unrelated", records["discharge"], "write", False)
    return results
