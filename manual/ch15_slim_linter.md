# Chapter 15: S.L.I.M. — SINC Linter & Inspection Module

> **Project Status: Early Pre-State Prototype**  
> S.L.I.M. (`./bin/slim.elf`) is an experimental architectural supervisor and linter prototype. Its current rule categorization and detection heuristics are basic line-level and tape-level pattern scanners. It does not construct complex semantic graphs or full AST dataflow trees, so false positives can occur. It represents an initial exploration into automated architectural hygiene to keep SINC codebases slim and bloat-free.

---

## 1. Architectural Concept

Modern compilers typically embed hundreds of warning passes directly into the compiler binary, slowing down compilation for every build.

In SINC, we separate concerns:
1. **Core Compiler (`sinc/`)**: Stays AST-free, fast (~1,000,000 lines/sec), and strictly focused on generating direct x86-64 machine code.
2. **SLIM Linter (`slim/`)**: An independent external tool that scans source code and IR tapes to enforce clean architecture, dead code elimination, and test validation.

```text
slim/
├── data/
│   └── diag.sinc           # Diagnostic tag constants & poke emitters
├── pure/
│   ├── lint.sinc           # Core static linter heuristics
│   ├── lint_bandaid.sinc   # Temporary patch / quick-fix detector
│   ├── lint_fossil.sinc    # Deprecated pattern detector
│   ├── lint_ghost.sinc     # Unreachable branch scanner
│   ├── lint_runner.sinc    # Linter pipeline dispatcher
│   ├── lint_splinter.sinc  # Expression complexity scanner
│   ├── mutator.sinc        # IR tape mutation scanner
│   └── gate.sinc           # Benchmark & size gate evaluator
└── sys/
    └── entry.sinc          # CLI command dispatcher
```

---

## 2. Current Diagnostic Tags & Detection Realities

SLIM defines five primary diagnostic tags. Understanding how they actually work under the hood helps developers interpret their output:

| Tag | Intended Goal | Actual Implementation Reality |
| :--- | :--- | :--- |
| `[TAG: LAZY]` | Flag overly dense, unreadable statements | **Operator Counter**: Flags any single statement containing $> 4$ operators on a line, encouraging intermediate variable decomposition. |
| `[TAG: DEAD WEIGHT]` | Prune unused functions to save context | **Identifier Scanner**: Flags declared functions that are never called within the scanned unit. |
| `[TAG: UNNECESSARY]` | Detect dead stores | **Variable Assignment Scanner**: Flags variables assigned but never subsequently referenced (note: can flag manual loop induction termination idioms). |
| `[TAG: WEAK TEST]` | Detect superficial green tests | **IR Tape Mutator**: Swaps arithmetic opcodes and checks if the test suite still exits 0. |
| `[TAG: UNVERIFIED]` | Ensure test coverage on critical paths | **Trace Gate**: Checks for zero execution trace on targeted functions. |

---

## 3. Honest Limitations & Future Evolution

* **Heuristic Scanners, Not Flow Graphs**:
  SLIM does not build a full interprocedural Control Flow Graph (CFG) or Static Single Assignment (SSA) form. Because it relies on flat token and tape patterns, complex multi-line idioms may trigger false positives.
* **Separation from Compiler Soundness**:
  SLIM is strictly a developer-advisory tool. Code that triggers SLIM warnings can still compile and run with 100% correctness under the core SINC compiler.

SLIM provides the foundation for an automated architectural watchdog tailored for AI coding workflows, designed to evolve over time without burdening the core compiler's speed.

---

## 4. Building with STAFF

SLIM is managed natively via its manifest [`slim/build.staff`](../slim/build.staff):

```bash
# 1. Compile SLIM via STAFF manifest
./bin/staff slim/build.staff scratch/slim.safe

# 2. Package into a standalone Linux ELF binary
./bin/packager_bin scratch/slim.safe bin/slim.elf
chmod +x bin/slim.elf

# 3. Run SLIM against a source unit
./bin/slim.elf check my_program.sinc
```


