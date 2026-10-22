#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BUILD_DIR=$ROOT_DIR/scratch/build
MANIFEST=$ROOT_DIR/sinc/build.staff

DEFAULT_STAFF="$ROOT_DIR/bin/staff"
STAFF=${STAFF:-"$DEFAULT_STAFF"}

DEFAULT_PACKAGER="$ROOT_DIR/bin/packager_bin"
[ -x "$DEFAULT_PACKAGER" ] || DEFAULT_PACKAGER="$ROOT_DIR/packager_bin"
PACKAGER=${PACKAGER:-"$DEFAULT_PACKAGER"}

SAFE=$BUILD_DIR/sinc_compiler.safe
ELF=$BUILD_DIR/sinc_compiler.elf

[ -x "$STAFF" ] || { printf 'missing staff orchestrator: %s\n' "$STAFF" >&2; exit 2; }
[ -x "$PACKAGER" ] || { printf 'missing packager: %s\n' "$PACKAGER" >&2; exit 2; }
[ -f "$MANIFEST" ] || { printf 'missing manifest: %s\n' "$MANIFEST" >&2; exit 2; }

mkdir -p "$BUILD_DIR" "$ROOT_DIR/bin"

"$STAFF" "$MANIFEST" "$SAFE"
"$PACKAGER" "$SAFE" "$ELF"
chmod 755 "$ELF"
mv -f "$ELF" "$ROOT_DIR/bin/sinc.elf"
printf 'self-compiled compiler via STAFF: %s\n' "$ROOT_DIR/bin/sinc.elf"
sha256sum "$SAFE" "$ROOT_DIR/bin/sinc.elf"
