# Appendix C: Diagnostics & Exit Codes

Because SINC is a bare-metal, self-hosted compiler designed for extreme compilation speed (~1,000,000 LOC/s), it does not construct heavy diagnostic AST graphs or format verbose multi-line template stack traces. 

Instead, the compiler follows a **fail-fast architecture**: upon encountering an unrecoverable syntactic, semantic, or safety constraint violation, the compiler halts immediately by returning a distinct non-zero integer exit code to the shell via `sys_exit!(code)`.

You can inspect the compiler's diagnostic exit code immediately in your terminal:
```bash
./bin/sinc.elf main.sinc main.safe
echo $?
```

---

## Compiler Exit Code Reference Table

| Exit Code | Diagnostic Category | Meaning / Constraint Violated | Triggering Subsystem |
| :---: | :--- | :--- | :--- |
| **`1`** | **Syntax / Arity Error** | Unexpected token, missing identifier, or function call arity mismatch. | `sinc/sys/parser.sinc` |
| **`2`** | **Parameter Syntax** | Malformed parameter list or expected parameter identifier. | `sinc/sys/parser.sinc` |
| **`3`** | **Unconsumed Linear Binding** | A linear variable was defined but not consumed before leaving scope. | `sinc/pure/parser_bindings.sinc` |
| **`4`** | **Linear Branch Divergence** | A linear variable was consumed in one branch (`then`) but not in the other (`else`). | `sinc/pure/parser_bindings.sinc` |
| **`5`** | **Purity Violation / Missing `;`** | Calling an impure function (`!`) from a pure scope, or missing statement semicolon. | `sinc/pure/parser_pratt.sinc` |
| **`6`** | **Invalid Top-Level Item** | Top-level item other than `fn`, `extern`, or `const`. | `sinc/sys/parser.sinc` |
| **`7`** | **Expression Syntax** | Operator precedence parsing failure, unbalanced parentheses, or misplaced operator. | `sinc/pure/parser_pratt.sinc` |
| **`8`** | **Use-After-Move** | Attempting to read or move a linear variable that has already been consumed. | `sinc/pure/parser_bindings.sinc` |
| **`10`** | **No Functions Defined** | Input program contains zero function definitions (`func_count < 1`). | `sinc/sys/entry.sinc` |
| **`11`** | **Function Table Overflow** | Program exceeds maximum of 1,024 function definitions (`func_count > 1024`). | `sinc/sys/entry.sinc` |
| **`12`** | **Code Buffer Overflow** | Compiled machine code exceeds 40 MB buffer ceiling (`code_len > 40000000`). | `sinc/sys/entry.sinc` |
| **`14`** | **Pure Memory Store** | Attempting to mutate memory (`@[...] = val`) inside a pure function. | `sinc/sys/parser.sinc` |
| **`15`** | **Out-of-Bounds Index** | Buffer index statically proven to exceed declared refinement bound (`idx >= bound`). | `sinc/pure/parser_pratt.sinc` |
| **`16`** | **Invalid Shift** | Bitwise shift amount $\ge 64$ detected during constant propagation. | `sinc/pure/simplify.sinc` |
| **`17`** | **Unbounded Loop Range** | Loop iteration range statically exceeds the loop's declared `:Bound`. | `sinc/sys/parser.sinc` |
| **`96`** | **Virtual Register Overflow** | A function exceeds 65,534 virtual registers (`val_id_counter > 65534`). | `sinc/sys/parser.sinc` |
| **`97`** | **Instruction Tape Overflow** | A function exceeds 65,534 IR instructions (`final_count > 65534`). | `sinc/sys/parser.sinc` |
| **`98`** | **Arena / Table Overflow** | Function descriptor table or call argument arena capacity exhausted. | `sinc/sys/parser.sinc`, `sinc/pure/parser_pratt.sinc` |
| **`99`** | **Out of Memory** | Descriptor arena allocation returned 0 (OOM ceiling reached). | `sinc/sys/parser.sinc` |

> *(Note: File I/O and CLI argument exit codes live in the driver/packager: `packager_entry.sinc` returns 1 for missing arguments, 2 for bad `.safe` header, 3 for open-write failure, 4 for mmap failure, 5 for write failure, and 6 for short read).*

---

## Detailed Error Patterns & Fixes

### Error 3 & 4: Linear Ownership Violations
In SINC, every variable is linear by default. If a linear value is not consumed, or if branches diverge, compilation halts:

```sinc
// FAILS with Exit Code 4 (Branch Divergence):
fn handle_packet!(p, flag) [
    if (flag > 0) [
        consume_packet!(p); // p consumed here
    ] else [
        // Error: p was NOT consumed in the else branch!
    ]
    ret 0;
]

// FIX: Ensure both branches consume p, or borrow with ~:
fn handle_packet!(p, flag) [
    if (flag > 0) [
        consume_packet!(p);
    ] else [
        drop_packet!(p);
    ]
    ret 0;
]
```

### Error 5: Purity Violations
Pure functions (`fn`) are mathematically isolated from memory mutation and I/O:

```sinc
// FAILS with Exit Code 5:
fn compute(data) [
    sys_write!(1, data, 8); // Error: calling impure 'sys_write!' from pure function
    ret data;
]

// FIX: Declare the function as impure with '!':
fn compute!(data) [
    sys_write!(1, data, 8);
    ret data;
]
```

### Error 8: Use-After-Move
Reading a linear resource after passing it moves ownership:

```sinc
// FAILS with Exit Code 8:
fn main!() [
    buf:64 = arena_alloc_words!(arena, 64);
    process_buf!(buf);
    val = buf@[0]; // Error: buf was already moved into process_buf!
    ret val;
]

// FIX: Borrow the buffer using trailing tilde '~':
fn main!() [
    buf:64 = arena_alloc_words!(arena, 64);
    process_buf!(buf~); // Borrows buf without consuming ownership
    val = buf@[0];      // OK: buf is still active
    ret val;
]
```

### Error 15: Compile-Time Bounds Failure
Refinement types prove bounds statically:

```sinc
// FAILS with Exit Code 15:
fn get_entry(index:100, buf) [
    ret buf@[index]; // Error: buf size is unproven, or index > bound
]

// FIX: Ensure buffer has a matching refinement proof:
fn get_entry(index:64, buf:64) [
    ret buf@[index]; // Proven safe: 0 runtime bounds checks needed!
]
```
