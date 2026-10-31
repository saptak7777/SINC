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
    int64_t val = call_sinc_3(sinc_poly3, 10, 20, 30);
    assert(val == 742);
    return 0;
}
