# HOUND: Hierarchical Optimized Universal Numeric Debugger
*(A Lightweight Runtime Telemetry & Register Monitor for SINC)*

> **Status: Visual Prototype & Concept Demonstration**  
> HOUND is an experimental terminal telemetry prototype exploring zero-dependency register inspection on SINC's flat tape architecture. The interactive dashboard currently operates with demonstration state and mock register feeds; live process attachment and execution replay are active development targets.

HOUND (**Hierarchical Optimized Universal Numeric Debugger**) is an experimental debugging tool and telemetry probe built for SINC's flat tape runtime architecture. It is a prototype concept—provided with no guarantees—designed to explore a simpler way to inspect program state, CPU registers, and execution steps directly in a lightweight terminal interface without heavy debug symbols.

---

## Architecture & Layout

HOUND is organized into three clean layers:

```text
hound/
├── data/                   # RODATA (Fault Matrix, Telemetry Masks, Layouts)
│   ├── fault_matrix.sinc   # 64-Bit Death Vector bitfields & Domain IDs
│   ├── hud_layout.sinc     # 4-Panel telemetry dimensions & word slicer modes
│   ├── errno_table.sinc    # Generic error code translation table
│   └── regs_layout.sinc    # Virtual & hardware register indices
│
├── pure/                   # Pure TEXT (Zero '!', Zero OS calls)
│   ├── death_decoder.sinc  # Pure mathematical 64-bit vector unpacker
│   ├── word_slicer.sinc    # Hex/ASCII quadword slicer (u8, u16, u32, u64)
│   └── rewind_tape.sinc    # Pure state-delta tracker for Clock Rewind
│
└── sys/                    # Impure TEXT: Telemetry HUD & 60-FPS Loop
    ├── hud_render.sinc     # ANSI VT100 direct-poke flat framebuffer painter
    └── entry.sinc          # 60-FPS loop (consumes steel/sys/ directly)
```

---

## SINC Hardware Terminology

HOUND maps debugging concepts directly to physical hardware state:

| Traditional Term | SINC Concept | Meaning |
| :--- | :--- | :--- |
| **Breakpoint** | **Signal Trap** | Halt injected into the IR tape to trap CPU execution. |
| **Stack Trace** | **Call Lineage** | The sequence of hardware call offsets leading to the instruction. |
| **Null Pointer Exception** | **Zero-Base Fracture** | Memory operation on unhandled zero allocation return. |
| **Segmentation Fault** | **Arena Breach** | Offset calculation exceeded pre-allocated memory boundary. |
| **Step Into / Step Over** | **Advance Clock / Skip Call** | Advancing the instruction pointer forward on the flat tape. |
| **Step Backward** | **Rewind Clock** | Stepping backward across side-effect-free pure instructions. |
| **Variable Watch** | **Register Tap** | Live monitor attached to a virtual register slot. |

---

## The 64-Bit Death Vector

Crashing programs allocate zero memory for error strings. When a fatal condition occurs, the runtime yields a single packed 64-bit integer:

$$\mathbf{[Instruction\;Offset: 48b]} \;|\; \mathbf{[Fault\;ID: 8b]} \;|\; \mathbf{[Domain\;ID: 8b]}$$

### The 3 Machine Domains:
1. **Domain 1: Physical Memory / MMU (`0x01`)**
   * `0x01` -> **Zero-Base Fracture** (Writing to unhandled 0 allocation return).
   * `0x02` -> **Arena Breach** (Writing past pre-allocated bump limit).
2. **Domain 2: ALU / Word Packing (`0x02`)**
   * `0x01` -> **Word Fracture** (Overlapping bit shifts / mask collision).
   * `0x02` -> **Lens Misalignment** (Misaligned constant offset).
   * `0x03` -> **Pure Logic Trap** (Math comparator failure).
3. **Domain 3: OS / External Gateway (`0x03`)**
   * `0x01` -> **Gateway Rejection** (Linux returned negative errno).

---

## The 4-Panel Telemetry HUD

```text
=== [ HOUND LOGIC PROBE ] ===
[A] [##########..........]
[B] 0x5720364EF2978548 | H...N6 W
[C] SYS: 01 RET: 0x5720364EF2978548
[D] RIP: 0x00000000004008E0 CLK: 01
```

* **Panel A (Memory Gauge)**: Displays the live memory utilization across allocated arenas.
* **Panel B (Word Slicer)**: Slices 64-bit hardware quadwords into hex grids and printable ASCII characters.
* **Panel C (OS Gateway)**: Intercepts Linux syscall transitions, translating syscall IDs and return codes.
* **Panel D (Tape Sequencer)**: Steps through instruction offsets (`RIP`) and CPU clock cycle counts.

---

## Build & Binary Footprint

* **Compilation**: Built via STAFF manifest:
  ```bash
  ./bin/staff hound/build.staff scratch/hound.safe
  ./bin/packager_bin scratch/hound.safe bin/hound.elf
  chmod +x bin/hound.elf
  ```
* **Compilation Speed**: **~4 ms**
* **Binary Size**: **~8.4 KB** (`hound.elf`).
* **Frame Flush Latency**: Microsecond single-syscall flush (`sys_write!(1, hud_buf, len)`).
* **Dependencies**: **0 external libraries** (No ncurses, no libc, no GUI frameworks).

