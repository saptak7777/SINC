#!/usr/bin/env bash
# ==============================================================================
# tools/verify_all.sh
# SINC Unified Verification Runner
# ==============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEFAULT_SINC="$ROOT_DIR/bin/sinc.elf"
[ -x "$DEFAULT_SINC" ] || DEFAULT_SINC="$ROOT_DIR/sinc.elf"
SINC=${SINC:-"$DEFAULT_SINC"}

DEFAULT_PACKAGER="$ROOT_DIR/bin/packager_bin"
[ -x "$DEFAULT_PACKAGER" ] || DEFAULT_PACKAGER="$ROOT_DIR/packager_bin"
PACKAGER=${PACKAGER:-"$DEFAULT_PACKAGER"}

case "${1:-}" in
    --sanity)
        exec python3 "$ROOT_DIR/tools/verify_sanity.py" "$SINC" "$PACKAGER" "${@:2}"
        ;;
    --bench)
        exec python3 "$ROOT_DIR/tools/bench_24_gcc.py" "${@:2}"
        ;;
    --all)
        echo "=== STEP 1: FUNCTIONAL SANITY & BEHAVIOR SUITE ==="
        python3 "$ROOT_DIR/tools/verify_sanity.py" "$SINC" "$PACKAGER"
        echo ""
        echo "=== STEP 2: GOLDEN BASELINE BITWISE AUDIT ==="
        exec python3 "$ROOT_DIR/tools/verify_golden_parity.py" "$SINC" "$PACKAGER" "${@:2}"
        ;;
    *)
        exec python3 "$ROOT_DIR/tools/verify_golden_parity.py" "$SINC" "$PACKAGER" "$@"
        ;;
esac
