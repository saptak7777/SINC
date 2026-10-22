# Chapter 1: Getting Started

Printing text to a terminal needs OS syscalls and byte buffers. To see how SINC works right away, let's start with a program that does math and returns the answer as an exit code:

```sinc
// converter.sinc
fn to_hours(minutes) [
    ret minutes / 60;
]

fn main!() [
    // Convert 180 minutes into hours
    hours = to_hours(180);
    ret hours;
]
```

SINC is built for one goal: writing fast, low-level code that maps straight to CPU registers and machine instructions, with compile-time checks for memory and side effects instead of runtime checks, garbage collection, or a heavy standard library.

No imports, no type labels, no setup. Every value is a 64-bit CPU word.

---

## Compiling & Running

For v0.01 / v1, we keep things simple and manual. No package manager or complex build tools. Just simple binaries doing their job.

All tools follow a clean `<input> <output>` convention. Output destinations are never hardcoded—you pass whatever path you want for both the intermediate `.safe` payload and the final executable (e.g. `./converter`, `bin/converter`, or `/tmp/converter`).

You can compile SINC programs either as single standalone files or as multi-file projects using a `build.staff` manifest.


### 1. Direct Compiler Invocation (Single File)
If you are compiling a single standalone file:

```bash
# 1. Compile source directly into a .safe machine code payload
./bin/sinc.elf converter.sinc converter.safe

# 2. Package the .safe payload into a standalone Linux ELF binary
./bin/packager_bin converter.safe ./converter
chmod +x ./converter

# 3. Run the binary
./converter
echo $?
# 3
```

In Linux, every program hands an exit code back to the parent shell. SINC takes the return value of `main!()` and passes it straight to the operating system in CPU register `rax`. When you check `echo $?`, you see the computed result: `3`.

### 2. Multi-File Project Workflow (STAFF Manifest)
For multi-file projects, SINC uses **STAFF** to read project manifests and build sources in memory. A project defines a simple `build.staff` manifest that lists dependencies and the target artifact:


```text
artifact my_app []

deps [
    steel/sys/sys.sinc;
]
```

To compile a project with STAFF:

```bash
# 1. Compile manifest to a .safe machine code payload
./bin/staff path/to/build.staff my_app.safe

# 2. Package into a standalone Linux ELF binary
./bin/packager_bin my_app.safe ./my_app
chmod +x ./my_app

# 3. Run it
./my_app
```

---

## Pure Functions vs. The `main!()` Entrypoint

You probably noticed that `to_hours` is declared as:
```sinc
fn to_hours(minutes) [ ... ]
```
While the entrypoint is declared with an exclamation mark:
```sinc
fn main!() [ ... ]
```

SINC enforces a strict separation between **pure** and **impure** code:
* **Pure functions (`fn`)**: Mathematical functions with zero side-effects. They take arguments, perform arithmetic or bitwise operations, and return a value. They cannot mutate external memory or perform I/O.
* **Impure functions (`fn ...!`)**: Functions that interact with the outside world, perform syscalls, or communicate with the operating system. Because `main` is the entrypoint that hands a process exit status to Linux, it is impure by definition.

---

## Brackets vs. Parentheses

SINC uses square brackets `[` and `]` for function bodies and control blocks instead of curly braces `{}`:

```sinc
fn main!() [
    ret 42;
]
```

Why square brackets? To keep the lexer and parser as simple and fast as possible. Using square brackets for blocks and round parentheses `()` for conditions and arguments allows the compiler to determine context with exactly one token of lookahead. This simplicity is why SINC compiles at over **1,000,000 lines per second** without complex parsing states.

