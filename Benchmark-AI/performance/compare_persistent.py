import sys
from pathlib import Path

# Les modules du harnais forment un espace de noms unique à la racine de
# Benchmark-AI : on l'ajoute pour que ce script reste exécutable directement.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from uuid import uuid4

import psycopg

from performance.compare_authorization import (
    API, IMAGES, TEST_KEY, docker, fga_check, setup_openfga, setup_postgres,
    setup_spicedb, spice_check, sql_check, start_container, verify_decisions,
    verify_revocation, wait_for_port,
)
from compare_clinical import replay as replay_clinical
from run import ROOT, summarize
from support import connect


def wait_for_http(port: int) -> None:
    deadline = time.monotonic() + 60
    while True:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        try:
            connection.request("GET", "/healthz")
            connection.getresponse().read()
            return
        except (OSError, http.client.HTTPException):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"HTTP service on port {port} did not become ready")
            time.sleep(.5)
        finally:
            connection.close()


def protected_read(system: str, api: API | None, db: psycopg.Connection,
                   index: int, store: str, model: str) -> bool:
    if system == "postgresql":
        return sql_check(db, index)
    if api is None:
        raise ValueError(f"{system} requires an authorization-service connection")
    allowed = (fga_check(api, store, model, index) if system == "openfga"
               else spice_check(api, index))
    if not allowed:
        return False
    return bool(db.execute(
        "SELECT id FROM comparison_records WHERE tenant_id = %s AND id = %s",
        ("tenantA", f"parcours-{index}"),
    ).fetchall())


def sample(system: str, port: int, store: str, model: str, clients: int) -> list[float]:
    def worker(index: int) -> list[float]:
        api = API(port, TEST_KEY if system == "spicedb" else None) if system != "postgresql" else None
        try:
            with connect(application=True) as db:
                for _ in range(20):
                    if not protected_read(system, api, db, index, store, model):
                        raise AssertionError(f"{system} denied a warm-up")
                values = []
                for _ in range(100):
                    begin = time.perf_counter_ns()
                    allowed = protected_read(system, api, db, index, store, model)
                    values.append((time.perf_counter_ns() - begin) / 1e6)
                    if not allowed:
                        raise AssertionError(f"{system} denied a measured read")
                return values
        finally:
            if api is not None:
                api.close()

    with ThreadPoolExecutor(max_workers=clients) as pool:
        return [value for batch in pool.map(worker, range(clients)) for value in batch]


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

    suffix = uuid4().hex[:12]
    network = f"adam-compare-network-{suffix}"
    names = {system: f"adam-persistent-{system}-{suffix}" for system in IMAGES}
    started: list[str] = []
    api_clients: list[API] = []
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    docker("network", "create", network)
    try:
        pg_port = start_container(
            names["postgresql"], 5432, IMAGES["postgresql"], started,
            options=("--network", network, "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                     "--env", "POSTGRES_DB=validation"),
            command=("-c", "track_commit_timestamp=on"),
        )
        deadline = time.monotonic() + 60
        while subprocess.run(
            ["docker", "exec", names["postgresql"], "pg_isready", "-h", "127.0.0.1",
             "-U", "postgres", "-d", "validation"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            if time.monotonic() >= deadline:
                raise TimeoutError("PostgreSQL did not become ready")
            time.sleep(.5)
        os.environ["ADAM_VALIDATION_DSN"] = f"host=127.0.0.1 port={pg_port} dbname=validation"
        with psycopg.connect(os.environ["ADAM_VALIDATION_DSN"], user="postgres", autocommit=True) as db:
            db.execute("CREATE DATABASE openfga")
            db.execute("CREATE DATABASE spicedb")
        version, files = setup_postgres(args.seeds)
        with connect() as db:
            db.execute("CREATE TABLE comparison_records (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL)")
            db.execute("INSERT INTO comparison_records SELECT id, tenant_id FROM parcours.etapes")
            db.execute("GRANT SELECT ON comparison_records TO read_validation")
            db.execute("ANALYZE comparison_records")
        fga_dsn = f"postgres://postgres@{names['postgresql']}:5432/openfga?sslmode=disable"
        spice_dsn = f"postgres://postgres@{names['postgresql']}:5432/spicedb?sslmode=disable"
        for image, command in (
            (IMAGES["openfga"], ("migrate", "--datastore-engine=postgres", f"--datastore-uri={fga_dsn}")),
            (IMAGES["spicedb"], ("migrate", "head", "--datastore-engine=postgres",
                                 f"--datastore-conn-uri={spice_dsn}")),
        ):
            subprocess.run(["docker", "run", "--rm", "--network", network, image, *command],
                           check=True, stdout=subprocess.DEVNULL)
        fga_port = start_container(
            names["openfga"], 8080, IMAGES["openfga"], started, options=("--network", network),
            command=("run", "--datastore-engine=postgres", f"--datastore-uri={fga_dsn}",
                     "--playground-enabled=false"),
        )
        spice_port = start_container(
            names["spicedb"], 8443, IMAGES["spicedb"], started, options=("--network", network),
            command=("serve", f"--grpc-preshared-key={TEST_KEY}", "--http-enabled",
                     "--datastore-engine=postgres", f"--datastore-conn-uri={spice_dsn}",
                     "--telemetry-endpoint="),
        )
        for port in (fga_port, spice_port):
            wait_for_port(port)
            wait_for_http(port)
        fga, spice = API(fga_port), API(spice_port, TEST_KEY)
        api_clients.extend((fga, spice))
        store, model = setup_openfga(fga, args.seeds)
        setup_spicedb(spice, args.seeds)
        verify_decisions(fga, spice, store, model, args.seeds)
        with connect(application=True) as db:
            for system, api in (("openfga", fga), ("spicedb", spice)):
                if not protected_read(system, api, db, 0, store, model):
                    raise AssertionError(f"{system} failed to retrieve an authorized record")
                if protected_read(system, api, db, args.seeds, store, model):
                    raise AssertionError(f"{system} returned a missing record")
        rows, raw = [], []
        for system, port in (("postgresql", pg_port), ("openfga", fga_port), ("spicedb", spice_port)):
            for clients in (1, 4):
                for repeat in range(1, 4):
                    begin = time.perf_counter()
                    values = sample(system, port, store, model, clients)
                    rows.append({"system": system, "clients": clients, "repeat": repeat,
                                 **summarize(values, time.perf_counter() - begin)})
                    raw.extend({"system": system, "clients": clients, "repeat": repeat, "ms": value}
                               for value in values)
        verify_revocation(fga, spice, store, model)
        clinical = replay_clinical(fga, spice)
        report = {
            "started_at_utc": started_at, "platform": platform.platform(),
            "postgres_version": version, "seeds": args.seeds,
            "images": {system: {"tag": IMAGES[system], "image_id": docker("inspect", name, "--format", "{{.Image}}")}
                       for system, name in names.items()},
            "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in files + [Path(__file__).resolve(),
                                                   ROOT / "Benchmark-AI/performance/compare_authorization.py",
                                                   ROOT / "Benchmark-AI/compare_clinical.py"]},
            "correctness": "allow, absent record, other subject, other tenant, revocation and unaffected record pass",
            "clinical_replay": clinical,
            "protocol": "client time; authorization and record lookup; persistent reused connections; "
                        "20 warmups, 100 requests per client, 3 repetitions, 1 or 4 clients",
            "scope": "direct-assignment read only; PostgreSQL-backed service stores and application data; "
                     "ADAM uses RLS, services check then fetch from a separate unrestricted table",
            "limitations": "different protocols, role/permission representations, caches and trust boundaries; "
                           "no atomic service-check/data-read or equivalent distributed consistency claim",
            "rows": rows,
        }
        (args.output / "latencies.json").write_text(json.dumps(raw, indent=2) + "\n")
        (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"output": str(args.output), "correctness": report["correctness"]}), flush=True)
    finally:
        for api in api_clients:
            api.close()
        if sys.exc_info()[0] is not None:
            for name in started:
                subprocess.run(["docker", "logs", "--tail", "40", name], check=True)
        for name in reversed(started):
            subprocess.run(["docker", "rm", "--force", name], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "network", "rm", network], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
