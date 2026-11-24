#!/usr/bin/env bash
# =============================================================================
# tests/test_trg_boundary.sh
# TRG Boundary Safety Regression Gate (Zero Undefined Behavior / Zero SIGSEGV)
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SINC_ELF="$ROOT_DIR/bin/sinc.elf"
TRG_ENCODE="$ROOT_DIR/bin/trg_encode"
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/trg_boundary_XXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT

PASS=0
FAIL=0

test_boundary() {
    local name="$1"
    local expect_exit="$2"
    shift 2

    set +e
    out=$("$@" 2>&1)
    actual_exit=$?
    set -e

    if [ "$actual_exit" -eq "$expect_exit" ]; then
        printf 'PASS %-55s (Exit %s)\n' "$name" "$actual_exit"
        PASS=$((PASS + 1))
    else
        printf 'FAIL %-55s (Expected %s, got %s)\n' "$name" "$expect_exit" "$actual_exit"
        printf '     Output: %s\n' "$out"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== TRG BOUNDARY SAFETY REGRESSION GATE ==="

# 1. Byte-7 'T' Raw UTF-8 Source (Eliminating //aaaaaT SIGSEGV 139)
printf '//aaaaaT\nfn main() [ ret 42; ]\n' > "$TMP_DIR/byte7_t.sinc"
test_boundary "1. Raw UTF-8 with byte 7='T' directly to sinc.elf" 20 "$SINC_ELF" "$TMP_DIR/byte7_t.sinc" "$TMP_DIR/out.safe"

# 2. Truncated Container (< 64 bytes, src_len + 8 < 72)
python3 -c 'import sys; sys.stdout.buffer.write(b"T" * 32)' > "$TMP_DIR/truncated.trg"
test_boundary "2. Truncated container (32 bytes < 64 bytes)" 20 "$SINC_ELF" "$TMP_DIR/truncated.trg" "$TMP_DIR/out.safe"

# 3. Forged Length Over-Read (claimed 10MB, actual 80 bytes)
python3 -c 'import struct, sys; sys.stdout.buffer.write(struct.pack("<IBBBB56x", 10000000, 1, 0, 0, 84) + b"A"*16)' > "$TMP_DIR/forged.trg"
test_boundary "3. Forged length container over-read guard" 20 "$SINC_ELF" "$TMP_DIR/forged.trg" "$TMP_DIR/out.safe"

# 4. Corrupted Header Flags (flags != 0)
python3 -c 'import struct, sys; sys.stdout.buffer.write(struct.pack("<IBBBB56x", 16, 1, 0, 1, 84) + b"A"*16)' > "$TMP_DIR/corrupt_flags.trg"
test_boundary "4. Corrupt header flags rejection" 20 "$SINC_ELF" "$TMP_DIR/corrupt_flags.trg" "$TMP_DIR/out.safe"

# 5. Corrupted Script A (Script A != 1)
python3 -c 'import struct, sys; sys.stdout.buffer.write(struct.pack("<IBBBB56x", 16, 2, 0, 0, 84) + b"A"*16)' > "$TMP_DIR/corrupt_script.trg"
test_boundary "5. Unsupported Script A (!= 1) rejection" 20 "$SINC_ELF" "$TMP_DIR/corrupt_script.trg" "$TMP_DIR/out.safe"

# 6. Unsupported Character Outside Comments ($ / é) Fail-Fast in trg_encode
printf 'fn main() [ ret 42; ] $\n' > "$TMP_DIR/bad_dollar.sinc"
test_boundary "6. Unsupported byte ($) fail-fast in trg_encode" 21 "$TRG_ENCODE" "$TMP_DIR/bad_dollar.sinc" "$TMP_DIR/bad.trg"

echo "=== RESULTS: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi

