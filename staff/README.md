# S.T.A.F.F. — Sorted Topological Artifact File Format
*(Bare-Metal Project Orchestrator for SINC)*

> **Status: Experimental Tooling**  
> S.T.A.F.F. (**S**orted **T**opological **A**rtifact **F**ile **F**ormat) is a lightweight project orchestrator written in SINC. It replaces ad-hoc shell scripts by reading a `build.staff` manifest, discovering your project files across the Universal Triad, and compiling them directly into an executable `.safe` binary payload in memory.

---

## 1. Core Architecture

STAFF compiles projects following SINC's **Universal Triad**:
$$\text{DATA } (\texttt{data/*}) \longrightarrow \text{PURE } (\texttt{pure/*}) \longrightarrow \text{SYS } (\texttt{sys/*})$$

It parses `.staff` manifests in pure SINC without pulling in external tools, resolves dependencies from `deps [...]`, reads directory trays via Linux `sys_getdents64`, sinks `entry.sinc` to the end, and directly calls `compile_core!` in memory.

---

## 2. Directory Layout

```text
staff/
├── README.md         # Documentation
├── build.staff       # Self-host manifest
└── sys/
    └── entry.sinc    # Master manifest orchestrator & entrypoint
```

---

## 3. CLI Usage

STAFF takes the path to your project manifest and writes out a `.safe` machine code payload:

```text
Usage: ./bin/staff <manifest.staff> [output.safe]
```

### Compiling a Project

```bash
# 1. Compile project manifest to .safe machine code payload
./bin/staff my_project/build.staff my_project.safe

# 2. Package into a standalone Linux ELF binary
./bin/packager_bin my_project.safe ./my_project
chmod +x ./my_project

# 3. Run it
./my_project
```

---

## 4. Manifest Format (`build.staff`)

A standard manifest declares the artifact, dependencies, and optional host driver:

```text
artifact my_service [
]

deps [
    steel/sys/sys.sinc;
    steel/sys/arena.sinc;
]

driver [
    steel/sys/driver_linux.sinc;
]
```

STAFF automatically bundles:
1. Files declared in `deps [...]`
2. All `.sinc` files found in `data/`
3. All `.sinc` files found in `pure/`
4. All `.sinc` files found in `sys/` (excluding `entry.sinc`)
5. `<root>/sys/entry.sinc`
6. Optional `driver` file

---

## 5. Self-Hosting

Because STAFF is written entirely in SINC, it compiles its own manifest:

```bash
# 1. Compile Stage 2 STAFF binary
./bin/staff staff/build.staff scratch/staff_s2.safe

# 2. Package into executable
./bin/packager_bin scratch/staff_s2.safe bin/staff
chmod +x bin/staff

# 3. Run automated test suite
./tests/staff/test_staff.sh
```

Fixed point verification (`stage2 == stage3`) completes in ~4–5.5 ms wall-clock / ~3.4 ms CPU user time.

