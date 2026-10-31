#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
DEFAULT_SINC="$ROOT_DIR/bin/sinc.elf"
[ -x "$DEFAULT_SINC" ] || DEFAULT_SINC="$ROOT_DIR/sinc.elf"
SINC=${SINC_COMPILER:-"$DEFAULT_SINC"}

DEFAULT_PACKAGER="$ROOT_DIR/bin/packager_bin"
[ -x "$DEFAULT_PACKAGER" ] || DEFAULT_PACKAGER="$ROOT_DIR/packager_bin"
PACKAGER=${PACKAGER:-"$DEFAULT_PACKAGER"}
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/sinc-term-test.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

echo "========================================================================="
echo "SINC Native Terminal Engine & Linux ioctl Integration Tests"
echo "========================================================================="

# Helper: compile and package a SINC program with STEEL sys and os_linux
compile_sinc_term_test() {
    local src="$1"
    local bin="$2"
    local combined="$WORK_DIR/combined_test.sinc"
    local safe="$WORK_DIR/test.safe"

    cat "$ROOT_DIR/steel/sys/sys.sinc" \
        "$ROOT_DIR/steel/sys/arena.sinc" \
        "$ROOT_DIR/steel/sys/os_linux.sinc" \
        "$src" > "$combined"

    "$SINC" "$combined" "$safe"
    "$PACKAGER" "$safe" "$bin"
    chmod +x "$bin"
}

# -------------------------------------------------------------------------
# Test 1: Terminal Window Size Query (TIOCGWINSZ via sys_ioctl)
# -------------------------------------------------------------------------
cat << 'EOF' > "$WORK_DIR/test1.sinc"
fn main!(argc, argv_ptr) [
    sys_mmap!(16777216);
    arena = arena_init!(536870912, 553648128);

    win_buf = arena_alloc_words!(arena, 1);
    win_buf@[0] = 0;
    res = steel_tty_winsize!(win_buf);
    // In a valid PTY, res == 0
    if (res != 0) [ sys_exit!(10); ]

    rows = win_buf@[0] & 65535;
    cols = (win_buf@[0] >> 16) & 65535;
    if ((rows != 24) | (cols != 80)) [ sys_exit!(11); ]

    sys_exit!(42);
]
EOF

compile_sinc_term_test "$WORK_DIR/test1.sinc" "$WORK_DIR/test1.elf"

python3 -c "
import pty, os, subprocess, fcntl, termios, struct
master, slave = pty.openpty()
# Set 24 rows x 80 cols on the PTY
fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
proc = subprocess.Popen(['$WORK_DIR/test1.elf'], stdin=slave, stdout=slave, stderr=slave, close_fds=True)
os.close(slave)
ret = proc.wait(timeout=3)
os.close(master)
assert ret == 42, f'Expected 42, got {ret}'
"
echo "[Test 1/3] Native Window Dimensions Query (TIOCGWINSZ)... PASS (rows=24, cols=80)"

# -------------------------------------------------------------------------
# Test 2: Instant Single-Keypress Raw Mode (VMIN=1, no Enter needed)
# -------------------------------------------------------------------------
cat << 'EOF' > "$WORK_DIR/test2.sinc"
fn main!(argc, argv_ptr) [
    sys_mmap!(16777216);
    arena = arena_init!(536870912, 553648128);

    raw_buf = arena_alloc_words!(arena, 5);
    saved_buf = arena_alloc_words!(arena, 5);
    if (steel_tty_raw!(raw_buf, saved_buf) != 0) [ sys_exit!(20); ]

    key_buf = arena_alloc_words!(arena, 1);
    bytes_read = sys_read!(0, key_buf, 1);
    if (bytes_read != 1) [ sys_exit!(21); ]
    key = key_buf@[0] & 255;

    steel_tty_cooked!(saved_buf);
    sys_exit!(key);
]
EOF

compile_sinc_term_test "$WORK_DIR/test2.sinc" "$WORK_DIR/test2.elf"

python3 -c "
import pty, os, subprocess
master, slave = pty.openpty()
os.write(master, b'Z') # Send raw single char 'Z' without newline
proc = subprocess.Popen(['$WORK_DIR/test2.elf'], stdin=slave, stdout=slave, stderr=slave, close_fds=True)
os.close(slave)
ret = proc.wait(timeout=3)
os.close(master)
assert ret == 90, f'Expected 90 (ASCII Z), got {ret}'
"
echo "[Test 2/3] Instant Raw Keypress without Enter (ASCII Z)... PASS (exit code = 90)"

# -------------------------------------------------------------------------
# Test 3: Non-Blocking Keyboard Polling (VMIN=0, VTIME=0)
# -------------------------------------------------------------------------
cat << 'EOF' > "$WORK_DIR/test3.sinc"
fn main!(argc, argv_ptr) [
    sys_mmap!(16777216);
    arena = arena_init!(536870912, 553648128);

    raw_buf = arena_alloc_words!(arena, 5);
    saved_buf = arena_alloc_words!(arena, 5);
    if (steel_tty_nonblocking!(raw_buf, saved_buf) != 0) [ sys_exit!(30); ]

    key_buf = arena_alloc_words!(arena, 1);
    // With no input piped, read MUST return 0 immediately without blocking
    bytes_read = sys_read!(0, key_buf, 1);
    if (bytes_read != 0) [ sys_exit!(31); ]

    // Cooked restoration
    if (steel_tty_cooked!(saved_buf) != 0) [ sys_exit!(32); ]

    sys_exit!(77);
]
EOF

compile_sinc_term_test "$WORK_DIR/test3.sinc" "$WORK_DIR/test3.elf"

python3 -c "
import pty, os, subprocess
master, slave = pty.openpty()
proc = subprocess.Popen(['$WORK_DIR/test3.elf'], stdin=slave, stdout=slave, stderr=slave, close_fds=True)
os.close(slave)
ret = proc.wait(timeout=3)
os.close(master)
assert ret == 77, f'Expected 77, got {ret}'
"
echo "[Test 3/3] Non-Blocking Read Polling (VMIN=0, VTIME=0)... PASS (read returns 0, exit = 77)"

echo "========================================================================="
echo "ALL 3 NATIVE TERMINAL TESTS PASSED! NATIVE TTY IS 100% OPERATIONAL!"
echo "========================================================================="
