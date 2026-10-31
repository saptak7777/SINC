#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SINC="$ROOT_DIR/bin/sinc.elf"
[ -x "$SINC" ] || SINC="$ROOT_DIR/sinc.elf"
PACKAGER_O="$ROOT_DIR/bin/packager_o"
[ -x "$PACKAGER_O" ] || PACKAGER_O="$ROOT_DIR/packager_o"
TMP_DIR="/tmp/sinc_ffi_test_$$"

mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "========================================================================="
echo "SINC <-> C FFI & ELF .o Integration Test Suite"
echo "========================================================================="

# -----------------------------------------------------------------------------
# Test Case 1: Zero-Argument Scalar Computation (Direct ABI Compatibility)
# -----------------------------------------------------------------------------
echo -n "[Test 1/5] Zero-Arg Scalar Function (Direct ABI match in %rax)... "

cat << 'EOF' > "$TMP_DIR/kernel_fib.sinc"
fn fib_fast() [
    a = 0;
    b = 1;
    loop (i:100 = 0 .. 40) [
        tmp = a + b;
        a = b;
        b = tmp;
    ]
    ret a;
]
EOF

"$SINC" "$TMP_DIR/kernel_fib.sinc" "$TMP_DIR/kernel_fib.safe"
"$PACKAGER_O" "$TMP_DIR/kernel_fib.safe" "$TMP_DIR/kernel_fib.o" "sinc_fib"

cat << 'EOF' > "$TMP_DIR/harness_1.c"
#include <stdio.h>
#include <stdint.h>
#include <assert.h>

extern int64_t sinc_fib(void);

int main(void) {
    int64_t val = sinc_fib();
    assert(val == 102334155LL);
    return 0;
}
EOF

gcc -O3 "$TMP_DIR/harness_1.c" "$TMP_DIR/kernel_fib.o" -no-pie -o "$TMP_DIR/app_1"
"$TMP_DIR/app_1"
echo "PASS (sinc_fib = 102334155)"

# -----------------------------------------------------------------------------
# Test Case 2: Multi-Argument Computation (SPINE ABI Parameter Bridge)
# -----------------------------------------------------------------------------
echo -n "[Test 2/5] Multi-Argument Math Kernel (SPINE ABI: %rcx, %rdx, %rbx)... "

cat << 'EOF' > "$TMP_DIR/kernel_poly.sinc"
fn poly3(a, b, c) [
    ret (a * a) + (b * c) + 42;
]
EOF

"$SINC" "$TMP_DIR/kernel_poly.sinc" "$TMP_DIR/kernel_poly.safe"
"$PACKAGER_O" "$TMP_DIR/kernel_poly.safe" "$TMP_DIR/kernel_poly.o" "sinc_poly3"

cat << 'EOF' > "$TMP_DIR/harness_2.c"
#include <stdio.h>
#include <stdint.h>
#include <assert.h>

extern void sinc_poly3(void);

static inline int64_t call_sinc_3(void *fn, int64_t a, int64_t b, int64_t c) {
    int64_t res;
    __asm__ volatile (
        "movq %1, %%rcx\n\t"
        "movq %2, %%rdx\n\t"
        "movq %3, %%rbx\n\t"
        "call *%4\n\t"
        "movq %%rax, %0\n\t"
        : "=r"(res)
        : "r"(a), "r"(b), "r"(c), "r"(fn)
        : "rax", "rcx", "rdx", "rbx", "rsi", "rdi", "r8", "r9", "r10", "r11", "memory"
    );
    return res;
}

int main(void) {
    // poly3(10, 20, 30) = (10*10) + (20*30) + 42 = 100 + 600 + 42 = 742
    int64_t val = call_sinc_3(sinc_poly3, 10, 20, 30);
    assert(val == 742);
    return 0;
}
EOF

gcc -O3 "$TMP_DIR/harness_2.c" "$TMP_DIR/kernel_poly.o" -no-pie -o "$TMP_DIR/app_2"
"$TMP_DIR/app_2"
echo "PASS (poly3(10, 20, 30) = 742)"

# -----------------------------------------------------------------------------
# Test Case 3: Zero-Copy Large Array Mutation (C Allocated Buffer Mutated by SINC)
# -----------------------------------------------------------------------------
echo -n "[Test 3/5] In-Place Large Array Mutation (1,000,000 C elements)... "

cat << 'EOF' > "$TMP_DIR/kernel_array.sinc"
fn transform_array!(buf, len, multiplier) [
    loop (i:10000000 = 0 .. len) [
        buf@[i] = buf@[i] * multiplier;
    ]
    ret len;
]
EOF

"$SINC" "$TMP_DIR/kernel_array.sinc" "$TMP_DIR/kernel_array.safe"
"$PACKAGER_O" "$TMP_DIR/kernel_array.safe" "$TMP_DIR/kernel_array.o" "sinc_transform_array"

cat << 'EOF' > "$TMP_DIR/harness_3.c"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <assert.h>

extern void sinc_transform_array(void);

static inline int64_t call_sinc_array(void *fn, int64_t *buf, int64_t len, int64_t mult) {
    int64_t res;
    __asm__ volatile (
        "movq %1, %%rcx\n\t"
        "movq %2, %%rdx\n\t"
        "movq %3, %%rbx\n\t"
        "call *%4\n\t"
        "movq %%rax, %0\n\t"
        : "=r"(res)
        : "r"(buf), "r"(len), "r"(mult), "r"(fn)
        : "rax", "rcx", "rdx", "rbx", "rsi", "rdi", "r8", "r9", "r10", "r11", "memory"
    );
    return res;
}

int main(void) {
    int64_t N = 1000000;
    int64_t *arr = (int64_t*)malloc(N * sizeof(int64_t));
    for (int64_t i = 0; i < N; i++) arr[i] = i + 1;

    int64_t count = call_sinc_array(sinc_transform_array, arr, N, 7);
    assert(count == N);

    // Verify samples
    assert(arr[0] == 7);
    assert(arr[10] == 77);
    assert(arr[999999] == 7000000);

    free(arr);
    return 0;
}
EOF

gcc -O3 "$TMP_DIR/harness_3.c" "$TMP_DIR/kernel_array.o" -no-pie -o "$TMP_DIR/app_3"
"$TMP_DIR/app_3"
echo "PASS (1,000,000 elements mutated in-place by SINC)"

# -----------------------------------------------------------------------------
# Test Case 4: Linking Multiple Distinct SINC Object Files Together with C
# -----------------------------------------------------------------------------
echo -n "[Test 4/5] Multi-Object Linking (Linking 2 distinct SINC .o with C)... "

cat << 'EOF' > "$TMP_DIR/mod_a.sinc"
fn compute_a(x) [
    ret x * 3;
]
EOF

cat << 'EOF' > "$TMP_DIR/mod_b.sinc"
fn compute_b(x) [
    ret x + 100;
]
EOF

"$SINC" "$TMP_DIR/mod_a.sinc" "$TMP_DIR/mod_a.safe"
"$PACKAGER_O" "$TMP_DIR/mod_a.safe" "$TMP_DIR/mod_a.o" "sinc_compute_a"

"$SINC" "$TMP_DIR/mod_b.sinc" "$TMP_DIR/mod_b.safe"
"$PACKAGER_O" "$TMP_DIR/mod_b.safe" "$TMP_DIR/mod_b.o" "sinc_compute_b"

cat << 'EOF' > "$TMP_DIR/harness_4.c"
#include <stdio.h>
#include <stdint.h>
#include <assert.h>

extern void sinc_compute_a(void);
extern void sinc_compute_b(void);

static inline int64_t call_sinc_1(void *fn, int64_t arg) {
    int64_t res;
    __asm__ volatile (
        "movq %1, %%rcx\n\t"
        "call *%2\n\t"
        "movq %%rax, %0\n\t"
        : "=r"(res)
        : "r"(arg), "r"(fn)
        : "rax", "rcx", "rdx", "rbx", "rsi", "rdi", "r8", "r9", "r10", "r11", "memory"
    );
    return res;
}

int main(void) {
    int64_t val_a = call_sinc_1(sinc_compute_a, 25);
    int64_t val_b = call_sinc_1(sinc_compute_b, val_a);
    // (25 * 3) + 100 = 75 + 100 = 175
    assert(val_b == 175);
    return 0;
}
EOF

gcc -O3 "$TMP_DIR/harness_4.c" "$TMP_DIR/mod_a.o" "$TMP_DIR/mod_b.o" -no-pie -o "$TMP_DIR/app_4"
"$TMP_DIR/app_4"
echo "PASS (Composition: compute_b(compute_a(25)) = 175)"

# -----------------------------------------------------------------------------
# Test Case 5: Complex AVX-512 Vectorized Loop Linked into C App
# -----------------------------------------------------------------------------
echo -n "[Test 5/5] AVX-512 Auto-Vectorized Kernel Linked into C Binary... "

"$SINC" "$ROOT_DIR/tests/native/avx512_eight_lane_reduction.sinc" "$TMP_DIR/vec_accum.safe"
"$PACKAGER_O" "$TMP_DIR/vec_accum.safe" "$TMP_DIR/vec_accum.o" "sinc_avx512_accum"

cat << 'EOF' > "$TMP_DIR/harness_5.c"
#include <stdio.h>
#include <stdint.h>
#include <assert.h>

extern int64_t sinc_avx512_accum(void);

int main(void) {
    int64_t res = sinc_avx512_accum();
    assert((res & 255) == 144);
    return 0;
}
EOF

gcc -O3 "$TMP_DIR/harness_5.c" "$TMP_DIR/vec_accum.o" -no-pie -o "$TMP_DIR/app_5"
"$TMP_DIR/app_5"
echo "PASS (AVX-512 8-lane reduction exit code 144 verified from C)"

echo "========================================================================="
echo "ALL 5 FFI INTEGRATION TESTS PASSED! SINC .o LINKING IS 100% WORKING!"
echo "========================================================================="
