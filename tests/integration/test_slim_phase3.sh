#!/usr/bin/env bash
# =============================================================================
# tests/integration/test_slim_phase3.sh
# S.L.I.M. Phase 3 Integration Tests: Dynamic Trace & Performance Gates
# Tests [TAG: UNVERIFIED] and [TAG: REGRESSION]
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SLIM="${SLIM:-"$ROOT_DIR/bin/slim.elf"}"
BUILD_DIR="$ROOT_DIR/scratch/test_phase3"

mkdir -p "$BUILD_DIR"

if [[ ! -x "$SLIM" ]]; then
    echo "Building S.L.I.M. linter via STAFF..."
    "$ROOT_DIR/bin/staff" "$ROOT_DIR/slim/build.staff" "$BUILD_DIR/slim.safe"
    "$ROOT_DIR/bin/packager_bin" "$BUILD_DIR/slim.safe" "$ROOT_DIR/bin/slim.elf"
    chmod +x "$ROOT_DIR/bin/slim.elf"
    rm -f "$BUILD_DIR/slim.safe"
fi

echo "========================================================================="
echo " RUNNING SINC S.L.I.M. PHASE 3 TESTS (Dynamic Trace & Performance Gates)"
echo "========================================================================="

# 1. Test [TAG: UNVERIFIED] when coverage count is 0
echo -n "[Test 1/4] Checking [TAG: UNVERIFIED] on zero execution trace... "
set +e
ERR_OUT=$("$SLIM" verify-trace 0 2>&1 >/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 1 ]] && echo "$ERR_OUT" | grep -q "\[TAG: UNVERIFIED\]"; then
    echo "PASS (Exit 1, [TAG: UNVERIFIED] applied)"
else
    echo "FAIL (Expected exit 1 with [TAG: UNVERIFIED], got $CODE: $ERR_OUT)"
    exit 1
fi

# 2. Test verified trace passes when coverage count > 0
echo -n "[Test 2/4] Checking verified trace execution PASS... "
set +e
OUT=$("$SLIM" verify-trace 42 2>/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 0 ]] && echo "$OUT" | grep -q "\[SLIM: PASS\]"; then
    echo "PASS (Exit 0, verified by trace)"
else
    echo "FAIL (Expected exit 0 with [SLIM: PASS], got $CODE: $OUT)"
    exit 1
fi

# 3. Test [TAG: REGRESSION] when cycle count exceeds ceiling
echo -n "[Test 3/4] Checking [TAG: REGRESSION] on benchmark regression... "
set +e
ERR_OUT=$("$SLIM" verify-bench 150 100 2>&1 >/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 1 ]] && echo "$ERR_OUT" | grep -q "\[TAG: REGRESSION\]"; then
    echo "PASS (Exit 1, [TAG: REGRESSION] applied)"
else
    echo "FAIL (Expected exit 1 with [TAG: REGRESSION], got $CODE: $ERR_OUT)"
    exit 1
fi

# 4. Test performance within budget passes
echo -n "[Test 4/4] Checking performance budget PASS... "
set +e
OUT=$("$SLIM" verify-bench 80 100 2>/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 0 ]] && echo "$OUT" | grep -q "\[SLIM: PASS\]"; then
    echo "PASS (Exit 0, within budget)"
else
    echo "FAIL (Expected exit 0 with [SLIM: PASS], got $CODE: $OUT)"
    exit 1
fi

echo "========================================================================="
echo " ALL PHASE 3 S.L.I.M. DYNAMIC GATE TESTS PASSED"
echo "========================================================================="
