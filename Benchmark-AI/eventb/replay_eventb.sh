#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: bash Benchmark-AI/eventb/replay_eventb.sh OUTPUT_DIRECTORY" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$1"
OUTPUT="$(cd "$1" && pwd)"
if [ -e "$OUTPUT/adam-replayed.zip" ] || [ -e "$OUTPUT/rodin.log" ] || [ -e "$OUTPUT/source-hashes.sha256" ]; then
    echo "Output already exists; choose a new directory" >&2
    exit 2
fi

(
    cd "$ROOT/EventB"
    shasum -a 256 .project ./*.bum ./*.buc > "$OUTPUT/source-hashes.sha256"
    zip -q "$OUTPUT/adam-replayed.zip" .project ./*.bum ./*.buc
)

docker run --rm --platform=linux/amd64 --network=none --cpus=2 --memory=3g \
    --mount "type=bind,src=$OUTPUT,dst=/models" \
    ghcr.io/eventb-rossi/rodin-headless@sha256:54aff23e5127847295087b9dfdf4b8fc478320141f7f26a4b640486d5d061c4f \
    autoprove --strict adam-replayed.zip 2>&1 | tee "$OUTPUT/rodin.log"
