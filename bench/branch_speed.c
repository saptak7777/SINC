#include <stdint.h>

int64_t bench_run(void) {
    int64_t limit = 100000000;
    int64_t sum = 0;
    int64_t x = 1;
    for (int64_t idx = 0; idx < limit; idx++) {
        if ((x & 1) == 0) {
            sum = sum + 3;
        } else {
            sum = sum + 7;
        }
        x = x + idx + 1;
    }
    return sum;
}

int main(void) {
    return (int)(bench_run() & 255);
}
