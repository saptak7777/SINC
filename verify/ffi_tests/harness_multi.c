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
    assert(val_b == 175);
    return 0;
}
