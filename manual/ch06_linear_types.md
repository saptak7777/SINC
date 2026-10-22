# Chapter 6: Linear Types & Borrowing (~)

In SINC, resource safety applies to memory buffers and pointers: **Bounded buffers and pointer parameters are linear by default**.

```sinc
fn free_buf!(buf) [
    // Consumes and releases the buffer
    ret 0;
]

fn handle!(packet:64) [
    free_buf!(packet); // packet is moved and consumed
    ret 0;
]
```

Plain numbers can be copied and reused freely. However, memory resources—such as bounded buffers (`buf:64`) and pointer parameters (`buf@`)—follow single-ownership rules to prevent use-after-free and memory leaks without runtime garbage collection.

---

## 1. Moving (Default)

Every memory buffer is uniquely owned. Passing a linear buffer to a function or assigning `b = a;` **moves** ownership:

```sinc
fn handle!(packet:64) [
    free_buf!(packet);
    
    // Error 8: 'packet' is already consumed
    // ret packet@[0]; 
    ret 0;
]
```

Attempting to read or pass a moved buffer triggers **Compile Error 8**.

---

## 2. Borrowing (`~`)

If you want to read or inspect a buffer **without consuming it**, append a trailing tilde `~`:

```sinc
fn read_checksum(buf) [
    ret buf@[0];
]

fn process!(packet:64) [
    // Borrow: packet stays valid for subsequent operations
    c1 = read_checksum(packet~); 
    c2 = read_checksum(packet~); 

    // Final move: consumes packet
    ret free_buf!(packet);
]
```

### Move vs. Borrow

| Syntax | Action | Can resource be used again? |
| :--- | :--- | :---: |
| `free_buf!(p);` | **Move** (transfers ownership) | No (consumed) |
| `read_checksum(p~);` | **Borrow** (temporary inspection) | Yes |
| `b = a;` | **Move** to `b` | `a` no, `b` yes |
| `b = a~;` | **Borrow** into `b` | Both can be used |

---

## 3. Chained Calls

When transforming resources through multiple processing stages, you can chain function calls left-to-right using dot syntax (`.`):

```sinc
fn verify!(p) [ ret p; ]
fn decrypt!(p) [ ret p; ]

fn process_stream!(packet:64) [
    packet = packet.verify!().decrypt!();
    ret packet;
]
```

Writing `packet.verify!().decrypt!()` passes `packet` as the first argument to `verify!`, and passes that result to `decrypt!`. Because chained calls evaluate left-to-right, explicit reassignment (`packet = ...`) keeps the transformed resource bound to `packet` without deeply nested call syntax like `decrypt!(verify!(packet))`.
