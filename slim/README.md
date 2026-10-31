# S.L.I.M. — SINC Linter & Inspection Module
*(Architectural Hygiene & Mutation Linter for SINC)*

> **Status: Experimental Architectural Linter Preview**  
> S.L.I.M. (**S**INC **L**inter & **I**nspection **M**odule) is an experimental companion tool and linter prototype designed for SINC's flat tape architecture. Its current heuristics are pattern-based scans for architectural hygiene and mutation validation; it is an opt-in preview to keep codebases lean and bloat-free, not an authoritative verifier or safety tool.

---

## Architecture & Layout

SLIM is organized into a clean, two-pass flat tape pipeline:

```text
slim/
├── README.md               # SLIM user & CLI guide
├── build.staff             # Self-host manifest
├── data/                   # OS-Neutral RODATA & Tag Definitions
│   └── diag.sinc           # Diagnostic tag constants, string-free poke helpers & error emitters
│
├── pure/                   # Pure Algorithms (Two-Pass Flat Tape Supervisor)
│   ├── tape_scanner.sinc   # Pass 1: Global symbol & extern syscall table indexer
│   ├── tape_auditor.sinc   # Pass 2: Unified statement, wrapper, and scope auditor
│   ├── lint_runner.sinc    # Master two-pass pipeline coordinator
│   ├── mutator.sinc        # Bytecode mutation engine & test-divergence evaluator
│   └── gate.sinc           # Dynamic trace & benchmark ceiling evaluator (UNVERIFIED, REGRESSION)
│
└── sys/                    # CLI Dispatcher & Tape Loader
    └── entry.sinc          # Whole-program tape loader (slim_load_tape!) & CLI entrypoint
```

---

## The Constraint Tag System

SLIM enforces distinct diagnostic tags tailored specifically for automated agents and developers:

| Tag | Category | Trigger Condition | Required AI Resolution |
| :--- | :--- | :--- | :--- |
| `[TAG: LAZY]` | Static | Single statement containing $> 4$ operators | Unroll complex one-liners into readable multi-step intermediate variables. |
| `[TAG: DEAD WEIGHT]` | Static | Declared function is never referenced or called | Prune unused functions to save LLM token context and eliminate legacy baggage. |
| `[TAG: UNNECESSARY]` | Static | Local variable assigned but never read | Delete dead store or return the computed value. |
| `[TAG: WRAPPER]` | Static | Trivial 1:1 forwarding wrapper around existing function | Informational: Informs developer of indirection layer so target can be called directly. |
| `[TAG: FOSSIL]` | Static | Self-assignment (`x = x;`) | Remove redundant no-op assignment. |
| `[TAG: RAWDATA]` | Static | Bare literal in comparison (`== 65535`) | Define and use a symbolic named constant. |
| `[TAG: WEAK TEST]` | Dynamic | Mutated bytecode survives test suite execution | Add explicit behavioral assertions verifying inverted runtime semantics. |
| `[TAG: UNVERIFIED]` | Dynamic | Function or code path has 0 execution trace | Write an automated test covering the logic path. |
| `[TAG: REGRESSION]` | Dynamic | Execution cycles exceed baseline ceiling | Optimize loop or algorithmic complexity to satisfy performance budget. |

---

## CLI Command Reference

### 1. Static Architectural Constraints
```bash
./bin/slim.elf check <source.sinc>
```
Scans the target source file for statement complexity, dead functions, and unread variables.
- **Exit 0**: `[SLIM: PASS] All static architectural constraints satisfied.`
- **Exit 1**: Emits structured tags to `stderr` with line numbers and identifiers.

### 2. Bytecode Mutation Engine
```bash
# Generate mutated bytecode (.safe)
./bin/slim.elf mutate <target.safe> <mutant.safe>

# Package and execute mutated binary
./bin/packager_bin mutant.safe mutant.elf
chmod +x mutant.elf
./mutant.elf; TEST_CODE=$?

# Evaluate whether test suite detected mutation
./bin/slim.elf eval-mutant $TEST_CODE
```
- If the test suite passed (`TEST_CODE == 0`), the mutant survived: SLIM emits `[TAG: WEAK TEST]` and halts with exit code 1.
- If the test caught the mutation (`TEST_CODE != 0`), SLIM outputs `[SLIM: PASS] Mutant killed by test assertion.` and exits with 0.

### 3. Dynamic Trace & Performance Gates
```bash
# Verify execution trace coverage
./bin/slim.elf verify-trace <execution_count>

# Verify benchmark cycle limits vs baseline ceiling
./bin/slim.elf verify-bench <current_cycles> <baseline_ceiling>
```

---

## Building SLIM

SLIM is compiled and packaged using STAFF:
```bash
./bin/staff slim/build.staff scratch/slim.safe
./bin/packager_bin scratch/slim.safe bin/slim.elf
chmod +x bin/slim.elf
```
This produces `./bin/slim.elf`.

