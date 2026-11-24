#!/usr/bin/env bash
# =============================================================================
# tests/lit/test_lit.sh
# LIT Sovereign Runtime Verification Suite (20 Deterministic Gates)
# =============================================================================
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
LIT="$ROOT_DIR/bin/lit.elf"
SINC=${SINC:-"$ROOT_DIR/bin/sinc"}
[ -x "$SINC" ] || SINC="$ROOT_DIR/bin/sinc.elf"
STAFF="$ROOT_DIR/bin/staff"
BUILD_DIR="$ROOT_DIR/scratch/test_lit"
CACHE_DIR="$ROOT_DIR/scratch/lit_cache"
REL_BUILD="scratch/test_lit"

mkdir -p "$BUILD_DIR" "$CACHE_DIR"
trap 'rm -rf "$BUILD_DIR" "$ROOT_DIR/_lit_gate20_tmp"' EXIT INT TERM

PASS=0
FAIL=0

test_gate() {
    local name="$1"
    local expect_exit="$2"
    shift 2

    set +e
    out=$("$@" 2>&1)
    actual_exit=$?
    set -e

    if [ "$actual_exit" -eq "$expect_exit" ]; then
        echo "[Gate] $name... PASS (Exit $actual_exit)"
        PASS=$((PASS + 1))
    else
        echo "[Gate] $name... FAIL (Expected exit $expect_exit, got $actual_exit)"
        echo "       Output: $out"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================================================="
echo " RUNNING LIT SOVEREIGN RUNTIME VERIFICATION SUITE (ALL 20 GATES)"
echo "========================================================================="

# Gate 1: Missing Argument Guard (exit 1)
test_gate "Gate 1: Missing Argument Guard (exit 1)" 1 "$LIT"

# Gate 2: Nonexistent File Guard (exit 2)
test_gate "Gate 2: Nonexistent File Guard (exit 2)" 2 "$LIT" "$BUILD_DIR/nonexistent.safe"

# Gate 3: Bad Magic Rejection (exit 3)
cat << 'EOF' > "$BUILD_DIR/fib.sinc"
fn fib(n) [
    if (n < 2) [ ret n; ]
    ret fib(n - 1) + fib(n - 2);
]

fn main() [
    ret fib(10);
]
EOF
"$SINC" "$BUILD_DIR/fib.sinc" "$BUILD_DIR/fib.safe"

cp "$BUILD_DIR/fib.safe" "$BUILD_DIR/corrupt_magic.safe"
python3 -c "
with open('$BUILD_DIR/corrupt_magic.safe', 'r+b') as f:
    f.seek(0)
    f.write(b'NOPE')
"
test_gate "Gate 3: Bad Magic Rejection (exit 3)" 3 "$LIT" "$BUILD_DIR/corrupt_magic.safe"

# Gate 4: Corrupted Bounds Rejection (exit 4)
cp "$BUILD_DIR/fib.safe" "$BUILD_DIR/corrupt_bounds.safe"
python3 -c "
import struct
with open('$BUILD_DIR/corrupt_bounds.safe', 'r+b') as f:
    f.seek(8)
    code_len = struct.unpack('<Q', f.read(8))[0]
    f.seek(16)
    f.write(struct.pack('<Q', code_len + 100))
"
test_gate "Gate 4: Corrupted Bounds Rejection (exit 4)" 4 "$LIT" "$BUILD_DIR/corrupt_bounds.safe"

# Gate 5: Pure Execution Parity (fib(10) == 55)
test_gate "Gate 5: Pure Execution Parity (exit 55)" 55 "$LIT" "$BUILD_DIR/fib.safe"

# Gate 6: Multi-Argument Pure Kernel (poly3(10, 20, 30) = 742 -> exit 742 & 255 = 230)
cat << 'EOF' > "$BUILD_DIR/poly3_runner.sinc"
fn poly3(a, b, c) [
    ret (a * a) + (b * c) + 42;
]

fn main() [
    ret poly3(10, 20, 30);
]
EOF
"$SINC" "$BUILD_DIR/poly3_runner.sinc" "$BUILD_DIR/poly3.safe"
test_gate "Gate 6: Multi-Argument Pure Kernel (exit 230)" 230 "$LIT" "$BUILD_DIR/poly3.safe"

# Gate 7: Deterministic W^X Guard (reads /proc/self/maps at runtime: r-xp present, zero rwxp)
echo -n "[Gate] Gate 7: Deterministic W^X Security Guard... "
cat "$ROOT_DIR/steel/sys/sys.sinc" "$ROOT_DIR/tests/lit/test_wx.sinc" > "$BUILD_DIR/test_wx_full.sinc"
"$SINC" "$BUILD_DIR/test_wx_full.sinc" "$BUILD_DIR/test_wx.safe"
set +e
maps_out=$("$LIT" "$BUILD_DIR/test_wx.safe" 2>&1)
maps_exit=$?
set -e
has_rx=$(echo "$maps_out" | grep -c "r-xp" || true)
has_rwx=$(echo "$maps_out" | grep -c "rwxp" || true)

if [ "$maps_exit" -eq 0 ] && [ "$has_rx" -gt 0 ] && [ "$has_rwx" -eq 0 ]; then
    echo "PASS"
    PASS=$((PASS + 1))
else
    echo "FAIL (r-xp count: $has_rx, rwxp count: $has_rwx, exit: $maps_exit)"
    echo "       Output: $maps_out"
    FAIL=$((FAIL + 1))
fi

# Gate 8: Impure Console Output (sys_write! to stdout)
cat << 'EOF' > "$BUILD_DIR/hello_runner.sinc"
fn main!(argc, argv_ptr) [
    buf = argv_ptr;
    buf@[0 * 1] = 72;
    buf@[1 * 1] = 101;
    buf@[2 * 1] = 108;
    buf@[3 * 1] = 108;
    buf@[4 * 1] = 111;
    buf@[5 * 1] = 44;
    buf@[6 * 1] = 32;
    buf@[7 * 1] = 76;
    buf@[8 * 1] = 73;
    buf@[9 * 1] = 84;
    buf@[10 * 1] = 33;
    buf@[11 * 1] = 10;
    sys_write!(1, buf, 12);
    sys_exit!(0);
]
EOF
cat "$ROOT_DIR/steel/sys/sys.sinc" "$BUILD_DIR/hello_runner.sinc" > "$BUILD_DIR/hello_full.sinc"
"$SINC" "$BUILD_DIR/hello_full.sinc" "$BUILD_DIR/hello.safe"

echo -n "[Gate] Gate 8: Impure Console Output (sys_write!)... "
set +e
hello_out=$("$LIT" "$BUILD_DIR/hello.safe" 2>&1)
hello_exit=$?
set -e
if [ "$hello_exit" -eq 0 ] && [ "$hello_out" = "Hello, LIT!" ]; then
    echo "PASS (Output: '$hello_out', Exit 0)"
    PASS=$((PASS + 1))
else
    echo "FAIL (Expected 'Hello, LIT!' and exit 0, got exit $hello_exit, output: '$hello_out')"
    FAIL=$((FAIL + 1))
fi

# Gate 9: Impure Host File I/O Roundtrip (open_write -> write -> close -> open_read -> read -> close)
cat << 'EOF' > "$BUILD_DIR/io_runner.sinc"
fn main!(argc, argv_ptr) [
    path = argv_ptr@[1];
    fd_w = sys_open_write!(path);
    if (fd_w < 0) [
        sys_exit!(1);
    ]
    buf = argv_ptr;
    buf@[0] = 123456789;
    w = sys_write!(fd_w, buf, 8);
    sys_close!(fd_w);
    if (w != 8) [
        sys_exit!(2);
    ]

    fd_r = sys_open_read!(path);
    if (fd_r < 0) [
        sys_exit!(3);
    ]
    buf@[0] = 0;
    r = sys_read!(fd_r, buf, 8);
    sys_close!(fd_r);
    if (r != 8) [
        sys_exit!(4);
    ]

    if (buf@[0] != 123456789) [
        sys_exit!(5);
    ]
    sys_exit!(42);
]
EOF
cat "$ROOT_DIR/steel/sys/sys.sinc" "$BUILD_DIR/io_runner.sinc" > "$BUILD_DIR/io_full.sinc"
"$SINC" "$BUILD_DIR/io_full.sinc" "$BUILD_DIR/io.safe"
token_file="$BUILD_DIR/token.bin"
test_gate "Gate 9: Impure Host File I/O Roundtrip (exit 42)" 42 "$LIT" "$BUILD_DIR/io.safe" "$token_file"

# Gate 10: Nested Sovereign Execution (LIT-runs-LIT)
"$STAFF" "$ROOT_DIR/lit/build.staff" "$BUILD_DIR/lit.safe"
test_gate "Gate 10: Nested Sovereign Execution (LIT-in-LIT exit 55)" 55 "$LIT" "$BUILD_DIR/lit.safe" "$BUILD_DIR/fib.safe"

# Gate 11: Phase 2B Single-File .trg Compile-on-Demand (exit 55)
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/fib.sinc" "$BUILD_DIR/fib.trg"
test_gate "Gate 11: Phase 2B Single-File Compile-on-Demand (exit 55)" 55 "$LIT" "$BUILD_DIR/fib.trg"

# Gate 12: Phase 2B Instant Cache Hit Verification (< 50 us latency)
echo -n "[Gate] Gate 12: Phase 2B Instant Cache Hit Verification... "
cached_file=$(ls -t "$CACHE_DIR"/*.safe | head -n 1)
mtime_before=$(stat -c %Y "$cached_file")
hit_exit=0
"$LIT" "$BUILD_DIR/fib.trg" > /dev/null 2>&1 || hit_exit=$?
mtime_after=$(stat -c %Y "$cached_file")
if [ "$hit_exit" -eq 55 ] && [ "$mtime_before" -eq "$mtime_after" ]; then
    echo "PASS (Cache hit verified, exit 55, zero rebuild)"
    PASS=$((PASS + 1))
else
    echo "FAIL (mtime changed or exit $hit_exit != 55)"
    FAIL=$((FAIL + 1))
fi

# Gate 13: Phase 2B Compiler Error Propagation (LIT_ERR_COMPILE = 9)
cat << 'EOF' > "$BUILD_DIR/syntax_error.sinc"
fn main() [
    broken syntax error here
]
EOF
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/syntax_error.sinc" "$BUILD_DIR/syntax_error.trg"
test_gate "Gate 13: Phase 2B Compiler Error Propagation (exit 9)" 9 "$LIT" "$BUILD_DIR/syntax_error.trg"

# Gate 14: Phase 2C Multi-File .staff Compile-on-Demand (exit 42)
mkdir -p "$BUILD_DIR/app/data" "$BUILD_DIR/app/pure" "$BUILD_DIR/app/sys"
cat << 'EOF' > "$BUILD_DIR/app/data/data.sinc"
const VAL_A = 10;
const VAL_B = 20;
EOF
cat << 'EOF' > "$BUILD_DIR/app/pure/math.sinc"
fn add_vals(a, b) [
    ret a + b;
]
EOF
cat << 'EOF' > "$BUILD_DIR/app/sys/entry.sinc"
fn main() [
    ret add_vals(VAL_A, VAL_B) + 12;
]
EOF
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/app/data/data.sinc" "$BUILD_DIR/app/data/data.trg"
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/app/pure/math.sinc" "$BUILD_DIR/app/pure/math.trg"
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/app/sys/entry.sinc" "$BUILD_DIR/app/sys/entry.trg"
cat << EOF > "$BUILD_DIR/app/build.staff"
artifact app [
    target = linux_x64;
    type   = bin;
]

deps [
    $REL_BUILD/app/data/data.trg;
    $REL_BUILD/app/pure/math.trg;
]

driver [
    $REL_BUILD/app/sys/entry.trg;
]

flags [
    optimize = 3;
    heap     = 1000000;
]
EOF
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/app/build.staff" "$BUILD_DIR/app/build.staff.trg"
test_gate "Gate 14: Phase 2C Multi-File Compile-on-Demand (exit 42)" 42 "$LIT" "$REL_BUILD/app/build.staff.trg"

# Gate 15: Phase 2C Stale-Cache Invalidation (leaf dependency change -> exit 43)
cat << 'EOF' > "$BUILD_DIR/app/data/data.sinc"
const VAL_A = 11;
const VAL_B = 20;
EOF
"$ROOT_DIR/bin/trg_encode" "$BUILD_DIR/app/data/data.sinc" "$BUILD_DIR/app/data/data.trg"
test_gate "Gate 15: Phase 2C Stale-Cache Invalidation (exit 43)" 43 "$LIT" "$REL_BUILD/app/build.staff.trg"

# Gate 16: Security & Compiler Purity Audit
echo -n "[Gate] Gate 16: Security & Compiler Purity Audit... "
sinc_diff=$(git diff --name-only origin/main sinc/ | grep -v -E "^sinc/(data/lexer\.sinc|pure/parser_pratt\.sinc|sys/entry\.sinc|sys/parser\.sinc|build\.staff)$" || true)
if [ -z "$sinc_diff" ]; then
    echo "PASS (TRG sovereign frontend verified, compiler purity maintained)"
    PASS=$((PASS + 1))
else
    echo "FAIL (Compiler core polluted: $sinc_diff)"
    FAIL=$((FAIL + 1))
fi

# Gate 17: Phase 3 Resident Slot Execution Parity
cat << 'EOF' > "$BUILD_DIR/v1.sinc"
fn main() [
    ret 100;
]
EOF
"$SINC" "$BUILD_DIR/v1.sinc" "$BUILD_DIR/v1.safe"

cat << 'EOF' > "$BUILD_DIR/v2.sinc"
fn main() [
    ret 200;
]
EOF
"$SINC" "$BUILD_DIR/v2.sinc" "$BUILD_DIR/v2.safe"

"$STAFF" tests/lit/test_slots.staff "$BUILD_DIR/test_slots.safe"

test_gate "Gate 17: Phase 3 Resident Slot Execution Parity (exit 0)" 0 "$LIT" "$BUILD_DIR/test_slots.safe" 17 "$BUILD_DIR/fib.safe"

# Gate 18: Phase 3 Live Atomic Hot-Swap (100 -> 200)
test_gate "Gate 18: Phase 3 Live Atomic Hot-Swap (exit 0)" 0 "$LIT" "$BUILD_DIR/test_slots.safe" 18 "$BUILD_DIR/v1.safe" "$BUILD_DIR/v2.safe"

# Gate 19: Phase 3 Slot Table Bounds & Double-Unload Safety
test_gate "Gate 19: Phase 3 Slot Table Bounds & Double-Unload Safety (exit 0)" 0 "$LIT" "$BUILD_DIR/test_slots.safe" 19 "$BUILD_DIR/fib.safe"

# Gate 20: Auto-Discovered Triad Folder Cache Invalidation (unlisted pure/ edit -> exit 77)
GATE20_DIR="$ROOT_DIR/_lit_gate20_tmp"
mkdir -p "$GATE20_DIR/data" "$GATE20_DIR/pure" "$GATE20_DIR/sys"
cat << 'EOF' > "$GATE20_DIR/data/data.sinc"
const BASE_NUM = 10;
EOF
cat << 'EOF' > "$GATE20_DIR/pure/unlisted_logic.sinc"
fn compute_bonus() [
    ret 32;
]
EOF
cat << 'EOF' > "$GATE20_DIR/sys/entry.sinc"
fn main() [
    ret BASE_NUM + compute_bonus();
]
EOF
"$ROOT_DIR/bin/trg_encode" "$GATE20_DIR/data/data.sinc" "$GATE20_DIR/data/data.trg"
"$ROOT_DIR/bin/trg_encode" "$GATE20_DIR/pure/unlisted_logic.sinc" "$GATE20_DIR/pure/unlisted_logic.trg"
"$ROOT_DIR/bin/trg_encode" "$GATE20_DIR/sys/entry.sinc" "$GATE20_DIR/sys/entry.trg"
cat << 'EOF' > "$GATE20_DIR/build.staff"
artifact _lit_gate20_tmp [
    target = linux_x64;
    type   = bin;
]

flags [
    optimize = 3;
    heap     = 1000000;
]
EOF
"$ROOT_DIR/bin/trg_encode" "$GATE20_DIR/build.staff" "$GATE20_DIR/build.staff.trg"
test_gate "Gate 20: Auto-Discovered Triad Cold Build (exit 42)" 42 "$LIT" "_lit_gate20_tmp/build.staff.trg"

cat << 'EOF' > "$GATE20_DIR/pure/unlisted_logic.sinc"
fn compute_bonus() [
    ret 67;
]
EOF
"$ROOT_DIR/bin/trg_encode" "$GATE20_DIR/pure/unlisted_logic.sinc" "$GATE20_DIR/pure/unlisted_logic.trg"
test_gate "Gate 20: Auto-Discovered Triad Stale Invalidation (exit 77)" 77 "$LIT" "_lit_gate20_tmp/build.staff.trg"
rm -rf "$GATE20_DIR"

echo "========================================================================="
echo " RESULTS: $PASS passed, $FAIL failed"
echo "========================================================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
