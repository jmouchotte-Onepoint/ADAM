import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from compare_attribute_plans import install_candidate
from compare_authorization import IMAGES, setup_postgres, start_container
from run import ROOT, tests
from support import connect


PATTERNS = ("test_protected_access.py", "test_lifecycle.py", "test_concurrency.py",
            "test_repository_claims.py", "test_clinical_replay.py",
            "test_eventb_sql_correspondence.py", "test_attribute_equivalence.py")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    name = "adam-extended-" + uuid4().hex[:12]
    started: list[str] = []
    try:
        port = start_container(name, 5432, IMAGES["postgresql"], started,
                               options=("--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                                        "--env", "POSTGRES_DB=validation"))
        deadline = time.monotonic() + 60
        while subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1",
                              "-U", "postgres", "-d", "validation"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            if time.monotonic() >= deadline:
                raise TimeoutError("PostgreSQL did not become ready")
            time.sleep(.5)
        os.environ["ADAM_VALIDATION_DSN"] = f"host=127.0.0.1 port={port} dbname=validation"
        version, files = setup_postgres(4)
        image_id = subprocess.check_output(
            ["docker", "inspect", name, "--format", "{{.Image}}"], text=True).strip()
        checks = {}
        for variant in ("baseline", "targeted-wrapper"):
            if variant == "targeted-wrapper":
                with connect() as admin:
                    install_candidate(admin)
            checks[variant] = {pattern: tests(pattern) for pattern in PATTERNS}
        source_files = files + [Path(__file__).resolve(), ROOT / "Benchmark-AI/run.py",
                                ROOT / "Benchmark-AI/support.py",
                                ROOT / "Benchmark-AI/compare_attribute_plans.py"]
        source_files += [ROOT / "Benchmark-AI" / pattern for pattern in PATTERNS]
        failed = any(result["exit_code"] for suite in checks.values() for result in suite.values())
        report = {"postgres_version": version, "image_id": image_id, "checks": checks,
                  "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in source_files}, "overall": "FAIL" if failed else "PASS"}
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        if failed:
            raise SystemExit("Extended evaluation failed; see saved results")
        print(f"PASS: baseline and candidate tests; {args.output}")
    finally:
        for container in reversed(started):
            subprocess.run(["docker", "rm", "--force", container], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
