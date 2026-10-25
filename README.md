# SINC

**SINC** is an experimental, self-hosted systems language and compiler that compiles directly to x86-64 machine code with zero external dependencies (no libc, no LLVM, no external assembler or linker).

Built to explore **Speed, Safety, and Simplicity (SSS)**—checking side effects, pointer ownership, and buffer bounds at compile time while keeping the entire compiler small enough (~4,200 lines of SINC, ~71 KB binary, ~4 ms self-build) for one person to understand end to end.

---

## A Sample of SINC

```sinc
const BASE_OFFSET = 16;

// Pure function: math only, zero side effects
fn compute_offset(idx) [
    ret idx * 8 + BASE_OFFSET;
]

// Impure function: writes to a bounded 64-word buffer
fn fill_buffer!(buf:64, count:64) [
    loop (i:64 = 0 .. count) [
        buf@[i] = compute_offset(i);
    ]
    ret 0;
]

fn main!(work_buf:64) [
    fill_buffer!(work_buf~, 64); // '~' borrows work_buf without consuming it
    ret work_buf@[0];
]
```

* **`!` (Effects):** Marks functions that touch memory or OS syscalls; pure `fn` functions cannot call `!` functions or write to memory.
* **`~` (Borrowing):** Buffers and pointers move by default; trailing `~` borrows them without consuming ownership.
* **`:N` (Bounds):** Proves array and loop limits at compile time (Error 15 on out-of-bounds) so the CPU runs raw loads and stores with zero runtime checks.
* **`@` and constant lenses (Memory):** `ptr@` and `ptr@[i]` provide direct word or byte-scaled addressing; `ptr.LENS` names a fixed 8-byte slot without struct or type-system bloat.

---

## Quick Start

SINC runs natively on Linux x86-64. The repository includes pre-built bootstrap binaries in `bin/` so no external toolchains or compilers are required.

### 1. Compile and Run a Single File

SINC uses a two-step toolchain: `sinc.elf` compiles source into a raw x86-64 machine code payload (`.safe`), and `packager_bin` wraps it into an executable Linux ELF.

```bash
# 1. Write a minimal systems routine
echo "fn main() [ ret 42; ]" > target.sinc

# 2. Compile to a .safe machine code payload
./bin/sinc.elf target.sinc target.safe

# 3. Package into a standalone executable and run
./bin/packager_bin target.safe ./target
chmod +x ./target
./target
echo "Exit: $?" # prints 42
```

> **Disassembly Note:** `packager_bin` emits lean, stripped headerless ELF binaries (`e_shnum = 0`) where the entrypoint is located at file offset `0x78` (`_start`). When inspecting compiled binaries with GNU `objdump`, pass `--start-address=0x78` (e.g. `objdump -d --start-address=0x78 ./target`) or use raw binary mode (`objdump -D -b binary -m i386:x86-64 target`).

> **C/C++ FFI:** SINC also emits standard `.o` object files for direct linking into C/C++ projects via `bin/packager_o` (see [Chapter 12](manual/ch12_steel_sys.md)).

### 2. Build Projects with STAFF

```bash
# Build multi-file projects using their declarative manifest
./bin/staff build.staff target.safe
```

### 3. Self-Host & Verify Fixed Point

```bash
# Rebuild the SINC compiler using itself via STAFF
./build.sh

# Verify bitwise deterministic self-hosting (Stage 2 == Stage 3)
bash tests/staff/test_staff.sh
```

---

## Repository Map

| Directory | Role & Description |
| :--- | :--- |
| **[`sinc/`](sinc/README.md)** | The self-hosted flat-tape compiler core (lexer, Pratt parser, LICM/vectorizer/simplify/DCE passes, register allocator, and x86-64 emitter). |
| **[`steel/`](steel/README.md)** | The standard library (bump arenas, string slices, FNV-1a hash, symbol tables, Linux syscalls, `.safe` to ELF/`.o` packagers). |
| **[`staff/`](staff/README.md)** | The in-memory multi-file build tool (`build.staff`). |
| **[`slim/`](slim/README.md)** | *(Experimental Prototype — not yet fit for general use)* S.L.I.M. linter & inspection module (AST-free architectural constraints, mutation testing, and trace/benchmark gates). |
| **[`hound/`](hound/README.md)** | *(Experimental Prototype — not yet fit for general use)* HOUND runtime telemetry and terminal register monitor. |
| **[`manual/`](manual/SUMMARY.md)** | The complete SINC book & language manual, including the [Manifesto](manual/manifesto.md), FFI guide, and [FAQ](manual/appendix_d_faq.md). |

---

## Key Numbers

| Metric | Measurement (Intel Core i5-11400F) |
| :--- | :--- |
| **Self-Hosting Bootstrap Time** | **~4–5.5 ms** wall-clock / **~3.4 ms** CPU user time (full compiler self-compilation) |
| **Compiler Binary Size** | **~71 KB** (Standalone ELF) |
| **Compile Throughput** | **~1,000,000 LOC/s** (CPU user time) / **~780,000 LOC/s** (wall-clock) |
| **Runtime & Build Dependencies** | **0** (Linux x86-64 kernel only — zero libc, zero LLVM, zero external assembler/linker) |
| **Bootstrap Verification** | **100% Deterministic (`stage2 == stage3` bitwise identical)** |

---

## Project Status & Scope

* SINC is an experimental prototype targeting **Linux x86-64** (with AVX-512 support for loop vectorization).
* It is built to explore flat-tape compilation, zero-overhead compile-time safety, and self-hosting simplicity—not as a drop-in replacement for general-purpose production toolchains.
* All compiler passes operate directly over linear memory tapes without graph ASTs, heap allocators, or external runtime libraries.
