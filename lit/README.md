# L.I.T. — Live-on-Time Runtime & Resident Slot Engine

> **Status: Experimental Linux Prototype (Designed for SOLOS/SHARK)**  
> L.I.T. (**L**ive-**i**n-**T**ime) is a runtime, on-demand compiler supervisor, and resident memory slot engine. It serves as the Linux host prototype and architectural blueprint for the upcoming Ring-0 operating system (**SOLOS**) and hypervisor kernel (**SHARK**).

---

## 1. Architectural Philosophy

LIT eliminates the traditional tradeoffs between Just-In-Time (JIT) compilation and Ahead-Of-Time (AOT) binaries:
* **Deterministic $W \oplus X$**: Memory is mapped `PROT_READ | PROT_WRITE`, populated with reverse thunks and bytecode, and sealed to `PROT_READ | PROT_EXEC` before execution. No page is ever simultaneously writable and executable.
* **On-Demand Sovereign Compilation**: Takes `.sinc` source files or `.staff` project manifests, resolves dependencies, auto-discovers triad directories via Linux `sys_getdents64`, computes bitwise deterministic FNV-1a cache keys, and transparently compiles to native `.safe` modules when stale.
* **Resident Slot Table & Atomic Hot-Swap**: Maintains a flat 32-byte slot table in resident memory. Modules are loaded into isolated slots, invoked repeatedly across the Spine ABI, and hot-swapped live via a single atomic 64-bit pointer swap.
* **Zero Host Shell / Zero C Library**: LIT is implemented entirely in self-hosted SINC and S.T.E.E.L., relying solely on direct Linux syscall reverse thunks.

---

## 2. Directory & Triad Layout

```text
lit/
├── README.md               # LIT user & architecture guide
├── build.staff             # Self-host manifest
├── data/
│   └── lit_defs.sinc       # Geometry, lenses, slot constants (SLOT_ENTRY, SLOT_BASE)
├── pure/
│   ├── safe_header.sinc    # Pure SAFE binary header verification
│   ├── dispatch.sinc       # Target dispatch detection (.safe, .sinc, .staff)
│   ├── cache.sinc          # Cache path formatting
│   ├── slots.sinc          # Pure 32-byte slot table indexing & lookup
│   └── staff_manifest.sinc # Pure manifest parser & artifact name extraction
└── sys/
    ├── runner.sinc         # Unified W^X memory mapper (lit_map_safe!) & direct execution
    ├── slot_runner.sinc    # Resident slot lifecycle & live atomic hot-swap
    ├── triad_scanner.sinc  # Triad auto-discovery & commutative XOR directory hashing
    └── entry.sinc          # CLI entrypoint driver & on-demand compilation orchestrator
```

---

## 3. Runtime Contracts & Constraints

### 3.1 Working Directory & Cache Path
* **Repo-Root CWD**: LIT and STAFF resolve artifact triad directories (`<artifact_name>/{data,pure,sys}`) relative to the process working directory (`CWD`).
* **Cache Root**: Cached artifacts are placed in `scratch/lit_cache/<fnv1a_hash>.safe`.
* **Compiler-Identity Seeding**: The cache seed incorporates the binary hashes of `bin/sinc.safe` and `bin/staff.safe`. Upgrading compiler binaries automatically invalidates all stale caches.

### 3.2 The Spine ABI Contract
Resident slot entrypoints communicate across standard SINC Spine calling conventions:
* `%rcx`: Argument 0
* `%rdx`: Argument 1
* `%rbx`: Argument 2
* `%rax`: Return code / status
* `%r12`: Preserved host `argv` pointer

### 3.3 Hot-Swap Scope: Single-Threaded Cooperative Quiescence
* Live slot hot-swapping stages fresh `PROT_RX` pages in parallel, reads the new module, and commits the slot update via a single atomic 64-bit write to `slot@[SLOT_ENTRY]`.
* In this Linux prototype (and single-core Ring-0 SOLOS), swapping occurs between calls at cooperative quiescent points.
* The previous mapping is unmapped immediately via `sys_munmap!`. Linux-specific pthread/RCU epoch-based deferred reclamation is intentionally omitted to avoid throwaway complexity before SOLOS (Law 11).

---

## 4. Building LIT

LIT is compiled and packaged using STAFF and the SINC packager:

```bash
./bin/staff lit/build.staff scratch/build/lit.safe
./bin/packager_bin scratch/build/lit.safe bin/lit.elf
chmod +x bin/lit.elf
```

---

## 5. Usage

### 5.1 Direct Native Execution (`.safe`)
Executes an ahead-of-time compiled SINC binary with deterministic $W \oplus X$:
```bash
./bin/lit.elf app.safe
```

### 5.2 On-Demand Single File Compilation (`.sinc`)
Hashes source content against compiler seed, compiles on cache miss, and executes:
```bash
./bin/lit.elf script.sinc
```

### 5.3 On-Demand Manifest Project (`.staff`)
Auto-discovers project triad folders (`data/`, `pure/`, `sys/`) and external `deps [...]`, checks cache validity, builds via STAFF on demand, and executes:
```bash
./bin/lit.elf build.staff
```

### 5.4 Verification Suite
Run the full 20-gate deterministic verification suite:
```bash
bash tests/lit/test_lit.sh
```
