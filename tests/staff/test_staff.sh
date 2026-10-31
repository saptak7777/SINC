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

# 8. Bounded getdents directory scan (>1000 non-source records)
LARGE_DIR="$BUILD_DIR/large_fixture"
rm -rf "$LARGE_DIR"
mkdir -p "$LARGE_DIR/app/data" "$LARGE_DIR/app/sys"
cat << 'EOF' > "$LARGE_DIR/app/build.staff"
artifact app [
]
EOF
for i in $(seq -w 1 1500); do
    touch "$LARGE_DIR/app/data/dummy_$i.txt"
done
cat << 'EOF' > "$LARGE_DIR/app/data/z_defs.sinc"
const SECRET_ANSWER = 42;
EOF
cat << 'EOF' > "$LARGE_DIR/app/sys/entry.sinc"
fn main!() [
    ret SECRET_ANSWER;
]
EOF
test_cmd "Compile project with >1000 non-source files" 0 bash -c "cd '$LARGE_DIR' && '$STAFF' app/build.staff out.safe"
"$PACKAGER" "$LARGE_DIR/out.safe" "$LARGE_DIR/out.elf"
chmod +x "$LARGE_DIR/out.elf"
test_cmd "Execute binary from >1000 file directory (returns 42)" 42 "$LARGE_DIR/out.elf"
rm -rf "$LARGE_DIR"

# 9. Duplicate internal dependency rejection (exit 5)
DUP_DIR="$BUILD_DIR/dup_fixture"
rm -rf "$DUP_DIR"
mkdir -p "$DUP_DIR/app/data" "$DUP_DIR/app/sys"
cat << 'EOF' > "$DUP_DIR/app/build.staff"
artifact app [
]
deps [
    app/data/defs.sinc;
]
EOF
echo 'const X = 1;' > "$DUP_DIR/app/data/defs.sinc"
echo 'fn main!() [ ret 0; ]' > "$DUP_DIR/app/sys/entry.sinc"
test_cmd "Duplicate internal dependency rejected (exit 5)" 5 bash -c "cd '$DUP_DIR' && '$STAFF' app/build.staff out.safe"
rm -rf "$DUP_DIR"

# 10. Missing dependency rejection (exit 2)
MISSING_DIR="$BUILD_DIR/missing_fixture"
rm -rf "$MISSING_DIR"
mkdir -p "$MISSING_DIR/app/sys"
cat << 'EOF' > "$MISSING_DIR/app/build.staff"
artifact app [
]
deps [
    steel/sys/nonexistent_file.sinc;
]
EOF
echo 'fn main!() [ ret 0; ]' > "$MISSING_DIR/app/sys/entry.sinc"
test_cmd "Missing dependency rejected (exit 2)" 2 bash -c "cd '$MISSING_DIR' && '$STAFF' app/build.staff out.safe"
rm -rf "$MISSING_DIR"

# 11. Tray capacity overflow (>127 discovered files, exit 5)
OVERFLOW_DIR="$BUILD_DIR/overflow_fixture"
rm -rf "$OVERFLOW_DIR"
mkdir -p "$OVERFLOW_DIR/app/data" "$OVERFLOW_DIR/app/sys"
cat << 'EOF' > "$OVERFLOW_DIR/app/build.staff"
artifact app [
]
EOF
for i in $(seq -w 1 128); do
    echo "const V$i = $i;" > "$OVERFLOW_DIR/app/data/file_$i.sinc"
done
echo 'fn main!() [ ret 0; ]' > "$OVERFLOW_DIR/app/sys/entry.sinc"
test_cmd "Tray capacity overflow >127 discovered files rejected (exit 5)" 5 bash -c "cd '$OVERFLOW_DIR' && '$STAFF' app/build.staff out.safe"
rm -rf "$OVERFLOW_DIR"

echo "========================================================================="
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo " ALL $TOTAL STAFF INTEGRATION TESTS PASSED"
    exit 0
else
    echo " $FAIL/$TOTAL STAFF INTEGRATION TESTS FAILED"
    exit 1
fi
