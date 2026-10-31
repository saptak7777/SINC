# Appendix E: Performance Analysis & Benchmark Scorecard

This appendix documents the performance characteristics of the SINC compiler prototype compared against GCC `-O3`. It provides the empirical benchmark scorecard, analyzes architectural strengths, outlines existing optimization weaknesses, and defines the intentional design boundaries that SINC will not compromise.

---

## 1. Methodology & Test Setup

All measurements are conducted via an automated 1-to-1 benchmark harness (`tools/bench_24_gcc.py`):
* **C Baseline**: GCC 11+ invoked with `-O3 -march=native`.
* **SINC**: Direct machine code emitted by `sinc.elf` and packaged via `packager_bin`.
* **Execution**: Single-core pinning via `taskset`, warm-up passes, and median latency calculated across consecutive runs.

---

## 2. Empirical Benchmark Scorecard

> **Reference Test Environment**:
> - **Processor**: Intel Core i5-11400F @ 2.60 GHz (Rocket Lake, 6 cores / 12 threads)
> - **OS & Kernel**: Linux 6.x x86-64
> - **Affinity**: Single-core pinning via `taskset -c 2`
> - **Compiler Baseline**: GCC 11+ invoked with `-O3 -march=native`
> - **Measurement**: Automated harness (`python3 tools/bench_24_gcc.py`) with median of consecutive runs
> - **Note on Noise**: The 1.18x geomean is a reference baseline snapshot measured under these isolated conditions. Live harness measurements on desktop systems typically fluctuate between 1.16x and 1.23x due to thermal throttling, frequency scaling governors, and background OS scheduling jitter.

The following table reflects the unified 24-workload suite comparing fresh SINC (`sinc.elf`) against clean GCC (`-O3 -march=native`), verified on isolated CPU Core 2 with bitwise exit code equality (100% semantic agreement):

| Benchmark Workload | Exit Code | SINC Latency | GCC -O3 Clean | Ratio (SINC / GCC) | Execution Outcome |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `linear_vector_triad` | 72 | 7.26 ms | 30.85 ms | 0.235x | SINC is 4.25x faster (AVX-512 ZMM) |
| `soa_speed` | 45 | 11.65 ms | 39.01 ms | 0.299x | SINC is 3.35x faster (AVX-512 ZMM) |
| `gemm_dot` | 0 | 45.14 ms | 74.90 ms | 0.603x | SINC is 1.66x faster |
| `multi_loop_pipeline` | 0 | 3.68 ms | 5.58 ms | 0.659x | SINC is 1.52x faster (AVX-512 ZMM) |
| `scalar_runtime` | 193 | 1.65 ms | 2.49 ms | 0.663x | SINC is 1.51x faster |
| `scalar_reference` | 6 | 0.38 ms | 0.56 ms | 0.679x | SINC is 1.47x faster |
| `branch_speed` | 0 | 38.20 ms | 53.44 ms | 0.715x | SINC is 1.40x faster |
| `pure_licm_hoist` | 131 | 9.70 ms | 12.21 ms | 0.794x | SINC is 1.26x faster |
| `poly_speed` | 128 | 17.66 ms | 20.99 ms | 0.841x | SINC is 1.19x faster (512-bit ZMM) |
| `shift_extract_speed`| 84 | 117.34 ms | 119.01 ms | 0.986x | Tied (~1.00x) |
| `bit_extract_speed` | 23 | 117.66 ms | 118.04 ms | 0.997x | Tied (~1.00x) |
| `branchless_filter` | 7 | 130.69 ms | 126.93 ms | 1.030x | Tied (~1.00x) |
| `refinement_bounds_elim` | 192 | 21.13 ms | 19.74 ms | 1.070x | GCC is 1.07x faster |
| `math_speed` | 128 | 27.45 ms | 24.69 ms | 1.112x | GCC is 1.11x faster |
| `hash_table_probe` | 208 | 15.32 ms | 11.55 ms | 1.326x | GCC is 1.33x faster |
| `jacobi_stencil` | 177 | 74.05 ms | 50.01 ms | 1.481x | GCC is 1.48x faster |
| `pure_calls_speed` | 217 | 32.76 ms | 20.27 ms | 1.616x | GCC is 1.62x faster (AVX-512 SIMD) |
| `tree_traverse` | 248 | 124.22 ms | 73.87 ms | 1.682x | GCC is 1.68x faster |
| `matrix_transpose_tiled` | 134 | 7.44 ms | 2.71 ms | 2.745x | GCC is 2.75x faster |
| `bench_unroll_fir8` | 0 | 1.71 ms | 0.57 ms | 2.990x | GCC is 2.99x faster |
| `bench_unroll_nested` | 0 | 1.61 ms | 0.53 ms | 3.038x | GCC is 3.04x faster |
| `deep_call_stack` | 180 | 12.37 ms | 3.72 ms | 3.325x | GCC is 3.33x faster |
| `magic_bitboard` | 127 | 42.89 ms | 11.13 ms | 3.854x | GCC is 3.85x faster |
| `dram_stream_triad` | 121 | 12.03 ms | 2.85 ms | 4.221x | GCC is 4.22x faster (512-bit ZMM) |

These figures reflect clean C implementations with all artificial `volatile` handicaps removed. Across the 24 workloads, SINC wins in 9 workloads, ties in 3 workloads, and GCC wins in 12 workloads (Suite geometric mean ratio: 1.18x).

---

## 3. Where SINC Wins (Architectural Strengths)

SINC outperforms GCC `-O3` in workloads centered on arithmetic density, tight unrolling, streaming vector pipelines, and predictable branch flow:

1. **Continuous 512-Bit Streaming Vector Pipelines (`linear_vector_triad`, `soa_speed`, & `multi_loop_pipeline`)**:
   SINC's vectorizer converts linear array loops into 8-lane 512-bit EVEX vector memory operations (`vmovdqu64`, `vpaddq`, `vpmullq`, `vpandq`), completing `linear_vector_triad` in **7.26 ms** vs GCC's **30.85 ms** (**4.25x faster than GCC -O3**), `soa_speed` in **11.65 ms** vs GCC's **39.01 ms** (**3.35x faster than GCC -O3**), and `multi_loop_pipeline` in **3.68 ms** vs GCC's **5.58 ms** (**1.52x faster than GCC -O3**).
2. **Scalar Reference & Spill-Free Arithmetic (`scalar_reference`, `scalar_runtime`)**:
   Eliminating legacy 2-address move cruft and redundant scratch register spills beats GCC by **1.47x** (0.38 ms vs 0.56 ms) on references, and **1.51x** (1.65 ms vs 2.49 ms) on runtime scalar iteration.
3. **Predictable Branch Layout (`branch_speed`)**:
   GCC frequently forces branchless instructions (`cmov`, `setcc`) even when branches are highly predictable. On modern x86 hardware, the CPU branch target buffer (BTB) predicts regular patterns with near 100% accuracy. SINC emits direct conditional jumps, outperforming GCC by **1.40x** (38.20 ms vs 53.44 ms).
4. **Dense Matrix & Dot Products (`gemm_dot`)**:
   SINC maps compound arithmetic directly to general-purpose registers without emitting redundant move instructions, outperforming GCC by **1.66x** (45.14 ms vs 74.90 ms).
5. **Loop-Invariant Code Motion (`pure_licm_hoist`)**:
   SINC's pure tape-level LICM pass hoists invariant calculations outside hot loop bodies with zero spill overhead, completing in **9.70 ms** compared to GCC's **12.21 ms** (**1.26x faster than GCC -O3**).
6. **Polynomial Evaluation with 512-Bit Vectors (`poly_speed`)**:
   SINC generates 8-lane 512-bit AVX-512 vector instructions across `%zmm0`–`%zmm31`, completing in **17.66 ms** compared to GCC's **20.99 ms** (**1.19x faster than GCC -O3**).
7. **Compilation Throughput**:
   SINC compiles at over 1,000,000 lines per second, building entire binaries in 4 to 5 milliseconds. GCC takes hundreds of milliseconds to compile and link equivalent C source files.


---

## 4. Where GCC Wins (Work-in-Progress Optimization Gaps)

GCC decisively outperforms SINC in specific structural patterns:

1. **Memory Streaming Latency & Prefetching (`dram_stream_triad` — GCC 4.2x faster)**:
   GCC aggressively schedules software prefetch instructions (`prefetcht0`) and unrolls non-temporal streaming pipelines. SINC executes straight-line 512-bit AVX-512 streaming vector memory loops directly (12.03 ms vs 2.85 ms), without hardware prefetch priming.
2. **Global Common Subexpression Elimination across Branches (`magic_bitboard` — GCC 3.9x faster)**:
   GCC builds global value graphs and computes complex shift-mask combinations with fewer redundant register transfers.
3. **Deep Recursive Call Frames & Leaf Call Vector Overhead (`deep_call_stack`, `pure_calls_speed`)**:
   GCC performs tail-call elimination and frame coalescing across deep recursive call trees (3.72 ms vs 12.37 ms). For leaf vector calls (`pure_calls_speed`), AVX-512 SIMD lowered latency from 52.65 ms down to **32.76 ms** (narrowing the gap to 1.62x vs GCC's 20.27 ms).
4. **Loop Induction and Constant Propagation (`bench_unroll_fir8`, `bench_unroll_nested`)**:
   When loops compute static constants, GCC's scalar evolution engine folds the entire loop into a single closed-form arithmetic product ($O(1)$), whereas SINC executes the loop at runtime. Pure 3-address EVEX register alternating reduced `bench_unroll_nested` latency from 2.90 ms down to **1.61 ms** (narrowing GCC's margin from 5.00x down to 3.04x).
5. **Matrix Transposition & Cache Blocking (`matrix_transpose_tiled` — GCC 2.7x faster)**:
   GCC schedules non-temporal streaming writes and interleaves transpose blocks across cache lines. SINC emits clean 1-cycle SIB LEAs and 3-address IMULs without cache priming (7.44 ms vs 2.71 ms).
6. **Arithmetic Expression Scheduling (`math_speed` — GCC 1.11x faster)**:
   GCC schedules parallel arithmetic pipes across execution ports on complex mixed scalar logic. SINC has substantially narrowed this gap to within 11% (27.45 ms vs 24.69 ms).
7. **Pointer Chasing in Linked Trees (`tree_traverse` — GCC 1.68x faster)**:
   GCC schedules data prefetch hints and reorders node pointer dereferences across iterations. SINC's direct instruction emitter generates code sequentially from the optimized tape, leaving memory latency hiding primarily to the CPU's out-of-order execution engine (124.22 ms vs 73.87 ms).
8. **Multi-Dimensional Stencil Vectorization (`jacobi_stencil` — GCC 1.48x faster)**:
   GCC's polyhedral loop analyzer recognizes 2D grid index patterns and reuses vector registers across adjacent row strides. SINC currently vectorizes 1D linear loops via AVX-512, but does not yet perform cross-stride 2D register tiling (74.05 ms vs 50.01 ms).

---

## 5. Weaknesses SINC Will NOT Fix (Intentional Design Boundaries)

There are several areas where GCC appears "faster" or where other compilers behave differently, but which SINC **intentionally refuses to implement**:

### A. No Compile-Time Deletion of Developer Work
GCC will sometimes detect an arithmetic loop (such as summing numbers from 0 to N) and replace the entire 10-million-iteration loop with a closed-form Gauss formula ($N(N+1)/2$). In a microbenchmark, GCC outputs `0.000s`, which can create an impression of instant execution. SINC chooses not to do this: if a developer writes an explicit loop to run at runtime, SINC executes that loop faithfully rather than evaluating it away into a closed-form constant.

### B. Developer Obedience Over Unsolicited Transformations
A core principle of SINC is obedience to the developer:
* SINC does exactly what the developer wrote.
* If a developer writes code with redundant calculations, SINC compiles and executes those calculations faithfully.
* The compiler will not silently restructure code or alter program intent under the assumption that it knows better than the developer.
* SINC values mechanical predictability where source statements map directly to emitted assembly.

### C. Static Bare-Metal Objects Over Dynamic Linking
SINC is designed as a bare-metal static tool. It does not implement dynamic linking (`.so`, `dlopen`, PLT/GOT relocations) or bundle a standard C runtime library. Interoperability with external C/C++ code is provided strictly through static ELF relocatable object files (`.o`) emitted by `packager_o`.

### D. Flat Tape Architecture Rather Than Traditional Graph Approaches
Traditional compilers typically construct graph-based Abstract Syntax Trees (ASTs) and Control Flow Graphs (CFGs). SINC is simply built to be different: its 7 sequential optimization passes (`inline`, `unroll`, `loops`, `vectorizer`, `simplify`, `erls`, `dce`) operate directly on a contiguous flat 64-bit IR word tape in pre-allocated linear memory. SINC chooses not to use graph-based approaches because the flat tape is central to its identity, keeping memory access linear, cache-friendly, and compilation times in the single-digit milliseconds. SINC intentionally prioritizes exploring this alternative architectural path rather than adopting traditional graph-rewriting frameworks.
