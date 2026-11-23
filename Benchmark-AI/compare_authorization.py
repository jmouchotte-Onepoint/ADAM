import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import time
from uuid import uuid4

import psycopg

from run import CHANGELOG, FIXTURE, RLS_POLICY, ROOT, sql_files, summarize
from support import connect


IMAGES = {
    "postgresql": "postgres:18.6",
    "openfga": "openfga/openfga:v1.14.1",
    "spicedb": "authzed/spicedb:v1.57.1",
}
TEST_KEY = "local-disposable-validation-key"


def docker(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True).strip()


def start_container(name: str, port: int, image: str, started: list[str],
                    options: tuple[str, ...] = (), command: tuple[str, ...] = ()) -> int:
    docker(
        "run", "--detach", "--name", name, "--cpus=1", "--memory=1g",
        "--publish", f"127.0.0.1::{port}", *options, image, *command,
    )
    started.append(name)
    return int(docker("port", name, f"{port}/tcp").rsplit(":", 1)[1])


def wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 60
    while True:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Local service on port {port} did not become ready")
            time.sleep(0.5)


class API:
    def __init__(self, port: int, token: str | None = None):
        self.connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        self.headers = {"Content-Type": "application/json"}
        if token is not None:
            self.headers["Authorization"] = f"Bearer {token}"

    def post(self, path: str, body: dict) -> dict:
        self.connection.request("POST", path, json.dumps(body), self.headers)
        response = self.connection.getresponse()
        payload = response.read()
        if not 200 <= response.status < 300:
            raise RuntimeError(f"POST {path}: HTTP {response.status}: {payload.decode()}")
        return json.loads(payload) if payload else {}

    def close(self) -> None:
        self.connection.close()


def fga_tuple(index: int, *, user: str = "nurse", tenant: str = "tenantA") -> dict:
    return {"user": f"user:{user}", "relation": "assigned", "object": f"record:{tenant}-{index}"}


def spice_relationship(index: int, *, user: str = "nurse", tenant: str = "tenantA") -> dict:
    return {
        "resource": {"objectType": "record", "objectId": f"{tenant}-{index}"},
        "relation": "assigned",
        "subject": {"object": {"objectType": "user", "objectId": user}},
    }


def fga_check(api: API, store: str, model: str, index: int, *, user: str = "nurse",
              tenant: str = "tenantA") -> bool:
    key = fga_tuple(index, user=user, tenant=tenant)
    key["relation"] = "can_read"
    response = api.post(f"/stores/{store}/check", {
        "authorization_model_id": model, "tuple_key": key, "consistency": "HIGHER_CONSISTENCY",
    })
    return response["allowed"]


def spice_check(api: API, index: int, *, user: str = "nurse", tenant: str = "tenantA") -> bool:
    relationship = spice_relationship(index, user=user, tenant=tenant)
    response = api.post("/v1/permissions/check", {
        "consistency": {"fullyConsistent": True},
        "resource": relationship["resource"], "permission": "can_read",
        "subject": relationship["subject"],
    })
    permission = response["permissionship"]
    if permission not in ("PERMISSIONSHIP_HAS_PERMISSION", "PERMISSIONSHIP_NO_PERMISSION"):
        raise RuntimeError(f"Unexpected SpiceDB permissionship: {permission}")
    return permission == "PERMISSIONSHIP_HAS_PERMISSION"


def sql_check(connection: psycopg.Connection, index: int) -> bool:
    return connection.execute(
        "SELECT EXISTS(SELECT 1 FROM parcours.etapes WHERE id = %s)", (f"parcours-{index}",)
    ).fetchone()[0]


def setup_openfga(api: API, count: int) -> tuple[str, str]:
    store = api.post("/stores", {"name": "adam-synthetic-comparison"})["id"]
    model = api.post(f"/stores/{store}/authorization-models", {
        "schema_version": "1.1",
        "type_definitions": [
            {"type": "user"},
            {"type": "record", "relations": {
                "assigned": {"this": {}},
                "can_read": {"computedUserset": {"relation": "assigned"}},
            }, "metadata": {"relations": {
                "assigned": {"directly_related_user_types": [{"type": "user"}]},
            }}},
        ],
    })["authorization_model_id"]
    for offset in range(0, count, 100):
        api.post(f"/stores/{store}/write", {
            "authorization_model_id": model,
            "writes": {"tuple_keys": [fga_tuple(i) for i in range(offset, min(offset + 100, count))]},
        })
    return store, model


def setup_spicedb(api: API, count: int) -> None:
    api.post("/v1/schema/write", {
        "schema": "definition user {}\ndefinition record {\n relation assigned: user\n"
                  " permission can_read = assigned\n}\n",
    })
    for offset in range(0, count, 100):
        api.post("/v1/relationships/write", {
            "updates": [
                {"operation": "OPERATION_CREATE", "relationship": spice_relationship(i)}
                for i in range(offset, min(offset + 100, count))
            ],
        })


def setup_postgres(count: int) -> tuple[str, list[Path]]:
    files = sql_files(CHANGELOG)
    files += [FIXTURE, RLS_POLICY]
    with psycopg.connect(os.environ["ADAM_VALIDATION_DSN"], user="postgres", autocommit=True) as admin:
        admin.execute("CREATE SCHEMA adam; SET search_path TO adam, public")
        for path in files:
            admin.execute(path.read_text())
        admin.execute(
            "INSERT INTO parcours.etapes(id, tenant_id) "
            "SELECT 'parcours-' || i, 'tenantA' FROM generate_series(0, %s) i",
            (count - 1,),
        )
        for i in range(count):
            admin.execute(
                "INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id) "
                "VALUES ('users','nurse','assigned','etapes',%s,'tenantA')",
                (f"parcours-{i}",),
            )
        admin.execute("ANALYZE")
        version = admin.execute("SELECT version()").fetchone()[0]
    return version, files


def verify_decisions(fga: API, spice: API, store: str, model: str, count: int) -> None:
    with connect(application=True) as sql:
        cases = [
            ("allowed", sql_check(sql, 0), fga_check(fga, store, model, 0), spice_check(spice, 0), True),
            ("missing record", sql_check(sql, count), fga_check(fga, store, model, count),
             spice_check(spice, count), False),
        ]
        sql.execute("SELECT set_config('app.adam.user_id','other-user',false)")
        cases.append(("other subject", sql_check(sql, 0), fga_check(fga, store, model, 0, user="other-user"),
                      spice_check(spice, 0, user="other-user"), False))
        sql.execute("SELECT set_config('app.adam.user_id','nurse',false), "
                    "set_config('app.adam.tenant_id','tenantB',false)")
        cases.append(("other tenant", sql_check(sql, 0), fga_check(fga, store, model, 0, tenant="tenantB"),
                      spice_check(spice, 0, tenant="tenantB"), False))
        for name, pg, fga_result, spice_result, expected in cases:
            if (pg, fga_result, spice_result) != (expected, expected, expected):
                raise AssertionError(f"{name}: PostgreSQL={pg}, OpenFGA={fga_result}, SpiceDB={spice_result}")


def sample_system(system: str, port: int, store: str, model: str, clients: int) -> list[float]:
    def worker(index: int) -> list[float]:
        api = API(port, TEST_KEY if system == "spicedb" else None) if system != "postgresql" else None
        sql = connect(application=True) if system == "postgresql" else None
        try:
            def check() -> bool:
                if system == "postgresql":
                    assert sql is not None
                    return sql_check(sql, index)
                assert api is not None
                if system == "openfga":
                    return fga_check(api, store, model, index)
                return spice_check(api, index)

            for _ in range(20):
                if not check():
                    raise AssertionError(f"{system} warm-up denied an authorized request")
            samples = []
            for _ in range(100):
                started = time.perf_counter_ns()
                allowed = check()
                elapsed = (time.perf_counter_ns() - started) / 1e6
                if not allowed:
                    raise AssertionError(f"{system} denied an authorized request")
                samples.append(elapsed)
            return samples
        finally:
            if api is not None:
                api.close()
            if sql is not None:
                sql.close()

    with ThreadPoolExecutor(max_workers=clients) as pool:
        return [value for batch in pool.map(worker, range(clients)) for value in batch]


def verify_revocation(fga: API, spice: API, store: str, model: str) -> None:
    with connect() as admin:
        admin.execute("DELETE FROM relations WHERE object_id = 'parcours-0'")
    fga.post(f"/stores/{store}/write", {
        "authorization_model_id": model, "deletes": {"tuple_keys": [fga_tuple(0)]},
    })
    spice.post("/v1/relationships/write", {
        "updates": [{"operation": "OPERATION_DELETE", "relationship": spice_relationship(0)}],
    })
    with connect(application=True) as sql:
        revoked = (sql_check(sql, 0), fga_check(fga, store, model, 0), spice_check(spice, 0))
        retained = (sql_check(sql, 1), fga_check(fga, store, model, 1), spice_check(spice, 1))
    if revoked != (False, False, False) or retained != (True, True, True):
        raise AssertionError(f"Revocation mismatch: revoked={revoked}, retained={retained}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=1000)
    args = parser.parse_args()
    if args.seeds < 4:
        parser.error("--seeds must be at least 4")
    if any((args.output / name).exists() for name in ("results.json", "latencies.json")):
        parser.error("output already contains results; choose a new directory")
    args.output.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    suffix = uuid4().hex[:12]
    names = {system: f"adam-compare-{system}-{suffix}" for system in IMAGES}
    started = []
    api_clients = []
    try:
        pg_port = start_container(
            names["postgresql"], 5432, IMAGES["postgresql"], started,
            options=("--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_DB=validation"),
        )
        fga_port = start_container(
            names["openfga"], 8080, IMAGES["openfga"], started,
            command=("run", "--datastore-engine=memory", "--playground-enabled=false"),
        )
        spice_port = start_container(
            names["spicedb"], 8443, IMAGES["spicedb"], started,
            command=("serve", f"--grpc-preshared-key={TEST_KEY}", "--http-enabled",
                     "--datastore-engine=memory", "--telemetry-endpoint="),
        )
        for port in (pg_port, fga_port, spice_port):
            wait_for_port(port)
        deadline = time.monotonic() + 60
        while subprocess.run(
            ["docker", "exec", names["postgresql"], "pg_isready", "-h", "127.0.0.1",
             "-U", "postgres", "-d", "validation"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            if time.monotonic() >= deadline:
                raise TimeoutError("PostgreSQL did not become ready")
            time.sleep(.5)
        os.environ["ADAM_VALIDATION_DSN"] = f"host=127.0.0.1 port={pg_port} dbname=validation"
        version, files = setup_postgres(args.seeds)
        fga, spice = API(fga_port), API(spice_port, TEST_KEY)
        api_clients.extend((fga, spice))
        store, model = setup_openfga(fga, args.seeds)
        setup_spicedb(spice, args.seeds)
        verify_decisions(fga, spice, store, model, args.seeds)
        rows, raw = [], []
        for system, port in (("postgresql", pg_port), ("openfga", fga_port), ("spicedb", spice_port)):
            for clients in (1, 4):
                for repeat in range(1, 4):
                    begin = time.perf_counter()
                    values = sample_system(system, port, store, model, clients)
                    rows.append({"system": system, "clients": clients, "repeat": repeat,
                                 **summarize(values, time.perf_counter() - begin)})
                    raw.extend({"system": system, "clients": clients, "repeat": repeat, "ms": value}
                               for value in values)
        verify_revocation(fga, spice, store, model)
        report = {
            "started_at_utc": started_at,
            "platform": platform.platform(), "machine": platform.machine(), "postgres_version": version,
            "images": {system: {"tag": IMAGES[system], "image_id": docker("inspect", name, "--format", "{{.Image}}")}
                       for system, name in names.items()},
            "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in files + [Path(__file__).resolve()]},
            "seeds": args.seeds, "rows": rows,
            "correctness": "allow, absent record, other subject, other tenant, revocation and unaffected record pass",
            "protocol": "client wall clock, persistent PostgreSQL or HTTP/JSON connections, 20 warmups and "
                        "100 measured requests per client per repetition; 3 repetitions; 1 and 4 clients",
            "scope": "common direct-assignment read subset only; PostgreSQL RLS includes row access and "
                     "materialized permissions, OpenFGA and SpiceDB use in-memory authorization stores",
            "consistency": "PostgreSQL READ COMMITTED; OpenFGA HIGHER_CONSISTENCY; SpiceDB fullyConsistent",
        }
        (args.output / "latencies.json").write_text(json.dumps(raw, indent=2))
        (args.output / "results.json").write_text(json.dumps(report, indent=2))
        print(json.dumps({"output": str(args.output), "correctness": report["correctness"]}, indent=2))
    finally:
        for api in api_clients:
            api.close()
        for name in reversed(started):
            subprocess.run(["docker", "rm", "--force", name], check=True)


if __name__ == "__main__":
    main()
