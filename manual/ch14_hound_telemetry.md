# Chapter 14: HOUND — Runtime Telemetry & Logic Probing

> **Project Status: Visual Prototype & Concept Demonstration**  
> HOUND is currently an experimental UI prototype and conceptual exploration of lightweight terminal telemetry. It demonstrates how debugging can look on SINC's flat tape architecture without loading heavy DWARF symbol tables or bloated debugger runtimes. In its current early state, the interactive dashboard operates with demonstration state and mock register feeds; full live `ptrace` process hooking and execution replay remain active development targets.

---

## 1. The HOUND Philosophy

Traditional debuggers (GDB, LLDB) are designed around complex DWARF symbol tables, deeply nested stackframes, and heap-allocated string formatting.

SINC programs run on a **flat, contiguous tape of 64-bit hardware words**.

**HOUND** (**H**ierarchical **O**ptimized **U**niversal **N**umeric **D**ebugger) was designed to explore a different debugging paradigm: inspecting machine execution directly at the register and memory word level in an instant, zero-dependency terminal dashboard.

---

## 2. Hardware Lexicon

HOUND maps debugging concepts directly to machine concepts:

| Traditional Term | SINC Concept | Hardware Meaning |
| :--- | :--- | :--- |
| **Breakpoint** | **Signal Trap** | A physical halt injected into the IR tape to trap CPU execution. |
| **Stack Trace** | **Call Lineage** | The exact sequence of hardware call offsets leading to an instruction. |
| **Null Pointer Exception** | **Zero-Base Fracture** | Writing to an unhandled 0 allocation return. |
| **Segmentation Fault** | **Arena Breach** | An offset calculation exceeding the physical bump-allocator limit. |
| **Step Into / Over** | **Advance Clock / Skip Call** | Advancing the instruction pointer forward on the flat tape. |
| **Variable Watch** | **Register Tap** | A live monitor attached to a virtual register in cache. |

---

## 3. The 64-Bit Death Vector (Zero String Panics)

Traditional languages allocate heap memory to format verbose English panic traces upon crashing. If a program crashes because memory is exhausted, allocating more memory to format an error message is fundamentally flawed.

In SINC, fatal runtime errors are designed to yield a single packed **64-Bit Death Vector**:

```
+------------------------------------+------------------+------------------+
|      Instruction Offset (48 bits)  |  Fault ID (8b)   |  Domain ID (8b)  |
|         Bits 16 .. 63              |   Bits 8 .. 15   |   Bits 0 .. 7    |
+------------------------------------+------------------+------------------+
```

### The 3 Physical Domains:
1. **Domain 1: Physical Memory / MMU (`0x01`)**
   * `0x01` $\to$ **Zero-Base Fracture**: Writing to an unhandled 0 allocation return.
   * `0x02` $\to$ **Arena Breach**: Writing past pre-allocated bump limit.
2. **Domain 2: ALU / Word Packing (`0x02`)**
   * `0x01` $\to$ **Word Fracture**: Overlapping bit shifts or bitmask collision.
   * `0x02` $\to$ **Lens Misalignment**: Misaligned constant struct offset.
3. **Domain 3: OS Gateway (`0x03`)**
   * `0x01` $\to$ **Gateway Rejection**: Linux kernel returned a negative errno.

HOUND includes a pure decoder (`hound/pure/death_decoder.sinc`) to unpack this integer instantly with zero heap allocations.

---

## 4. The 4-Panel Telemetry HUD

Running `./bin/hound.elf` launches an interactive terminal HUD rendered through an ANSI VT100 flat framebuffer:

```text
=== [ HOUND LOGIC PROBE ] ===
[A] [##########..........] 32MB / 64MB
[B] 0x5720364EF2978548 | H...N6 W
[C] SYS: 01 (sys_write) | RET: 0x00000000
[D] RIP: 0x00000000004008E0 CLK: 01
```

* **Panel A (Arena Oscilloscope)**: Visual progress bar tracking linear memory bump tides.
* **Panel B (Word Slicer)**: Decomposes quadwords into 8 hex bytes and printable ASCII characters.
* **Panel C (OS Gateway)**: Translates Linux kernel syscall return values and error numbers.
* **Panel D (Tape Sequencer)**: Displays the instruction pointer (`RIP`) and advances cycle clock counts.

---

## 5. Current Implementation vs. Roadmap

| Feature | Current State | Notes |
| :--- | :---: | :--- |
| **ANSI VT100 Framebuffer** | **Working** | Direct single-syscall flush via `sys_write!`. |
| **Raw Mode TTY Key Catching** | **Working** | Non-blocking single keypress capture without Enter. |
| **Word Slicer Algorithm** | **Working** | Pure hex and ASCII byte unpacking. |
| **Death Vector Unpacker** | **Working** | Unpacks 64-bit integer into domain, fault, and RIP. |
| **Live Ptrace Attachment** | *Prototype / Mock* | Currently runs with demonstration telemetry state. |
| **Time-Travel Execution Replay** | *Conceptual* | Design exploration for rewinding pure function state. |

HOUND serves as a prototype proving that rich terminal diagnostics can be built completely bare-metal without relying on bloated external debugging frameworks.

---

## 6. Building with STAFF

HOUND is fully integrated into the SINC Sovereign Suite with its own manifest [`hound/build.staff`](../hound/build.staff):

```bash
# 1. Compile HOUND via STAFF manifest
./bin/staff hound/build.staff scratch/hound.safe

# 2. Package into a standalone Linux ELF binary
./bin/packager_bin scratch/hound.safe bin/hound.elf
chmod +x bin/hound.elf

# 3. Launch HOUND HUD
./bin/hound.elf
```


