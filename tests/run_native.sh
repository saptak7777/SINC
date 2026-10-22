#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEFAULT_SINC="$ROOT_DIR/bin/sinc.elf"
[ -x "$DEFAULT_SINC" ] || DEFAULT_SINC="$ROOT_DIR/sinc.elf"
SINC=${1:-${SINC:-"$DEFAULT_SINC"}}

DEFAULT_PACKAGER="$ROOT_DIR/bin/packager_bin"
[ -x "$DEFAULT_PACKAGER" ] || DEFAULT_PACKAGER="$ROOT_DIR/packager_bin"
PACKAGER=${2:-${PACKAGER:-"$DEFAULT_PACKAGER"}}
TEST_DIR=${TEST_DIR:-"$ROOT_DIR/tests/native"}
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/sinc-native-tests.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

if [ ! -x "$SINC" ]; then
    printf 'missing executable compiler: %s\n' "$SINC" >&2
    exit 2
fi
if [ ! -x "$PACKAGER" ]; then
    printf 'missing executable packager: %s\n' "$PACKAGER" >&2
    exit 2
fi

passed=0
failed=0

for source in "$TEST_DIR"/*.sinc; do
    name=$(basename "$source" .sinc)
    safe="$WORK_DIR/$name.safe"
    binary="$WORK_DIR/$name.elf"

    compile_error=$(sed -n 's|^// COMPILE_ERROR: \([0-9][0-9]*\)$|\1|p' "$source")
    if [ -n "$compile_error" ]; then
        set +e
        "$SINC" "$source" "$safe" >/dev/null 2>&1
        actual=$?
        set -e
        if [ "$actual" -eq "$compile_error" ]; then
            printf 'PASS %-32s rejected exit=%s\n' "$name" "$actual"
            passed=$((passed + 1))
        else
            printf 'FAIL %-32s compile exit=%s expected=%s\n' "$name" "$actual" "$compile_error"
            failed=$((failed + 1))
        fi
        continue
    fi

    expected=$(sed -n 's|^// EXPECT: \([0-9][0-9]*\)$|\1|p' "$source")
    if [ -z "$expected" ]; then
        printf 'FAIL %-32s missing EXPECT metadata\n' "$name"
        failed=$((failed + 1))
        continue
    fi
    if ! "$SINC" "$source" "$safe" >/dev/null 2>&1; then
        printf 'FAIL %-32s compiler rejected valid source\n' "$name"
        failed=$((failed + 1))
        continue
    fi
    if ! "$PACKAGER" "$safe" "$binary" >/dev/null 2>&1; then
        printf 'FAIL %-32s packager failed\n' "$name"
        failed=$((failed + 1))
        continue
    fi
    chmod +x "$binary"
    set +e
    "$binary" >/dev/null 2>&1
    actual=$?
    set -e
    if [ "$actual" -ne "$expected" ]; then
        printf 'FAIL %-32s exit=%s expected=%s\n' "$name" "$actual" "$expected"
        failed=$((failed + 1))
        continue
    fi

    require_insn=$(sed -n 's|^// REQUIRE_INSN: \(.*\)|\1|p' "$source")
    if [ -n "$require_insn" ]; then
        matched=$(objdump -b binary -m i386:x86-64 -D "$binary" 2>/dev/null | grep -c -E "$require_insn" || true)
        if [ "$matched" -eq 0 ]; then
            printf 'FAIL %-32s missing required instruction: %s\n' "$name" "$require_insn"
            failed=$((failed + 1))
            continue
        fi
    fi

    printf 'PASS %-32s exit=%s\n' "$name" "$actual"
    passed=$((passed + 1))
done

printf '\nNative tests: %s passed, %s failed\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
