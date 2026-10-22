#!/usr/bin/env bash
# =============================================================================
# tests/integration/test_slim_phase2.sh
# S.L.I.M. Phase 2 Integration Tests: Bytecode Mutation Testing Engine
# Tests [TAG: WEAK TEST] and Mutant Elimination
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SLIM="${SLIM:-"$ROOT_DIR/bin/slim.elf"}"
SINC="$ROOT_DIR/bin/sinc.elf"
PACKAGER="$ROOT_DIR/bin/packager_bin"
BUILD_DIR="$ROOT_DIR/scratch/test_phase2"

mkdir -p "$BUILD_DIR"

if [[ ! -x "$SLIM" ]]; then
    echo "Building S.L.I.M. linter via STAFF..."
    "$ROOT_DIR/bin/staff" "$ROOT_DIR/slim/build.staff" "$BUILD_DIR/slim.safe"
    "$ROOT_DIR/bin/packager_bin" "$BUILD_DIR/slim.safe" "$ROOT_DIR/bin/slim.elf"
    chmod +x "$ROOT_DIR/bin/slim.elf"
    rm -f "$BUILD_DIR/slim.safe"
fi

echo "========================================================================="
echo " RUNNING SINC S.L.I.M. PHASE 2 TESTS (Bytecode Mutation Engine)"
echo "========================================================================="

# 1. Compile Impure Target with ADD operation
cat << 'EOF' > "$BUILD_DIR/target.sinc"
fn compute!(a, b) [
    ret a + b;
]

fn main!() [
    res = compute!(10, 20);
    ret res;
]
EOF

echo -n "[Test 1/3] Compiling and generating bytecode mutant... "
"$SINC" "$BUILD_DIR/target.sinc" "$BUILD_DIR/target.safe"
MUT_RES=$("$SLIM" mutate "$BUILD_DIR/target.safe" "$BUILD_DIR/target_mut.safe")

if [[ -f "$BUILD_DIR/target_mut.safe" ]] && echo "$MUT_RES" | grep -q "\[SLIM: PASS\]"; then
    echo "PASS (Mutated bytecode produced)"
else
    echo "FAIL (Failed to produce mutant)"
    exit 1
fi

# Package both binaries
"$PACKAGER" "$BUILD_DIR/target.safe" "$BUILD_DIR/target.elf"
"$PACKAGER" "$BUILD_DIR/target_mut.safe" "$BUILD_DIR/target_mut.elf"
chmod +x "$BUILD_DIR/target.elf" "$BUILD_DIR/target_mut.elf"

# Verify runtime divergence
set +e
"$BUILD_DIR/target.elf"
ORIG_EXIT=$?
"$BUILD_DIR/target_mut.elf"
MUT_EXIT=$?
set -e

if [[ $ORIG_EXIT -eq 30 ]] && [[ $MUT_EXIT -ne 30 ]]; then
    echo "    -> Verified: Original exit = 30, Mutated exit = $MUT_EXIT (Logic Inverted)"
else
    echo "FAIL: Expected divergent exit codes, got orig=$ORIG_EXIT, mut=$MUT_EXIT"
    exit 1
fi

# 2. Test weak test runner (ignores mutant divergence, exit 0)
echo -n "[Test 2/3] Evaluating weak test runner... "
set +e
WEAK_OUT=$("$SLIM" eval-mutant 0 2>&1 >/dev/null)
WEAK_CODE=$?
set -e

if [[ $WEAK_CODE -eq 1 ]] && echo "$WEAK_OUT" | grep -q "\[TAG: WEAK TEST\]"; then
    echo "PASS (Exit 1, [TAG: WEAK TEST] applied)"
else
    echo "FAIL (Expected exit 1 with [TAG: WEAK TEST], got $WEAK_CODE: $WEAK_OUT)"
    exit 1
fi

# 3. Test strong test runner (detects mutant divergence, exit != 0)
echo -n "[Test 3/3] Evaluating strong test runner... "
set +e
STRONG_OUT=$("$SLIM" eval-mutant 1 2>/dev/null)
STRONG_CODE=$?
set -e

if [[ $STRONG_CODE -eq 0 ]] && echo "$STRONG_OUT" | grep -q "\[SLIM: PASS\]"; then
    echo "PASS (Exit 0, mutant killed)"
else
    echo "FAIL (Expected exit 0 with [SLIM: PASS], got $STRONG_CODE: $STRONG_OUT)"
    exit 1
fi

echo "========================================================================="
echo " ALL PHASE 2 S.L.I.M. MUTATION TESTS PASSED"
echo "========================================================================="
