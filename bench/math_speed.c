#include <stdint.h>

int64_t bench_run(void) {
    int64_t limit = 100000000;
    int64_t sum = 0;
    for (int64_t idx = 0; idx < limit; idx++) {
        int64_t seed = idx;
        int64_t a = 1 + (seed & 7);
        int64_t b = 2 + (seed & 3);
        int64_t c = 3 + (seed & 1);
        sum = sum + (a + b) * c;
    }
    return sum;
}

int main(void) {
    return (int)(bench_run() & 255);
}
