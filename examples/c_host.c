// examples/c_host.c
// Demonstrates calling a compiled SINC function (.o) from C

#include <stdio.h>
#include <stdint.h>

// SINC zero-argument functions return their result directly in %rax
extern int64_t sinc_math(void);

int main(void) {
    int64_t result = sinc_math();
    printf("Computed in SINC: %ld\n", result);
    return 0;
}
