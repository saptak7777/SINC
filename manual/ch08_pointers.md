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


