#include <stdint.h>

static inline int64_t pure_transform(int64_t c) {
    int64_t t1 = c * 1103515245 + 12345;
    return (t1 >> 16) & 65535;
}

int64_t bench_pure_licm(void) {
    int64_t limit = 50000000;
    int64_t sum = 0;
    int64_t k = 42;
    for (int64_t i = 0; i < limit; i++) {
        int64_t invariant_val = pure_transform(k);
        int64_t dynamic_val = pure_transform(i & 255);
        sum = sum + invariant_val + dynamic_val;
    }
    return sum & 255;
}

int main(void) {
    return (int)bench_pure_licm();
}
