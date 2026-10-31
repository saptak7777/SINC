#!/usr/bin/env bash
# ==============================================================================
# tests/test_verify_bugs.sh
# Automated Verification Suite for SINC Compiler Bugs & Vulnerabilities
# ==============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEFAULT_SINC="$ROOT_DIR/bin/sinc.elf"
[ -x "$DEFAULT_SINC" ] || DEFAULT_SINC="$ROOT_DIR/sinc.elf"
SINC=${SINC:-"$DEFAULT_SINC"}

DEFAULT_PACKAGER="$ROOT_DIR/bin/packager_bin"
[ -x "$DEFAULT_PACKAGER" ] || DEFAULT_PACKAGER="$ROOT_DIR/packager_bin"
PACKAGER=${PACKAGER:-"$DEFAULT_PACKAGER"}
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/sinc-bug-tests.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

echo "=================================================="
echo "    SINC COMPILER BUG VERIFICATION SUITE"
echo "=================================================="

FAILED=0

# ------------------------------------------------------------------------------
# TEST 1: Loop Syntax Error Tape Corruption Bug (parser.sinc:106)
# When a syntax error occurs inside a loop (e.g. invalid % operator),
# parse_loop! fails to guard inst_count < 0, emits 5 IR instructions,
# and mutates error -7 into -2 (exiting with code 2 instead of 7).
# ------------------------------------------------------------------------------
echo -n "[BUG 1] Loop Syntax Error Error-Code Mutation... "
cat << 'EOF' > "$WORK_DIR/loop_syntax_err.sinc"
fn main() [
    loop (i = 0 .. 10) [
        if (i % 4 == 0) [
            ret 1;
        ]
    ]
    ret 0;
]
EOF

cat << 'EOF' > "$WORK_DIR/normal_syntax_err.sinc"
fn main() [
    i = 0;
    if (i % 4 == 0) [
        ret 1;
    ]
    ret 0;
]
EOF

set +e
"$SINC" "$WORK_DIR/normal_syntax_err.sinc" "$WORK_DIR/normal.safe" >/dev/null 2>&1
NORMAL_EXIT=$?
"$SINC" "$WORK_DIR/loop_syntax_err.sinc" "$WORK_DIR/loop.safe" >/dev/null 2>&1
LOOP_EXIT=$?
set -e

if [ "$NORMAL_EXIT" -eq 7 ] && [ "$LOOP_EXIT" -eq 7 ]; then
    echo "RESOLVED / FIXED (Both exit with code 7 as expected)"
elif [ "$NORMAL_EXIT" -eq 7 ] && [ "$LOOP_EXIT" -eq 2 ]; then
    echo "CONFIRMED BUGGY (Normal syntax error exits with 7, loop error mutated -7+5 into exit 2)"
    FAILED=$((FAILED + 1))
else
    echo "UNEXPECTED EXIT: Normal=$NORMAL_EXIT, Loop=$LOOP_EXIT"
    FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# TEST 2: CLI Driver Negative FD Signed Comparison Bypass (driver_linux.sinc:13)
# When compiling a nonexistent source file, fd_in is -2.
# Because -2 < 2147483648 in signed comparison, it skips sys_exit!(2),
# compiles an empty file, and exits with 0!
# ------------------------------------------------------------------------------
echo -n "[BUG 2] Nonexistent File Descriptor Bypass... "
set +e
"$SINC" "$WORK_DIR/this_file_definitely_does_not_exist_99999.sinc" "$WORK_DIR/nonexistent.safe" >/dev/null 2>&1
NONEXISTENT_EXIT=$?
set -e

if [ "$NONEXISTENT_EXIT" -eq 2 ]; then
    echo "RESOLVED / FIXED (Exited with code 2 as expected)"
elif [ "$NONEXISTENT_EXIT" -eq 0 ]; then
    echo "CONFIRMED BUGGY (Nonexistent file bypassed check and exited with code 0 instead of 2)"
    FAILED=$((FAILED + 1))
else
    echo "UNEXPECTED EXIT: $NONEXISTENT_EXIT"
    FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# TEST 3: Arithmetic Right Shift (SAR) Broken on Negative Numbers
# >> in SINC always emits shrx (logical shift), zero-filling high bits.
# -100 >> 2 should produce -25 (SAR), but produces 4611686018427387879 (SHR).
# ------------------------------------------------------------------------------
echo -n "[BUG 3] Right Shift >> on Negative Numbers (SAR vs SHR)... "
cat << 'EOF' > "$WORK_DIR/test_sar.sinc"
fn main() [
    val = -100;
    shifted = val >> 2;
    if (shifted == -25) [
        ret 42; // Correct arithmetic shift
    ]
    ret 99; // Corrupted logical shift
]
EOF

"$SINC" "$WORK_DIR/test_sar.sinc" "$WORK_DIR/test_sar.safe" >/dev/null 2>&1
"$PACKAGER" "$WORK_DIR/test_sar.safe" "$WORK_DIR/test_sar.elf" >/dev/null 2>&1
chmod +x "$WORK_DIR/test_sar.elf"
set +e
"$WORK_DIR/test_sar.elf" >/dev/null 2>&1
SAR_EXIT=$?
set -e

if [ "$SAR_EXIT" -eq 42 ]; then
    echo "RESOLVED / FIXED (Exited 42: proper arithmetic shift)"
elif [ "$SAR_EXIT" -eq 99 ]; then
    echo "CONFIRMED BUGGY (Exited 99: >> zero-fills negative numbers instead of sign-extending)"
    FAILED=$((FAILED + 1))
else
    echo "UNEXPECTED EXIT: $SAR_EXIT"
    FAILED=$((FAILED + 1))
fi

# ------------------------------------------------------------------------------
# TEST 4: Fake Test Assertion Omission (bmi_shlx_shrx_variable.sinc)
# Tests that if we assert on the SAR shift in bmi_shlx_shrx_variable.sinc,
# it fails immediately.
# ------------------------------------------------------------------------------
echo -n "[BUG 4] Hidden Failure in bmi_shlx_shrx_variable.sinc... "
cat << 'EOF' > "$WORK_DIR/bmi_sar_asserted.sinc"
fn test_variable_sar(val, amt) [
    ret val >> amt;
]

fn main() [
    z = -100;
    t3 = test_variable_sar(z, 2);
    // If SAR was real, t3 == -25.
    if (t3 == -25) [
        ret 10;
    ]
    ret 90; // Failed SAR assertion
]
EOF

"$SINC" "$WORK_DIR/bmi_sar_asserted.sinc" "$WORK_DIR/bmi_sar_asserted.safe" >/dev/null 2>&1
"$PACKAGER" "$WORK_DIR/bmi_sar_asserted.safe" "$WORK_DIR/bmi_sar_asserted.elf" >/dev/null 2>&1
chmod +x "$WORK_DIR/bmi_sar_asserted.elf"
set +e
"$WORK_DIR/bmi_sar_asserted.elf" >/dev/null 2>&1
BMI_EXIT=$?
set -e

if [ "$BMI_EXIT" -eq 10 ]; then
    echo "RESOLVED / FIXED (SAR works)"
elif [ "$BMI_EXIT" -eq 90 ]; then
    echo "CONFIRMED BUGGY (Asserting on SAR fails with exit 90; test suite hid this by returning t2+10)"
    FAILED=$((FAILED + 1))
else
    echo "UNEXPECTED EXIT: $BMI_EXIT"
    FAILED=$((FAILED + 1))
fi

echo "=================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "    ALL 4 BUGS RESOLVED & VERIFIED CLEAN (0 REGRESSIONS)"
    echo "=================================================="
    exit 0
else
    echo "    VERIFICATION FAILED: $FAILED BUGS OR REGRESSIONS DETECTED"
    echo "=================================================="
    exit 1
fi
