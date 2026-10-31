#include <stdint.h>

int64_t bench_branchless_filter(void) {
    int64_t limit = 100000000;
    int64_t acc = 0;
    int64_t seed = 1234567;
    for (int64_t i = 0; i < limit; i++) {
        seed = (seed * 1103515245 + 12345) & 2147483647;
        int64_t val = (seed >> 16) & 255;
        if (val > 127) {
            acc = acc + val;
        }
    }
    return acc & 255;
}

int main(void) {
    return (int)bench_branchless_filter();
}
