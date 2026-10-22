# SINC: Self-Hosted Compiler Core
*(Simple IR Native Compiler)*

The **SINC Compiler Core** (`sinc/`) is an experimental, 100% self-hosted compiler prototype designed to explore a simpler, high-throughput pipeline: single-pass parsing onto a flat tape and direct x86-64 machine code generation with zero external dependencies.

It is built for **SSS: Speed, Safety, Simplicity**.

```text
sinc/
├── data/                      # RODATA: Parser IR, Tape Operations & Lexer Tables
│   ├── lexer.sinc             # High-throughput character lookup tables & tokens
│   ├── parser_ir.sinc         # Flat 64-bit IR instruction definitions
│   └── tape_ops.sinc          # Canonical IR tape micro-operations & branch remapper
│
├── pure/                      # Pure TEXT: Optimizers & Code Generation (Zero '!', Zero OS)
│   ├── allocator.sinc         # 64-bit packed cumulative register allocator
│   ├── dce.sinc               # Local dead code elimination pass
│   ├── erls.sinc              # Diamond & triangle CMOV select fusion pass
│   ├── inline.sinc            # Single-block leaf function inliner
│   ├── loops.sinc             # Single-pass Loop Invariant Code Motion (LICM)
│   ├── parser_bindings.sinc   # Scope & variable binding resolver
│   ├── parser_pratt.sinc      # Zero-recursion Flat Pratt expression parser
│   ├── simplify.sinc          # Constant folding & range propagation pass
│   ├── unroll.sinc            # Bounded constant trip loop unroller
│   ├── vectorizer.sinc        # AVX-512 8-lane loop auto-vectorizer
│   └── x86_64.sinc            # Direct x86-64 machine code byte emitter
│
└── sys/                       # Impure TEXT: Parsing & Pipeline Execution
    ├── entry.sinc             # Self-hosted compiler pipeline & entrypoint
    └── parser.sinc            # Flat tape statement parser & driver
```

---

## Microarchitectural Pillars

### 1. Flat Tape IR & Canonical Micro-Operations (`data/tape_ops.sinc`)
Traditional compilers construct massive graph-based Abstract Syntax Trees (AST) and Control Flow Graphs (CFG) connected by pointer-chasing nodes in heap memory. This thrashes CPU caches and causes massive memory fragmentation.

SINC completely eradicates ASTs and CFGs:
* **The Flat IR Tape**: The entire program is parsed directly onto a flat, contiguous 64-bit word tape in a pre-allocated linear arena.
* **Canonical Micro-Operations**: `data/tape_ops.sinc` provides zero-overhead primitives (`tape_set_4!`, `tape_copy_4!`, `tape_clone!`, `tape_remap_branches!`, `tape_commit!`) allowing passes to stream and transform code sequentially.

### 2. The Optimization Engine (`pure/`)
All middle-end passes are mathematically pure and operate directly on flat tape buffers:
* **`inline.sinc`**: Expands leaf calls directly into caller tapes across program call sites.
* **`unroll.sinc`**: Unrolls constant loops ($\le 8$ trips, $\le 16$ insts) into linear code.
* **`simplify.sinc`**: Folds arithmetic constants, evaluates algebraic identities, and propagates range bounds.
* **`loops.sinc` & `vectorizer.sinc`**: Single-Pass LICM hoisting loop-invariant arithmetic to pre-headers and triggering 8-lane 512-bit EVEX vector emission for eligible loops.
* **`erls.sinc`**: Flattens branches into flag-free `cmov` selects.
* **`dce.sinc`**: Backward linear liveness sweep pruning unread instruction slots.

### 3. 64-Bit Packed Cumulative Register Allocator (`pure/allocator.sinc`)
Instead of complex graph-coloring algorithms or disjoint interval trees, SINC uses an $\mathcal{O}(1)$ **Packed Cumulative Counter Allocator**:
* Encodes cross-call volatility detection directly into a single 64-bit word:
  $$\mathbf{Packed\;State} = \mathbf{Register\;Index} \;|\; (\mathbf{Call\;Count} \ll 32)$$
* Volatility and spill decisions require zero sorting, zero bitsets, and zero dynamic heap vectors.

### 4. Direct x86-64 Machine Code Generation (`pure/x86_64.sinc`)
SINC does not emit `.s` assembly files or rely on GNU `as`/`ld`. The backend emits raw, executable x86-64 opcode bytes directly into an output `.safe` binary payload featuring 3-term SIB LEA hardware fusion and flag-free arithmetic.

This payload can be packaged immediately via:
* **`bin/packager_bin`**: Zero-dependency standalone Linux ELF executable.

---

## Compilation Performance

| Metric | Measurement (Intel Core i5-11400F) |
| :--- | :--- |
| **Self-Hosting Bootstrap Time** | **~4–5.5 ms wall-clock / ~3.4 ms CPU user time** (full compiler self-compilation) |
| **Compiler Binary Size** | **~71 KB (Standalone ELF)** |
| **Compile Throughput** | **~1,000,000 LOC/s** (CPU user time throughput) / **~780k LOC/s** (wall-clock) |
| **External Dependencies** | **0 (Zero libc, zero Python, zero GNU as/ld)** |
| **Fixed-Point Self-Hosting** | **100% Deterministic (`stage2 == stage3` bitwise identical)** |


