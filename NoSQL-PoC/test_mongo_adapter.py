from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from pymongo import MongoClient

from mongo_adapter import protected_read, protected_write, record_fixture
from run_mongo import run_tests


class MongoHarnessTests(unittest.TestCase):
    def test_empty_discovery_stops_the_benchmark(self) -> None:
        with patch.dict(os.environ), patch(
            "run_mongo.unittest.defaultTestLoader.discover", return_value=unittest.TestSuite()
        ):
            with self.assertRaisesRegex(RuntimeError, "benchmark not run"):
                run_tests("mongodb://unused")


class MongoAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MongoClient(os.environ["ADAM_MONGO_URI"])
        self.records = self.client["adam_tests"]["records"]
        self.record = str(uuid4())
        self.records.insert_one(record_fixture(self.record))

    def tearDown(self) -> None:
        self.records.delete_one({"_id": self.record})
        self.client.close()

    def read(self, subject: str = "nurse", tenant: str = "tenantA",
             profession: str = "nurse") -> bool:
        return protected_read(self.records, self.record, tenant, subject, profession) is not None

    def write(self, subject: str = "nurse", tenant: str = "tenantA",
              profession: str = "nurse") -> bool:
        return protected_write(self.records, self.record, tenant, subject, profession)

    def test_allowed_read_write_and_persistence(self) -> None:
        self.assertTrue(self.read())
        self.assertTrue(self.write())
        self.assertEqual(self.records.find_one({"_id": self.record})["value"], 1)

    def test_subject_tenant_and_attribute_mismatch(self) -> None:
        for args in (("other", "tenantA", "nurse"), ("nurse", "tenantB", "nurse"),
                     ("nurse", "tenantA", "doctor"), ("$tenant_id", "tenantA", "nurse")):
            with self.subTest(args=args):
                self.assertFalse(self.read(*args))
                self.assertFalse(self.write(*args))

    def test_missing_identity_or_attribute_is_an_error(self) -> None:
        for args in (("", "tenantA", "nurse"), ("nurse", "", "nurse"),
                     ("nurse", "tenantA", "")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.read(*args)

    def test_consent_denies_reads_and_writes(self) -> None:
        self.records.update_one({"_id": self.record}, {"$set": {"consent": False}})
        self.assertFalse(self.read())
        self.assertFalse(self.write())

    def test_permission_and_source_expiry(self) -> None:
        expired = datetime.now(timezone.utc) - timedelta(minutes=1)
        for field in ("expires_at", "source_expires_at"):
            with self.subTest(field=field):
                self.records.update_one({"_id": self.record},
                                        {"$set": {f"grants.$[].{field}": expired}})
                self.assertFalse(self.read())
                self.assertFalse(self.write())
                self.records.update_one({"_id": self.record},
                                        {"$set": {f"grants.$[].{field}": None}})
                self.assertTrue(self.read())

    def test_revocation_is_seen_by_subsequent_requests(self) -> None:
        self.records.update_one({"_id": self.record},
                                {"$set": {"grants.$[].source_allow": False}})
        self.assertFalse(self.read())
        self.assertFalse(self.write())

    def test_operation_and_permission_revocation(self) -> None:
        self.records.update_one({"_id": self.record},
                                {"$set": {"grants.1.allow": False}})
        self.assertTrue(self.read())
        self.assertFalse(self.write())
        self.records.update_one({"_id": self.record}, {"$set": {
            "grants.0.allow": False, "grants.1.allow": True,
        }})
        self.assertFalse(self.read())
        self.assertFalse(self.write())

    def test_conditions_must_match_the_same_grant(self) -> None:
        self.records.update_one({"_id": self.record}, {"$set": {
            "grants.0.profession": "doctor",
            "grants.1.operation": "other",
        }})
        self.assertFalse(self.read())


if __name__ == "__main__":
    unittest.main()
