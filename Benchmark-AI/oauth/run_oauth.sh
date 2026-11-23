#!/usr/bin/env bash
set -euo pipefail

code_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$code_dir"

for command in docker uv; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Required command not found: %s\n' "$command" >&2
        exit 1
    fi
done

if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running or is not accessible." >&2
    exit 1
fi

image="adam-oauth-validation:run-$(date +%s)-$$"
if docker image inspect "$image" >/dev/null 2>&1; then
    echo "The temporary image tag already exists: $image" >&2
    exit 1
fi

image_built=0
cleanup() {
    status=$?
    trap - EXIT
    if [ "$image_built" -eq 1 ] && ! docker image rm "$image" >/dev/null; then
        echo "Could not remove temporary image: $image" >&2
        exit 1
    fi
    exit "$status"
}
trap cleanup EXIT

echo "Building the temporary PostgreSQL OAuth image..."
docker build --tag "$image" - < Docker/OAuth.Dockerfile
image_built=1

echo "Starting Keycloak and PostgreSQL and running the synthetic scenario..."
ADAM_OAUTH_IMAGE="$image" uv run --locked --group validation \
    python -u Benchmark-AI/check_oauth_keycloak.py
docker image rm "$image" >/dev/null
image_built=0
echo "OAuth scenario passed; temporary containers, certificates and image tag were removed."
