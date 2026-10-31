#!/usr/bin/env bash
# =============================================================================
# tests/integration/test_slim_phase1.sh
# S.L.I.M. Phase 1 Integration Tests: Static Architectural Constraints
# Tests [TAG: LAZY], [TAG: DEAD WEIGHT], [TAG: UNNECESSARY], and PASS
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SLIM="${SLIM:-"$ROOT_DIR/bin/slim.elf"}"
BUILD_DIR="$ROOT_DIR/scratch/test_phase1"

mkdir -p "$BUILD_DIR"

if [[ ! -x "$SLIM" ]]; then
    echo "Building S.L.I.M. linter via STAFF..."
    "$ROOT_DIR/bin/staff" "$ROOT_DIR/slim/build.staff" "$BUILD_DIR/slim.safe"
    "$ROOT_DIR/bin/packager_bin" "$BUILD_DIR/slim.safe" "$ROOT_DIR/bin/slim.elf"
    chmod +x "$ROOT_DIR/bin/slim.elf"
    rm -f "$BUILD_DIR/slim.safe"
fi

echo "========================================================================="
echo " RUNNING SINC S.L.I.M. PHASE 1 TESTS (Static Architectural Constraints)"
echo "========================================================================="

# -----------------------------------------------------------------------------
# Test 1: [TAG: LAZY] Statement Complexity Cap (>4 ops)
# -----------------------------------------------------------------------------
echo -n "[Test 1/4] Checking [TAG: LAZY] complexity cap... "
cat << 'EOF' > "$BUILD_DIR/lazy.sinc"
fn main() [
    x = 1 + 2 + 3 + 4 + 5 + 6;
    ret x;
]
EOF

set +e
ERR_OUT=$("$SLIM" check "$BUILD_DIR/lazy.sinc" 2>&1 >/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 1 ]] && echo "$ERR_OUT" | grep -q "\[TAG: LAZY\] line 2:"; then
    echo "PASS (Exit 1, [TAG: LAZY] detected)"
else
    echo "FAIL (Expected exit 1 with [TAG: LAZY], got code $CODE: $ERR_OUT)"
    exit 1
fi

# -----------------------------------------------------------------------------
# Test 2: [TAG: DEAD WEIGHT] Unused Function Detection
# -----------------------------------------------------------------------------
echo -n "[Test 2/4] Checking [TAG: DEAD WEIGHT] unused function... "
cat << 'EOF' > "$BUILD_DIR/dead.sinc"
fn dead_weight_helper(a, b) [
    ret a + b;
]

fn main() [
    ret 0;
]
EOF

set +e
ERR_OUT=$("$SLIM" check "$BUILD_DIR/dead.sinc" 2>&1 >/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 1 ]] && echo "$ERR_OUT" | grep -q "\[TAG: DEAD WEIGHT\] line 1: dead_weight_helper"; then
    echo "PASS (Exit 1, [TAG: DEAD WEIGHT] detected)"
else
    echo "FAIL (Expected exit 1 with [TAG: DEAD WEIGHT], got code $CODE: $ERR_OUT)"
    exit 1
fi

# -----------------------------------------------------------------------------
# Test 3: [TAG: UNNECESSARY] Dead Stores / Unread Local Variable
# -----------------------------------------------------------------------------
echo -n "[Test 3/4] Checking [TAG: UNNECESSARY] dead store... "
cat << 'EOF' > "$BUILD_DIR/unnec.sinc"
fn main() [
    ghost_variable = 100;
    ret 0;
]
EOF

set +e
ERR_OUT=$("$SLIM" check "$BUILD_DIR/unnec.sinc" 2>&1 >/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 1 ]] && echo "$ERR_OUT" | grep -q "\[TAG: UNNECESSARY\] line 2: ghost_variable"; then
    echo "PASS (Exit 1, [TAG: UNNECESSARY] detected)"
else
    echo "FAIL (Expected exit 1 with [TAG: UNNECESSARY], got code $CODE: $ERR_OUT)"
    exit 1
fi

# -----------------------------------------------------------------------------
# Test 4: [SLIM: PASS] Clean Codebase Passes
# -----------------------------------------------------------------------------
echo -n "[Test 4/4] Checking clean codebase PASS... "
cat << 'EOF' > "$BUILD_DIR/clean.sinc"
fn add_numbers(a, b) [
    ret a + b;
]

fn main() [
    result = add_numbers(10, 20);
    ret result;
]
EOF

set +e
STDOUT_OUT=$("$SLIM" check "$BUILD_DIR/clean.sinc" 2>/dev/null)
CODE=$?
set -e

if [[ $CODE -eq 0 ]] && echo "$STDOUT_OUT" | grep -q "\[SLIM: PASS\]"; then
    echo "PASS (Exit 0, [SLIM: PASS])"
else
    echo "FAIL (Expected exit 0 with [SLIM: PASS], got code $CODE: $STDOUT_OUT)"
    exit 1
fi

echo "========================================================================="
echo " ALL PHASE 1 S.L.I.M. TESTS PASSED WITH ZERO COMPILER IMPACT"
echo "========================================================================="
