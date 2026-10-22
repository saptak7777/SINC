# Chapter 10: Typeless Constant Lenses

In SINC, you can access memory offsets using property-like accessor syntax without defining structs, classes, or layout descriptors:

```sinc
// Define compile-time field offsets in 8-byte words
const USER_ID = 0;
const USER_AGE = 1;
const USER_SCORE = 2;

fn update_score!(user, points) [
    // Read user score using a constant lens
    current = user.USER_SCORE;
    
    // Update score value
    user.USER_SCORE = current + points;
    ret user.USER_SCORE;
]
```

---

## 1. What Constant Lenses Actually Are

Instead of managing struct definitions, padding rules, and member alignment tables, SINC keeps the compiler minimal and fast.

SINC provides **Constant Lenses** as a shorthand for reading or writing 8-byte slots from a base address (`ptr.CONSTANT`):
* `CONSTANT` must be a globally defined compile-time integer constant (`const NAME = value;`).
* When the parser encounters `ptr.CONSTANT`:
  1. It looks up `CONSTANT` in the global constant table.
  2. It multiplies the offset by 8 bytes (`const_val * 8`).
  3. It emits a native base-displacement hardware instruction:
     ```assembly
     mov rax, [rdi + 16]   ; for user.USER_SCORE (offset 2 * 8)
     ```
* Similarly, for assignments (`user.USER_SCORE = val;`), the parser converts the load into a base-displacement store:
  ```assembly
  mov [rdi + 16], rsi
  ```

---

## 2. Architectural Boundaries (What Constant Lenses Are NOT)

To maintain realistic expectations, understand what this feature is and is not:

* **No Custom Struct Types**: SINC does not have `struct { ... }` or `class { ... }` keywords. All memory is raw flat memory.
* **No Field Type Checking**: The compiler treats the loaded value strictly as a 64-bit hardware integer or pointer.
* **No Sub-Word Alignment**: Constant lenses operate on **64-bit (8-byte) word displacements**. They are not intended for arbitrary byte-level packing.
* **No Nested Dot Syntax**: You cannot write `a.b.c`; lenses represent a single direct pointer-plus-offset calculation.

Constant lenses provide readable field-style access in source code while compiling straight to hardware base-plus-displacement instructions.

