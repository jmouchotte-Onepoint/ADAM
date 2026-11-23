import os
import unittest
from uuid import uuid4

import psycopg


def connect(*, application: bool = False, autocommit: bool = True) -> psycopg.Connection:
    connection = psycopg.connect(
        os.environ["ADAM_VALIDATION_DSN"],
        user="read_validation" if application else "postgres",
        autocommit=autocommit,
        options="-c search_path=adam,public",
    )
    connection.execute(
        "SELECT set_config('app.adam.user_id', %s, false), "
        "set_config('app.adam.tenant_id', 'tenantA', false), "
        "set_config('app.adam.user_attributes', '{}', false)",
        ("nurse" if application else "postgres",),
    )
    return connection


class DatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.admin = connect()
        self.app = connect(application=True)
        self.record = "parcours-" + uuid4().hex
        self.admin.execute(
            "INSERT INTO protected_records(id, tenant_id) VALUES (%s, 'tenantA')",
            (self.record,),
        )
        self.admin.execute(
            "INSERT INTO parcours.etapes(id, tenant_id) VALUES (%s, 'tenantA')",
            (self.record,),
        )
        self.seed = self.admin.execute(
            "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
            "VALUES ('users','nurse','assigned','etapes',%s,'tenantA') RETURNING id",
            (self.record,),
        ).fetchone()[0]

    def tearDown(self) -> None:
        self.app.close()
        self.admin.execute("DELETE FROM roles WHERE object_id = %s", (self.record,))
        self.admin.execute("DELETE FROM relations WHERE object_id = %s", (self.record,))
        self.admin.execute("DELETE FROM protected_records WHERE id = %s", (self.record,))
        self.admin.execute("DELETE FROM parcours.etapes WHERE id = %s", (self.record,))
        self.admin.close()

    def visible(self, connection: psycopg.Connection | None = None) -> bool:
        connection = connection if connection is not None else self.app
        return bool(
            connection.execute(
                "SELECT id FROM protected_records WHERE id = %s", (self.record,)
            ).fetchall()
        )
