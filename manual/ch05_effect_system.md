# Chapter 5: The Effect System (!)

SINC separates functions into pure calculations and impure side effects at compile time using the `!` mark:

```sinc
// A pure function by default
fn square(x) [
    ret x * x;
]

// An impure function (mutates memory or calls the OS)
fn write_log!(val) [
    ret 0;
]
```

Functions in SINC belong to two distinct categories: **Pure** and **Impure**.

---

## Pure vs. Impure

Every function in SINC is pure by default. A pure function is a mathematical calculation: it takes inputs, returns outputs, and does nothing else.

When a function needs to mutate memory, write to a buffer, or execute a system call, it must be marked with a trailing exclamation mark `!` (e.g. `write_log!`).

The compiler enforces two absolute rules on pure functions:
1. **No Impure Calls (Compile Error 5)**: A pure function cannot call any `!` function.
   ```sinc
   fn pure_calc(x) [
       write_log!(x); // Error 5: pure function cannot call impure function
       ret x + 1;
   ]
   ```
2. **No Memory Writes via `@` (Compile Error 14)**: A pure function cannot mutate memory addresses or buffers (`ptr@ = val;` or `ptr@[i] = val;`).
   ```sinc
   fn store_pure(ptr, val) [
       ptr@ = val; // Error 14: pure function cannot write to memory
       ret 0;
   ]
   ```

Marking side-effecting functions with `!` gives both the developer and the compiler a clear guarantee: pure functions can be cached, reordered, and hoisted, while impure functions execute in strict order.

---

## Optimization: Loop Invariant Code Motion (LICM)

Because the compiler knows exactly which functions are pure, it can optimize them safely.

If you call a pure function inside a loop, and the arguments do not change between iterations, the loop optimizer (`sinc/pure/loops.sinc`) lifts the entire function call out of the loop and executes it once:


```sinc
// SINC code
loop (i = 0 .. 100) [
    val = calculate_constant_pure(42);
    ptr@[i * 8] = val;
]
```

Behind the scenes, because `calculate_constant_pure` is pure and its arguments are loop-invariant, the optimizer hoists it. The final assembly compiles as if you wrote:

```sinc
val = calculate_constant_pure(42);
loop (i = 0 .. 100) [
    ptr@[i * 8] = val;
]
```

If the function were impure (if it had a `!`), the compiler wouldn't dare touch it, because lifting it might change the order of OS side effects or memory mutations. But for pure functions? We can speculate and hoist them safely.
