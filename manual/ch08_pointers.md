# Chapter 8: Pointers & The `@` Sigil

A pointer in SINC is a 64-bit memory address. The `@` operator reads or writes bytes and 8-byte words at that address:

```sinc
fn exchange!(ptr, value) [
    // Read the current 64-bit integer from the pointer address
    current = ptr@;
    
    // Write the new value to the pointer address
    ptr@ = value;
    
    // Return the original value
    ret current;
]
```

Every value in SINC is a 64-bit word, so pointers are not special types. The postfix `@` sigil tells the compiler to treat the value as an address and emit a load or store instruction.

---

## The `@` Sigil and Postfix Dereferencing

The `@` sigil can be attached to any variable or expression:
*   **Base dereference (`ptr@`)**: Reads or writes the 8-byte word at the address in `ptr`.
*   **Word indexing (`ptr@[i]`)**: Reads or writes the `i`-th 8-byte word. SINC scales `i` by 8 automatically (`[ptr + i * 8]`).
*   **Byte indexing (`ptr@[i * 1]`)**: Reads or writes a single byte at byte offset `i` (`* 2` and `* 4` scaling are also supported).
*   **Expression dereference (`(base + 8)@`)**: Dereferences a parenthesized address calculation.

When reading from a dereference (`val = ptr@;` or `val = ptr@[i];`), the compiler generates a load instruction. When assigning to it (`ptr@ = val;` or `ptr@[i] = val;`), the compiler generates a store instruction.

In function signatures, parameters holding base memory addresses are declared plainly (e.g. `fn process!(ptr, count)`). You dereference the pointer inside the function body using postfix `@` (`ptr@`), subscript indexing (`ptr@[i]`), or constant lenses (`ptr.LENS`).

### Indexing Syntax and Parentheses

Arithmetic inside index brackets requires parentheses because `@[...]` binds tighter than `+` and `*`:

```sinc
// Parenthesize arithmetic expressions inside index brackets:
val = arr@[(i + 1)];

// Or compute the index into a variable beforehand:
idx = i + 1;
arr@[idx] = val;
```

---

## Pointer Tiers: Refined `:BOUND` Slices vs. Raw Dynamic Pointers

Memory access in SINC operates in two distinct architectural tiers:

### Tier 1: Refined `:BOUND` Slices (Statically Bounds-Checked)
When a pointer or loop variable is declared with an explicit upper bound (e.g. `buf:64` or `loop (i:128 = 0 .. count)`), SINC's frontend activates static range refinement:
* Every load and store (`buf@[idx]`) is checked against the known bound at compile time.
* If an index exceeds or cannot be proven to fit within `0 .. BOUND - 1`, the compiler rejects the program immediately with **Exit Code 15** (`Index Out Of Bounds`).
* Refined variables carry linear ownership semantics: assigning or passing a refined slice transfers ownership, preventing accidental double consumption or data corruption.

### Tier 2: Raw Dynamic Pointers (Unchecked by Design)
When memory is allocated dynamically via bump arenas (`arena_alloc_words!`) or OS `sys_mmap!` without a bound suffix, the pointer has `rng == 0`:
* Raw pointers represent unchecked low-level memory buffers (tapes, hash tables, bytecode emit buffers).
* They allow unbounded pointer arithmetic, arbitrary offset arithmetic, and aliasing necessary for systems programming, runtime kernels, and compiler internals.
* No compile-time bounds checks are synthesized for raw pointers; bounds management is the responsibility of the allocator and loop termination invariants.
