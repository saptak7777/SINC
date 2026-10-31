# Chapter 7: Refinement Types & Index Safety

In traditional programming languages, types only tell the compiler *what kind* of data a variable holds (like an integer or a pointer). 

In SINC, **Refinement Types** allow you to tell the compiler **what range of values** a variable is allowed to hold. By attaching a simple upper bound to a variable, you get **100% compile-time memory safety** with **zero runtime speed penalty**.

---

## 1. Declaring Range Bounds (`:N`)

You can refine the range of any parameter, loop counter, or memory buffer by adding a colon `:` followed by a positive integer limit:

```sinc
// 1. A parameter that is guaranteed to never exceed 10
fn get_item(idx:10) [
    ret idx;
]

// 2. A loop whose counter is proven to stay within 0 .. 63
loop (i:64 = 0 .. 64) [
    // The compiler knows 'i' is always less than 64
]

// 3. A local memory buffer with a fixed capacity of 64 words
buf:64 = arena_alloc_words!(arena, 64);

// 4. A function parameter receiving a bounded 64-word buffer
fn process_buffer!(buf:64) [
    ret buf@[0];
]
```

---

## 2. Compile-Time Memory Safety (Zero Crashes)

Most languages enforce memory safety by adding hidden checks that run on every array access while your program executes. If you go out of bounds, your program crashes at runtime.

SINC follows a different philosophy: **Fail Fast, Fail Hard. We Won't Compile Bad Code.**

When you access a bounded buffer (`buf:N`), SINC validates your index **at compile time**:

```sinc
fn process!(arena) [
    buf:64 = arena_alloc_words!(arena, 64);

    // OK: Constant index is within the 64-word capacity
    buf@[0]  = 42;
    buf@[63] = 100;

    // Error 15: Constant index is out of bounds!
    // buf@[64] = 999; 

    // OK: Loop counter 'i' is proven to never exceed 64
    loop (i:64 = 0 .. 64) [
        buf@[i] = i * 2;
    ]

    // OK: Refinement is copied across variable assignment
    idx = i;
    buf@[idx] = 42;

    // Error 15: Compound arithmetic drops proven refinement
    // buf@[i + 1] = 999; // Syntax error: arithmetic needs parentheses: buf@[(i + 1)]
    // Even with parentheses, compound expressions drop proven refinement!

    // Error 15: Negative constants are unrefined
    // neg = -1;
    // buf@[neg] = 0; // Rejected at compile time!

    ret 0;
]
```

### Indexing Rules for Bounded Buffers:
1. **Clean Index Variables**: Arithmetic inside index brackets requires parentheses (`buf@[(i + 1)]`) because `@[...]` binds tighter than arithmetic operators. However, bounded buffers (`buf:N`) require an index whose range is statically proven by the compiler. Compute the index into a refined variable beforehand or use loop counters with proven bounds.
2. **Bounds Propagate Across Assignments**: When you assign a bounded index to a new variable (`idx = i;`), the new variable inherits the bound and can be used to index safely.
3. **Negative Indices are Prohibited**: Negative numbers cannot index refined buffers.

If an index cannot be proven safe, compilation halts immediately with **Compile Error `15`**. Your code will not build until memory safety is guaranteed.

---

## 3. Why Refinement Types Make Your Code Faster

Traditional runtime bounds checks emit comparison and jump instructions on every access:

```asm
; Traditional runtime check emitted on every index:
cmp rsi, 64
jae .panic_out_of_bounds    ; Extra CPU branch check
mov rax, [rdi + rsi*8]
```

Because SINC proves bounds safety **at compile time**, all runtime checks are eliminated. SINC emits direct, single-cycle hardware instructions:

```asm
; SINC emitted machine code (bounds proven at compile time):
mov rax, [rdi + rsi*8]     ; 1 CPU cycle, 0 branch penalties
```

You get complete memory safety with **zero runtime overhead**.

---

## 4. Automatic Optimizations

When you provide refinement bounds, SINC uses that knowledge to optimize your code automatically:

* **AVX-512 SIMD Vectorization**: When the compiler knows a loop iterates over a bounded array, it can automatically convert your scalar loop into 8-lane 512-bit vector instructions without needing scalar cleanup tails.
* **Loop Unrolling**: Constant trip loops with known limits are automatically unrolled into straight-line instructions for maximum CPU throughput.
* **Branch Elimination**: Conditional checks inside bounded loops can be flattened into single-cycle conditional move (`CMOV`) instructions.

---

## 5. Summary

Refinement Types are the third pillar of SINC's safety system:

1. **`!` (Effects)**: Ensures pure mathematical functions never mutate memory or cause side effects.
2. **`~` (Linearity & Borrowing)**: Ensures allocated memory is uniquely owned, safely borrowed, and never leaked.
3. **`:` (Refinement)**: Ensures memory buffers are never indexed out of bounds.

By combining these three rules, SINC programs eliminate memory leaks, out-of-bounds errors, and unintended side effects at compile time, running directly at physical CPU speed.

