#!/usr/bin/env bash
# =============================================================================
# tests/staff/test_staff.sh
# SINC STAFF: Sovereign Parasite Automated Integration Test Suite
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
STAFF="$ROOT_DIR/bin/staff"
PACKAGER="$ROOT_DIR/bin/packager_bin"
BUILD_DIR="$ROOT_DIR/scratch/test_staff"

mkdir -p "$BUILD_DIR"

PASS=0
FAIL=0

test_cmd() {
    local name="$1"
    local expect_exit="$2"
    shift 2

    set +e
    out=$("$@" 2>&1)
    actual_exit=$?
    set -e

    if [ "$actual_exit" -eq "$expect_exit" ]; then
        echo "[Test] $name... PASS (Exit $actual_exit)"
        PASS=$((PASS + 1))
    else
        echo "[Test] $name... FAIL (Expected exit $expect_exit, got $actual_exit)"
        echo "       Output: $out"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================================================="
echo " RUNNING SINC STAFF INTEGRATION TESTS"
echo "========================================================================="

# 1. Missing arguments guard (argc < 2 -> exit 1)
test_cmd "No arguments guard (exit 1)" 1 "$STAFF"

# 2. Non-existent manifest path (exit 2)
test_cmd "Nonexistent manifest guard (exit 2)" 2 "$STAFF" "$BUILD_DIR/nonexistent.staff" "$BUILD_DIR/out.safe"

# 3. Compile SINC via staff
test_cmd "Compile SINC manifest (sinc/build.staff)" 0 "$STAFF" "$ROOT_DIR/sinc/build.staff" "$BUILD_DIR/sinc.safe"
"$PACKAGER" "$BUILD_DIR/sinc.safe" "$BUILD_DIR/sinc.elf"
chmod +x "$BUILD_DIR/sinc.elf"

# Verify compiled SINC can compile a basic program
echo 'fn main() [ ret 42; ]' > "$BUILD_DIR/test_prog.sinc"
"$BUILD_DIR/sinc.elf" "$BUILD_DIR/test_prog.sinc" "$BUILD_DIR/test_prog.safe"
"$PACKAGER" "$BUILD_DIR/test_prog.safe" "$BUILD_DIR/test_prog.elf"
chmod +x "$BUILD_DIR/test_prog.elf"
test_cmd "Execute binary compiled by STAFF-built SINC (returns 42)" 42 "$BUILD_DIR/test_prog.elf"

# 4. Self-host STAFF (Stage 2)
test_cmd "Compile STAFF manifest (staff/build.staff) -> Stage 2" 0 "$STAFF" "$ROOT_DIR/staff/build.staff" "$BUILD_DIR/staff_s2.safe"
"$PACKAGER" "$BUILD_DIR/staff_s2.safe" "$BUILD_DIR/staff_s2"
chmod +x "$BUILD_DIR/staff_s2"

# 5. Fixed-point verification (Stage 2 compiles Stage 3)
test_cmd "Stage 2 compiles Stage 3" 0 "$BUILD_DIR/staff_s2" "$ROOT_DIR/staff/build.staff" "$BUILD_DIR/staff_s3.safe"
if cmp -s "$BUILD_DIR/staff_s2.safe" "$BUILD_DIR/staff_s3.safe"; then
    echo "[Test] Bitwise identical fixed point (Stage 2 == Stage 3)... PASS"
    PASS=$((PASS + 1))
else
    echo "[Test] Bitwise identical fixed point (Stage 2 == Stage 3)... FAIL"
    FAIL=$((FAIL + 1))
fi

# 6. Compile HOUND via staff
test_cmd "Compile HOUND manifest (hound/build.staff)" 0 "$STAFF" "$ROOT_DIR/hound/build.staff" "$BUILD_DIR/hound.safe"
"$PACKAGER" "$BUILD_DIR/hound.safe" "$BUILD_DIR/hound.elf"
chmod +x "$BUILD_DIR/hound.elf"

# 7. Compile SLIM via staff
test_cmd "Compile SLIM manifest (slim/build.staff)" 0 "$STAFF" "$ROOT_DIR/slim/build.staff" "$BUILD_DIR/slim.safe"
"$PACKAGER" "$BUILD_DIR/slim.safe" "$BUILD_DIR/slim.elf"
chmod +x "$BUILD_DIR/slim.elf"
test_cmd "Execute binary compiled by STAFF-built SLIM (returns 1 for help)" 1 "$BUILD_DIR/slim.elf"

echo "========================================================================="
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo " ALL $TOTAL STAFF INTEGRATION TESTS PASSED"
    exit 0
else
    echo " $FAIL/$TOTAL STAFF INTEGRATION TESTS FAILED"
    exit 1
fi
