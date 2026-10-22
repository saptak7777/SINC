#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON=${PYTHON:-python3}
ROUNDS=${1:-10}

exec "$PYTHON" "$ROOT_DIR/tools/differential_oracle.py" --random-rounds "$ROUNDS"
