# Manifesto: Simple & Efficient by Design

```sinc
// a taste of SINC: zero garbage collection, zero runtime overhead.
fn consume!(buf~) [ ret buf@[0] * 2; ]

fn main!() [
    buf:64 = arena_alloc_words!(arena, 64);
    ret consume!(buf~); // borrows buf, preserving linear ownership
]
```

Honestly, I really hate Garbage Collectors. But I also absolutely detest writing code that randomly segmentation faults because I mismanaged a pointer. So SINC is basically my compromise.

If you look at modern systems languages, they have become incredibly complex. They have giant compilers, complex abstract syntax trees (ASTs), and runtime safety mechanisms that eat up CPU cycles.

SINC is an experimental exploration: a **prototype with no guarantees**, built around a single main objective—to explore a completely different type of compiler built for **SSS: Speed, Safety, Simplicity**. We reject unnecessary complexity.

I threw out user-defined structs, garbage collection, and hidden control flow. I want SINC to be simple, but simple doesn't mean it generates unoptimized binary that is slow in runtime. Every single line of SINC compiles down to raw x86-64 machine instructions without any middleman. And the whole compiler core—lexing, parsing, register allocation, optimization, and code generation—is implemented in roughly **4,200 lines of SINC code**, and it compiles itself in about **4 to 5.5 milliseconds wall-clock / ~3.4 ms CPU user time**.


---

## The Core Philosophy

### 1. The Principle of Eliminating Structs
Designing a complex type checker for structures and classes is a massive headache. So I didn't build one. The goal was to build an optimizing compiler that one person can understand, upgrade, and maintain—achieving fast compile times and clean machine code without AST, CFG, or SSA complexity.

SINC does not have structs. Instead, we use **Constant Lenses** (global constant offsets mapped directly to raw memory addresses). It sounds a bit sketchy at first, but it compiles straight into hardware SIB (Scale-Index-Base) pointer arithmetic. No memory copying, no pointer aliasing issues, and zero runtime cost.

### 2. Symmetries and the Law of Consumption (Linear by Default)
In SINC, every variable binding is **Linear by Default**. If you create a resource (like a buffer or scalar value), passing it or assigning it to another variable moves ownership and consumes it. 

If you want to read a linear resource without consuming it, you use **explicit borrowing** by suffixing it with a trailing tilde `~` (e.g. `read_packet!(packet~)`).

If you try to read a consumed variable again without borrowing, the compiler stops compilation immediately (Compile Error `8`). It is a simple, compile-time rule that makes resource leaks and accidental aliasing mathematically impossible, without needing a garbage collector or complex lifetime annotations.

### 3. Explicit Effects (`!`)
If a function does something dangerous—like writing to a file or mutating memory—it must have an exclamation mark `!` suffix.

Think of it as a warning label. It tells you and the compiler that this function is impure. And since pure functions cannot call impure functions, we get complete architectural isolation between logic and side effects. This lets the compiler aggressively optimise your code.

### 4. The Law of Bounded Space: Refinement Types (`:`)
Most "safe" modern languages prevent buffer overflows by spraying your compiled binary with hidden comparison branches (`cmp` + `jae .panic`) on every single array access. If your index goes out of bounds, your program crashes at runtime.

SINC rejects runtime crashes. We use **Refinement Types (`:N`)** to prove bounds statically at compile time:

```sinc
// buf is proven to hold 64 words; loop index 'i' is proven to stay within 0 .. 64
buf:64 = arena_alloc_words!(arena, 64);
loop (i:64 = 0 .. 64) [
    buf@[i] = i * 2; // 0 runtime bounds checks. 1 single-cycle CPU instruction.
]
```

If you try to index a bounded buffer with an unproven, subexpression, or out-of-bounds variable, SINC doesn't build a binary that panics in production—**the compiler halts compilation immediately** (Compile Error `15`). Because bounds are mathematically proven before code emission, SINC completely eliminates runtime bounds checking. You get raw, single-cycle machine memory access (`mov rax, [rdi + rsi*8]`), and the compiler can auto-vectorize your loops directly into 512-bit AVX-512 instructions with zero scalar cleanup tails.

### 5. Architectural Trade-offs (To Get Something, You Lose Something)
SINC is intentionally strict. It refuses to let you leak a resource, it refuses to let you index a buffer without proving its bound, it refuses to let you write an unbounded while-loop, and it outright bans memory writes inside pure code.

Together, these form **The Chosen Trinity of SINC**:
1. **`!` (Effects)**: Pure math can never touch memory or trigger side effects.
2. **`~` (Linearity & Borrowing)**: Resources are uniquely owned by default; trailing `~` allows safe borrowing—zero leaks, zero double-frees, zero aliasing bugs.
3. **`:` (Refinement)**: Memory indices are proven in-bounds—zero buffer overflows, zero runtime branch checks.

**To get something, you trade away something**. You trade away automatic garbage collection overhead and dynamic type flexibility to get mathematically provable safety, zero runtime checks, and a compiler that builds in milliseconds.

---

So, welcome to SINC. It is simple, it is direct, and it is built for **SSS: Speed, Safety, Simplicity**. Let's get started.

