import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import platform
import subprocess
import time
import unittest
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from mongo_adapter import protected_read, protected_write, record_fixture
from run import quantile


ROOT = Path(__file__).resolve().parent
IMAGE = "mongo:8.0"


def docker(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True).strip()


def run_tests(uri: str) -> None:
    os.environ["ADAM_MONGO_URI"] = uri
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern="test_mongo_adapter.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("MongoDB adapter tests failed; benchmark not run")


def benchmark(client: MongoClient, seeds: int, output: Path) -> None:
    db = client[f"adam_benchmark_{seeds}"]
    records = db.records
    ids = [f"bench-{i}" for i in range(seeds)]
    for offset in range(0, seeds, 500):
        records.insert_many([record_fixture(record) for record in ids[offset:offset + 500]])
    if records.count_documents({}) != seeds:
        raise RuntimeError("Unexpected seed count")
    db.create_collection("system.profile", capped=True, size=32 * 1024 * 1024)
    db.command("profile", 2)

    def worker(operation: str, worker_id: int, tag: dict) -> None:
        record = ids[worker_id]
        action = protected_read if operation == "read" else protected_write
        for _ in range(20):
            if not action(records, record, "tenantA", "nurse", "nurse"):
                raise RuntimeError("Warm-up operation denied")
        for _ in range(100):
            if not action(records, record, "tenantA", "nurse", "nurse", comment=tag):
                raise RuntimeError("Measured operation denied")

    samples = []
    summary = []
    for clients in (1, 4):
        for repeat in range(1, 4):
            for operation in ("read", "write"):
                tag = {"campaign": "adam-mongo", "clients": clients,
                       "repeat": repeat, "operation": operation}
                with ThreadPoolExecutor(max_workers=clients) as pool:
                    list(pool.map(lambda i: worker(operation, i, tag), range(clients)))
                entries = list(db["system.profile"].find(
                    {"command.comment": tag}, {"millis": 1, "_id": 0}
                ))
                if len(entries) != clients * 100:
                    raise RuntimeError(f"Expected {clients * 100} profile samples, got {len(entries)}")
                values = [entry["millis"] for entry in entries]
                samples.extend({"operation": operation, "clients": clients, "repeat": repeat,
                                "ms": value} for value in values)
                summary.append({"operation": operation, "clients": clients, "repeat": repeat,
                                "samples": len(values), "p50_ms": quantile(values, .5),
                                "p95_ms": quantile(values, .95), "p99_ms": quantile(values, .99)})
    db.command("profile", 0)
    output.mkdir(parents=True, exist_ok=True)
    (output / "latencies.json").write_text(json.dumps(samples, indent=2) + "\n")
    metadata = {
        "seeds": seeds,
        "image_id": docker("image", "inspect", IMAGE, "--format", "{{.Id}}"),
        "mongodb_version": client.server_info()["version"],
        "host": platform.platform(),
        "container": "1 CPU, 1 GiB, WiredTiger cache 0.25 GiB, ephemeral standalone",
        "measurement": "MongoDB profiler millis, integer milliseconds; server time, not client time",
        "read_concern": str(db.read_concern.document),
        "write_concern": str(db.write_concern.document),
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("mongo_adapter.py", "test_mongo_adapter.py", "run_mongo.py")
        },
        "summary": summary,
    }
    (output / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Recorded {len(samples)} profiler samples for {seeds} seeds in {output}", flush=True)


def main() -> None:
    name = "adam-mongo-validation-" + uuid4().hex[:12]
    started = False
    try:
        docker("run", "-d", "--name", name, "--cpus", "1", "--memory", "1g",
               "-p", "127.0.0.1::27017", IMAGE, "--bind_ip_all",
               "--wiredTigerCacheSizeGB", "0.25")
        started = True
        port = docker("port", name, "27017/tcp").rsplit(":", 1)[1]
        uri = f"mongodb://127.0.0.1:{port}/?directConnection=true&serverSelectionTimeoutMS=1000"
        with MongoClient(uri) as client:
            for attempt in range(60):
                try:
                    client.admin.command("ping")
                    break
                except ConnectionFailure:
                    if attempt == 59:
                        raise
                    time.sleep(1)
            run_tests(uri)
            for seeds in (1000, 10000):
                benchmark(client, seeds, ROOT / f"results-mongo-{seeds}")
    finally:
        if started:
            subprocess.run(["docker", "rm", "-f", name], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
