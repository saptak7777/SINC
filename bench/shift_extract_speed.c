#include <stdint.h>

int64_t bench_shift_extract(void) {
    int64_t limit = 100000000;
    int64_t sum = 0;
    for (int64_t idx = 0; idx < limit; idx++) {
        int64_t shift_amt = (idx & 7) + 1;
        int64_t t1 = sum << shift_amt;
        int64_t t2 = t1 >> shift_amt;
        sum = sum + ((t2 >> 2) & 63) + 1;
    }
    return sum;
}

int main(void) {
    return (int)(bench_shift_extract() & 255);
}
