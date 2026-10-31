#include <stdint.h>

static inline int64_t poly(int64_t x) {
    return x * x + 2 * x + 3;
}

int64_t bench_run(void) {
    int64_t limit = 100000000;
    int64_t sum = 0;
    int64_t x = 1;
    for (int64_t idx = 0; idx < limit; idx++) {
        sum = sum + poly(x);
        x = x + 1;
    }
    return sum;
}

int main(void) {
    return (int)(bench_run() & 255);
}
