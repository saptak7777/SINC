#include <stdio.h>
#include <stdint.h>
#include <assert.h>
extern int64_t sinc_fib(void);
int main(void) {
    int64_t val = sinc_fib();
    assert(val == 102334155LL);
    return 0;
}
