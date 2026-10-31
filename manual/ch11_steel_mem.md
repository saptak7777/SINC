# Chapter 11: The `steel_mem` and `steel_string` Engines

SINC provides direct memory copying and slicing using pointer arithmetic and compile-time bounds checking:

```sinc
// Copies count words from src to dest (indices automatically scale by 8 bytes)
fn copy_words!(dest, src, count) [
    loop (i = 0 .. count) [
        val = src@[i];
        dest@[i] = val;
    ]
    ret 0;
]
```

SINC relies entirely on direct pointer operations and arena-backed layouts, avoiding garbage collection and complex runtime allocators.

---

## Zero-Overhead Memory Copying

In SINC, arrays and buffers are represented as raw pointers `ptr`. Because SINC lacks structures, you do not allocate struct instances—you just slice and manipulate raw byte buffers.

To prevent buffer overflows in a loop like `copy_words!`:

A runtime bounds check on `src@[i * 8]` and `dest@[i * 8]` for every iteration would add CPU overhead. SINC does not inject runtime checks.

Instead, the loop counter `i` is refined by the loop bounds `0..count`. If `count` has a known upper bound, SINC's simplifier verifies that the index is safe. If the ranges prove that no out-of-bounds access is possible, SINC compiles this loop with zero runtime boundary checks. It translates directly to a tight assembly loop executing `mov` operations at full hardware speed.

---

## Memory Slicing

If you want to extract a sub-portion of a memory buffer, you do not copy the bytes into a new buffer. You just offset the base pointer using offset arithmetic:

```sinc
fn get_payload(packet) [
    // Shift base pointer forward by 4 words (32 bytes)
    payload_ptr = packet + 32;
    ret payload_ptr;
]
```

And because pointers are typeless, this is completely free. We just add `32` to the base address and return it, creating a zero-cost memory slice.

---

## Module 2: S.T.E.E.L. Linear Memory Arena

The standard library `steel_mem` module implements a zero-fragmentation, zero-GC Linear Bump Allocator (`steel/sys/arena.sinc`) using compile-time **Constant Lenses**:

*   `ARENA_START` (Offset 0): The start of allocatable space.
*   `ARENA_NEXT` (Offset 1): The next free address cursor.
*   `ARENA_LIMIT` (Offset 2): The boundary limit of the mmap'd region.

The allocator manages memory strictly in 8-byte aligned boundaries (`((bytes + 7) >> 3) << 3`):

```sinc
const ARENA_START = 0;
const ARENA_NEXT  = 1;
const ARENA_LIMIT = 2;

fn arena_alloc!(arena, bytes) [
    aligned_bytes = ((bytes + 7) >> 3) << 3;
    current_next = arena.ARENA_NEXT;
    limit = arena.ARENA_LIMIT;
    if (current_next + aligned_bytes > limit) [
        ret 0; // Out of memory
    ]
    arena.ARENA_NEXT = current_next + aligned_bytes;
    ret current_next;
]
```

---

## Module 4: Zero-Copy String Slices

The `steel_string` module introduces a zero-copy string representation (`steel/data/slice.sinc`) using a 2-word fat pointer layout:

*   `SLICE_PTR` (Offset 0): The raw memory address of the first character.
*   `SLICE_LEN` (Offset 1): The number of bytes.

### Native Byte-Level Memory Indexing
SINC provides native single-byte memory operations using the `* 1` scale factor in bracketed dereference syntax (`ptr@[i * 1]`). The backend emits direct x86-64 `movzx` (zero-extending byte loads) and `mov byte` instructions:

```sinc
// Native single-byte load (movzx rax, byte ptr [rdi + rsi*1])
char_byte = ptr@[i * 1];

// Native single-byte store (mov byte ptr [rdi + rsi*1], al)
ptr@[i * 1] = char_byte;
```

This delivers single-cycle byte manipulation with zero shift-and-mask overhead, as used throughout STEEL's string slice, lexer, and stream engines.

---

## Module 5: FNV-1a Hash Engine

The `steel/data/hash.sinc` engine takes a String Slice and grinds it into a single 64-bit integer using the FNV-1a algorithm:

*   **Signed Constant Representation**: Since SINC treats literals as signed 64-bit integers, the unsigned FNV-1a offset basis `14695981039346656037` is defined as its two's complement equivalent: `-3750763034362895579`.
*   **Hardware Wrapping**: Multiplication overflows naturally wrap at the 64-bit boundary matching FNV-1a logic.

---

## Module 6: Arena-Backed Symbol Table

To support the self-hosted SINC compiler frontend, `steel/data/sym_table.sinc` implements an open-addressed, linear-probing Symbol Table.

Each Symbol slot occupies exactly 4 words (32 bytes):
```sinc
const SYM_HASH = 0; // The 64-bit FNV-1a Hash
const SYM_PTR  = 1; // String character pointer
const SYM_LEN  = 2; // String length
const SYM_VAL  = 3; // Unique integer ID
```

### Direct Slot Slicing
Since a String Slice (`[PTR, LEN]`) shares the exact physical layout as the pointer and length fields of a Symbol Slot (`[HASH, PTR, LEN, VAL]`), we skip the Hash field by shifting the pointer forward by 8 bytes (`slot_ptr + 8`) and pass it directly to `slice_eq` as a standard slice. This allows zero runtime allocations during symbol lookup.

### Modulo Bitwise AND Masking
SINC does not support the modulo `%` operator. By requiring the Symbol Table capacity to be a power of two, SINC resolves table indexes using bitwise AND masking:
*   Initial index: `idx = hash & (capacity - 1);`
*   Linear probing step: `idx = (idx + 1) & (capacity - 1);`
This clears the sign bit and wraps slots in a single cycle without branching.
