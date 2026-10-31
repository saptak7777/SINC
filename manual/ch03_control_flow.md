# Chapter 3: Control Flow

Control flow in SINC consists of conditional `if`/`else` branches and bounded `loop` blocks:

```sinc
fn main!() [
    counter = 0;
    if (counter < 10) [
        counter = counter + 1;
    ]
    ret counter;
]
```

Branching and loops in SINC follow a strict format designed to keep parsing simple and single-pass.

---

## Branching (`if`, `else if`, `else`)

In SINC, conditions are enclosed in parentheses `()`, and statement bodies are enclosed in square brackets `[]`. Multiple branches are chained using `else if`:

```sinc
fn classify(x) [
    if (x < 0) [
        ret -1;
    ] else if (x == 0) [
        ret 0;
    ] else [
        ret 1;
    ]
]
```

Parentheses around the condition and square brackets around blocks are strictly required, allowing single-pass parsing without backtracking.

---

## Loops

SINC provides bounded `loop` constructs in two forms:

### 1. Constant Bounds
When the upper limit is a constant integer:

```sinc
fn sum_ten!() [
    sum = 0;
    loop (i = 0 .. 10) [
        sum = sum + i;
    ]
    ret sum;
]
```

### 2. Variable Bounds with Maximum Refinement Limit
When the upper limit is a variable (`n`), provide a maximum bound `:LIMIT` so the compiler can prove termination and verify bounds safety at compile time:

```sinc
fn sum_n!(n) [
    sum = 0;
    loop (i:1000 = 0 .. n) [
        sum = sum + i;
    ]
    ret sum;
]
```

In both forms, SINC compiles loops directly into x86-64 `cmp` and `jl` instructions without runtime overhead. The compile-time range information is preserved so subscript memory operations inside the loop body can be proven safe without runtime bounds checking.
