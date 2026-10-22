#include <stdio.h>
#include <stdint.h>
#include <assert.h>
extern int64_t sinc_avx512_accum(void);
int main(void) {
    int64_t res = sinc_avx512_accum();
    assert((res & 255) == 144);
    return 0;
}
