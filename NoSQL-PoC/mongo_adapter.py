from typing import Any

from pymongo.collection import Collection


def _filter(record: str, tenant: str, subject: str, profession: str, operation: str) -> dict:
    if not all(isinstance(value, str) and value for value in (record, tenant, subject, profession)):
        raise ValueError("Record, tenant, subject and profession must be nonempty strings")
    if operation not in ("read", "write"):
        raise ValueError("Unsupported operation")

    def unexpired(field: str) -> dict:
        return {"$or": [
            {"$eq": [{"$ifNull": [field, None]}, None]},
            {"$gt": [field, "$$NOW"]},
        ]}

    def grant_check(required_operation: str) -> dict:
        return {"$anyElementTrue": [{"$map": {
            "input": {"$ifNull": ["$grants", []]},
            "as": "grant",
            "in": {"$and": [
                {"$eq": ["$$grant.subject", {"$literal": subject}]},
                {"$eq": ["$$grant.operation", {"$literal": required_operation}]},
                {"$eq": ["$$grant.profession", {"$literal": profession}]},
                {"$eq": ["$$grant.allow", True]},
                {"$eq": ["$$grant.source_allow", True]},
                unexpired("$$grant.expires_at"),
                unexpired("$$grant.source_expires_at"),
            ]},
        }}]}

    checks = [grant_check("read")]
    if operation == "write":
        checks.append(grant_check("write"))
    return {
        "_id": record,
        "tenant_id": tenant,
        "consent": True,
        "$expr": {"$and": checks},
    }


def protected_read(
    collection: Collection, record: str, tenant: str, subject: str, profession: str,
    *, comment: dict | None = None,
) -> dict | None:
    return collection.find_one(
        _filter(record, tenant, subject, profession, "read"),
        {"_id": 1}, comment=comment,
    )


def protected_write(
    collection: Collection, record: str, tenant: str, subject: str, profession: str,
    *, comment: dict | None = None,
) -> bool:
    result = collection.update_one(
        _filter(record, tenant, subject, profession, "write"),
        {"$inc": {"value": 1}}, comment=comment,
    )
    return result.matched_count == 1


def record_fixture(record: str) -> dict[str, Any]:
    grants = [
        {
            "subject": "nurse",
            "operation": "read" if i == 1 else "write" if i == 2 else f"permission_{i}",
            "profession": "nurse",
            "allow": True,
            "source_allow": True,
            "expires_at": None,
            "source_expires_at": None,
            "source_id": f"source-{record}",
        }
        for i in range(1, 22)
    ]
    return {
        "_id": record,
        "tenant_id": "tenantA",
        "consent": True,
        "value": 0,
        "source_id": f"source-{record}",
        "roles": [f"role_{i}" for i in range(1, 5)],
        "grants": grants,
    }
