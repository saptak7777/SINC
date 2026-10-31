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
    assert(arr[0] == 7);
    assert(arr[10] == 77);
    assert(arr[999999] == 7000000);
    free(arr);
    return 0;
}
