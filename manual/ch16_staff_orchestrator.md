# Chapter 16: SINC STAFF — Project Orchestrator

> **Project Status: Experimental Prototype**  
> STAFF (`./bin/staff`) is the project build tool for SINC. It parses a `build.staff` manifest, collects project sources across the Universal Triad, and compiles them directly into an executable `.safe` payload in memory.

---

## 1. Design and Execution

STAFF compiles multi-file projects without external toolchain dependencies:
* **Written in SINC**: Implemented entirely in SINC without external libraries or runtimes.
* **In-Memory Compilation**: Rather than writing temporary merged files to disk, STAFF reads source files into a contiguous bump arena and passes the buffer directly to `compile_core!`.
* **Fast Execution**: A full project manifest build completes in ~4 milliseconds.

---

## 2. The Universal SINC Triad

STAFF expects projects to follow the SINC Triad layout:

```text
my_project/
├── build.staff         # Project manifest
├── data/               # Constants, lenses, bitmasks, memory layouts
│   └── defs.sinc
├── pure/               # Pure functions (fn), math, transformers
│   └── logic.sinc
└── sys/                # Impure effects (fn ...!), syscalls, entrypoint
    └── entry.sinc      # Contains fn main!()
```

### The Three Layers:
1. **`data/`**:
   * Holds constants (`const FOO = 42;`), layout lenses, and lookup tables.
   * **Rule**: Zero logic, zero function declarations, zero side-effects.
2. **`pure/`**:
   * Holds mathematical algorithms and data transformations declared with pure `fn`.
   * **Rule**: Cannot contain impure functions (`fn ...!`), cannot perform syscalls or touch OS state.
3. **`sys/`**:
   * Holds OS interaction, syscalls, and the program entrypoint (`fn main!()`).
   * **Rule**: Impure code lives here. The entrypoint `main!()` in `entry.sinc` is guaranteed to be linked last.

---

## 3. Manifest Format (`build.staff`)

A standard manifest declares the project artifact, dependencies, and optional host driver:

```text
artifact my_service []

deps [
    steel/sys/sys.sinc;
    steel/sys/arena.sinc;
]

driver [
    steel/sys/driver_linux.sinc;
]
```

STAFF automatically appends files in strict universal order:
1. All files declared in `deps [...]` (in declared order)
2. All `.sinc` files found inside `data/` (sorted in strict lexicographical order)
3. All `.sinc` files found inside `pure/` (sorted in strict lexicographical order)
4. All `.sinc` files found inside `sys/` (sorted in strict lexicographical order, excluding `entry.sinc`)
5. `<root>/sys/entry.sinc`
6. Optional `driver` (if declared)

Within each tray (`data/`, `pure/`, `sys/`), STAFF sorts file names lexicographically in-place before reading. This guarantees 100% bitwise deterministic compilation across different filesystems (ext4, btrfs, tmpfs) and platforms.

### Manifest Contract & Fail-Fast Architectural Ceilings

Under SINC's Single Source of Truth principle (Rule 3) and Fail-Fast philosophy (Rule 4):
* **Internal Triad Files Belong Exclusively to Auto-Streaming:** Files located in `data/`, `pure/`, or `sys/` are automatically streamed by STAFF. They must **never** be manually listed in `deps [...]`.
* **Direct Structural Rejection:** If a broken manifest duplicates an internal `<root>/...` file in `deps [...]`, STAFF rejects the manifest immediately with **Exit Code 5** (`STAFF Manifest / Tray Capacity Violation`).
* **Missing Dependencies Fail Fast:** If a path in `deps [...]` cannot be opened or read, STAFF halts immediately with **Exit Code 2** (`File Open / Read Failure`).
* **Bounded Tray Limits:** Each triad directory tray supports up to 127 ordinary discovered `.sinc` files (with `sys/entry.sinc` becoming the 128th source in `sys/`) and a 64 KiB directory record scan buffer. Exceeding 127 discovered files immediately halts compilation with **Exit Code 5**.

---

## 4. CLI Usage & Build Workflow

For v0.01 / v1, we keep things simple and manual. STAFF accepts the manifest path and the target output path:

```text
Usage: ./bin/staff <manifest.staff> [output.safe]
```

### Compiling a Project

```bash
# 1. Compile manifest directly to .safe machine code payload
./bin/staff my_project/build.staff my_project.safe

# 2. Package into a standalone Linux ELF binary
./bin/packager_bin my_project.safe ./my_project
chmod +x ./my_project

# 3. Run it
./my_project
```

### Self-Hosting STAFF
Because STAFF is written in SINC itself, it can compile its own manifest:

```bash
# Compile Stage 2 STAFF binary
./bin/staff staff/build.staff scratch/staff_s2.safe
./bin/packager_bin scratch/staff_s2.safe bin/staff
chmod +x bin/staff
```

This self-compilation reaches a bitwise identical fixed point (`stage2 == stage3`) in ~4–5.5 ms wall-clock (~3.4 ms CPU user time).

