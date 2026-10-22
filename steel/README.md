# S.T.E.E.L. — SINC Typeless Ergonomic Extension Library

S.T.E.E.L. (**S**INC **T**ypeless **E**rgonomic **E**xtension **L**ibrary) is the minimal standard library prototype for SINC, providing simple memory arenas, byte streams, string slices, and raw Linux syscall thunks with zero dependencies on libc.

```text
steel/
├── steel.sinc              # Standard library prelude index
│
├── data/                   # Data structures & fat pointers
│   └── slice.sinc          # 2-word fat pointer string slice engine
│
├── pure/                   # Pure TEXT: Math & Algorithms (Zero '!', Zero OS)
│   ├── bitset.sinc         # 64-bit word bitset operations
│   ├── ctype.sinc          # Character classification lookup tables
│   ├── fast_math.sinc      # Fast bare-metal math & square root helpers
│   ├── hash.sinc           # FNV-1a non-cryptographic 64-bit hash engine
│   ├── sym_table.sinc      # Arena-backed linear-probing symbol table
│   └── vec.sinc            # Dynamic 64-bit word vector operations
│
└── sys/                    # Impure TEXT: Memory, Streams & OS Subsystems
    ├── arena.sinc          # Zero-fragmentation linear bump allocator
    ├── stream.sinc         # Linear byte stream reader & writer
    ├── sys.sinc            # Low-level OS syscall wrappers
    ├── os_linux.sinc       # Modular Linux hardware & telemetry control
    ├── driver_linux.sinc   # SINC Linux CLI executable driver
    ├── elf_packager.sinc       # Bare-metal .safe to ELF64 executable packager engine
    ├── packager_entry.sinc     # Standalone ELF executable packager CLI entrypoint
    ├── obj_packager.sinc       # Bare-metal .safe to ELF64 relocatable object (.o) packager engine
    ├── packager_obj_entry.sinc # Standalone ELF object packager CLI entrypoint
    └── bridge_linux.s          # System V AMD64 ABI assembly translation thunks
```

---

## Architecture & Conventions

### 1. SINC Spine ABI Calling Convention
Parameters are mapped to incoming physical registers in the following order:
1. `rcx` (Arg 0)
2. `rdx` (Arg 1)
3. `rbx` (Arg 2)
4. `rsi` (Arg 3)
5. `rdi` (Arg 4)
6. `r8`  (Arg 5)
7. `r9`  (Arg 6)
8. `r13` (Arg 7)
9. `r14` (Arg 8)
10. `r15` (Arg 9)
11. `rax` (Arg 10, return value register)
12. `r10` (Arg 11)
13. `r11` (Arg 12)
14. `r12` (Arg 13)

### 2. System V AMD64 ABI (Linux Bridge)
Under Linux, external C library and kernel syscalls map to `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`.
Register translation thunks reside under [`steel/sys/bridge_linux.s`](sys/bridge_linux.s).

---

## Standard Library Modules

### 1. Memory Arena (`steel/sys/arena.sinc`)
A zero-fragmentation, zero-garbage-collector Linear Bump Allocator managing memory strictly in 8-byte aligned boundaries using constant lenses (`ARENA_START`, `ARENA_NEXT`, `ARENA_LIMIT`).

### 2. Byte Streams (`steel/sys/stream.sinc`)
Contiguous byte stream reader and writer for high-speed binary parsing.

### 3. String Slices (`steel/data/slice.sinc`)
Zero-copy string representation using a 2-word fat pointer layout (`SLICE_PTR` and `SLICE_LEN`).

### 4. FNV-1a Hash Engine (`steel/data/hash.sinc`)
Deterministic 64-bit non-cryptographic hash grinder using wrapping multiplication.

### 5. Symbol Table (`steel/data/sym_table.sinc`)
Open-addressed, linear-probing Symbol Table with an 80% load-factor safety guard.

### 6. OS, Syscalls & Terminal Engine (`steel/sys/sys.sinc` & `steel/sys/os_linux.sinc`)
Low-level Linux kernel wrappers for file operations, process termination (`sys_exit!`), memory mapping (`sys_mmap!`), kernel `ioctl` (`sys_ioctl!`), and ptrace single-stepping. Includes a standalone, zero-dependency **Terminal Engine** (`steel_tty_raw!`, `steel_tty_nonblocking!`, `steel_tty_cooked!`, `steel_tty_winsize!`) enabling instant single-keypress capture, sub-microsecond non-blocking keyboard polling, and terminal window dimension queries directly without external C runtime.

### 7. ELF Packaging & C Object Emission (`steel/sys/elf_packager.sinc` & `steel/sys/obj_packager.sinc`)
Dual packaging subsystem transforming raw `.safe` machine code payloads into either:
* **Standalone Executables (`packager_bin`)**: Zero-dependency Linux ELF binaries with embedded kernel syscall thunks.
* **Relocatable Object Files (`packager_o`)**: Standard 64-bit ELF `ET_REL` (`.o`) files with `.text`, `.strtab`, and `.symtab` sections for direct static linking with C/C++ projects via GCC, Clang, or GNU ld.
