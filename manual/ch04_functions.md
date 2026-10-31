# Chapter 4: Functions

Functions in SINC accept up to 10 register arguments, compute a result, and return a 64-bit value in register `rax`:


```sinc
fn add(x, y) [
    ret x + y;
]

fn main!() [
    res = add(10, 20);
    ret res;
]
```

Functions are the primary abstraction block in SINC. By default, they are pure and cannot cause side effects or modify global state.

---

## Function Parameters & Return Types

Functions define parameters inside parentheses `()`, separated by commas. SINC is typeless, so parameters do not have explicit type labels.

The function return value is specified by the `ret` keyword followed by an expression. Every function must end with `ret <expr>;` (use `ret 0;` when there is no meaningful return value). The compiler only emits the function exit epilogue on an explicit `ret` statement; omitting `ret` causes execution to fall off the end of the function.

---

## Hardware Calling Convention

Function parameters are mapped sequentially across 10 general-purpose registers: `rax`, `rcx`, `rdx`, `rbx`, `rsi`, `rdi`, `r8`, `r9`, `r14`, and `r15`.

Arguments passed in these 10 hardware registers require zero stack memory pushes, executing at direct register speed. Additional arguments, if any, spill to 8-byte stack slots.

Pure leaf functions (containing no inner loops, branches, or downstream function calls) are automatically flattened into their callers by the inliner pass (`ir_inline!`), removing `call`/`ret` jump overhead completely from the generated machine code.
