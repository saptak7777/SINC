#include <stdint.h>

static inline int64_t pure_hash(int64_t x) {
    return ((x * 1103515245 + 12345) >> 16) & 65535;
}

int64_t bench_pure(void) {
    int64_t limit = 100000000;
    int64_t sum = 0;
    for (int64_t idx = 0; idx < limit; idx++) {
        int64_t h1 = pure_hash(idx & 1023);
        int64_t h2 = pure_hash(idx & 1023);
        sum = sum + (h1 ^ h2) + h1;
    }
    return sum;
}

int main(void) {
    return (int)(bench_pure() & 255);
}
