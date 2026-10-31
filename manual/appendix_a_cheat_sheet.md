# Appendix A: SINC Cheat Sheet

This cheat sheet serves as a quick reference for the SINC syntax, sigils, and compiler constraints. If you ever find yourself scratching your head wondering why a variable suffix is refusing to compile, this is the place to check.

---

## The Sigils Table

The suffixes !, ~, and :N are parsed directly into the identifier token, while @ is a separate postfix token (T_AT).

| Sigil / Suffix / Prefix | Example Usage | Type / Hardware Flag | Description |
| :--- | :--- | :--- | :--- |
| **`!`** (Suffix) | `fn print!(msg)` | Impure (clears `FLAG_PURE`) | Marks a function as impure or side-effectful. Impure functions cannot be called from pure functions. |
| **`~`** (Suffix) | `read(packet~)` | Explicit Borrow (clears `FLAG_LINEAR`) | Explicitly borrows a linear variable for non-consuming reads. Default usage without `~` is a Move. |
| **`@`** (Suffix) | `buffer@`, `ptr@[i * 8]` | Deref Token (`T_AT`) | Treats the value as a memory pointer. Allows zero-overhead indexing and base-displacement offset lookups. |
| **`:`** (Infix) | `index:15`, `buf:64` | Refinement Bounds | Attaches a compile-time range constraint of `[0, Bound]` to an integer variable or buffer. |

*(Note: Loop vectorization into 8-lane 512-bit AVX-512 instructions is automatic via the middle-end `vectorizer.sinc` pass on bounded linear loops; no explicit sigil is needed).*

---

## Single Source of Truth (SSOT) Flag Packing

When the lexer processes an identifier, it packs all type and semantic flags into a single 64-bit word (`TOK_FLAGS`). This allows SINC to run single-pass compilation without abstract syntax trees:

```
  Bits 63..32                               Bits 31..2       Bit 1     Bit 0
+-----------------------------------------+----------------+---------+---------+
|             REFINEMENT BOUND            |    (Unused)    |  PURE   | LINEAR  |
+-----------------------------------------+----------------+---------+---------+
```

*   **`LINEAR` (`1 << 0`)**: Enforced linear usage. By default, every variable is linear; trailing `~` clears this bit for explicit borrowing.
*   **`PURE` (`1 << 1`)**: Set by default. Cleared if the function name ends with `!`.
*   **`BOUND` (Bits 32–63)**: Stores the parsed integer limit when an identifier has an attached refinement bound (`:Bound`).

---

## Refinement Constraints

Refinement constraints enforce bounds safety at compile time. By attaching `:Bound` to an identifier, you restrict its value range:

```sinc
fn process(index:15, buf:16) [
    // buf has size 16 (0..15).
    // The compiler knows index is [0, 15].
    // This load requires ZERO runtime bounds checks!
    val = buf@[index];
    ret val;
]
```

### Compiler Rules for Refinement Ranges:
1.  **Constants**: Non-negative integer literals create an exact refined range `[k, k]`. Negative numbers cannot index refined buffers.
2.  **Refined Params**: Parameter `x:10` is refined to `[0, 10]`.
3.  **Loop Indices**: A loop over `i = 0 .. limit` refines the index `i` to `[0, limit)`.
4.  **Refinement Copying**: Assigning `x = i;` preserves and propagates the refinement bound to `x`.
5.  **Clean Indices Only**: Compound arithmetic expressions (`buf@[i + 1]`) are rejected; compute the index variable beforehand.
6.  **Out-of-Bounds Rejection**: If an index cannot be proven within buffer bounds at compile time, compilation halts with Error 15.

---

## STAFF CLI & Triad Quick Reference

### The Universal Triad Layout
```text
project/
├── build.staff         # Zero-config manifest
├── data/               # Constants, lenses, offsets (pure data, 0 logic)
├── pure/               # Pure functions (fn), algorithms (0 side-effects)
└── sys/                # Impure effects (fn ...!), entry.sinc (fn main!())
```

### Project Manifest (`build.staff`)
```text
artifact app_name []

deps [
    steel/sys/sys.sinc;
    steel/sys/arena.sinc;
]
```

### STAFF CLI Workflow
* `./bin/staff <manifest.staff> [output.safe]` — Compiles manifest sources directly into a standalone `.safe` machine code payload in memory.
* `./bin/packager_bin <output.safe> <output.elf>` — Packages the `.safe` payload into a zero-dependency Linux ELF executable.




