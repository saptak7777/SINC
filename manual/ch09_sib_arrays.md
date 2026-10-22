# Chapter 9: Hardware SIB Arrays

SINC compiles buffer indexing directly into x86-64 Scale-Index-Base (SIB) memory operands:

```sinc
fn get_word(arr, index:15) [
    // Read the index-th 8-byte word directly from memory
    value = arr@[index];
    ret value;
]
```

When you write `arr@[index]`, SINC lowers it straight to a single x86-64 assembly instruction:

```assembly
mov rax, [rax + rcx * 8]
```

Because SINC values are 64-bit words, subscript indexing scales by 8 bytes automatically. The CPU executes the base address addition, index scaling, and memory load in a single hardware cycle.

---

## The Syntax of SINC Subscripts

SINC supports both default word scaling and explicit byte scaling:

```sinc
base@[index]         // Default: 8-byte word indexing ([base + index * 8])
base@[index * scale] // Explicit scale: 1, 2, 4, or 8
```

*   **`base@[index]`**: The standard word-indexing form. Automatically scales by 8 bytes, reading or writing the `index`-th 64-bit word.
*   **`base@[index * 1]`**: Single-byte indexing. Reads or writes a single byte at byte offset `index`.
*   **`scale`**: Hardware supports scales of `1`, `2`, `4`, or `8` bytes.

Always align your data structures to power-of-two boundaries to allow the CPU to address memory in a single cycle.

---

## Combining Refinements with SIB for Zero-Overhead Safety

In SINC, refinement types guarantee bounds safety at compile time. By defining `index:15`, the compiler knows that `index` is guaranteed to stay within `[0, 15]`. When accessing a buffer with a known capacity of 16 elements, the compiler verifies the index statically and emits the raw SIB instruction without runtime comparison or jump instructions.

