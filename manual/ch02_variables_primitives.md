# Chapter 2: Variables & Primitives

Variables in SINC store 64-bit numbers in hardware registers and are scoped to the function or block where they are declared:

```sinc
fn main!() [
    count = 10;
    rate = 2;
    result = count * rate;
    ret result;
]
```

There are no type annotations. Every local variable is assigned by name and scoped to its function or block.

---

## The 64-Bit Word: SINC's Basic Value

SINC has **one basic value: the 64-bit integer word**.

Because SINC compiles directly to x86-64 machine code without a virtual machine or heavy runtime, every variable maps directly to:
1. One of the **10 general-purpose CPU registers** (`rax`, `rcx`, `rdx`, `rbx`, `rsi`, `rdi`, `r8`, `r9`, `r14`, `r15`), or
2. An 8-byte stack slot when all 10 registers are busy (keeping `r10` and `r11` as scratch registers, `rsp`, `rbp`, `r12`, and `r13` reserved, and 30 vector registers available for loops).

All arithmetic operations (`+`, `-`, `*`, `/`) and bitwise operators (`&`, `|`, `^`, `<<`, `>>`) operate natively on 64-bit words using direct physical CPU instructions (`add`, `sub`, `imul`, `idiv`, `and`, `or`, `xor`, `shl`, `sar`).

---

## Constants (`const`)

SINC supports top-level global constants:

```sinc
const BUFFER_SIZE = 4096;
const TIMEOUT_SECS = 30;

fn get_buffer_limit() [
    ret BUFFER_SIZE;
]
```

Constants are defined at the top level of the file using the `const` keyword. They hold positive or negative 64-bit integer values resolved at compile time. SINC bakes constants directly into machine instructions as immediate numbers, eliminating memory lookups.

---

## Resource Ownership: Buffers and Pointers

In SINC, plain numbers are copied freely and can be reused without restriction. However, memory resources—such as bounded buffers (`buf:64`) and pointer parameters (`ptr@`)—follow strict single-ownership rules:
1. **Move by Default**: Passing a buffer or assigning `b = a;` transfers ownership to `b`. Once moved, `a` cannot be read again.
2. **Borrowing with `~`**: If you want to inspect a buffer without transferring ownership, append a trailing tilde: `b = a~;`.
