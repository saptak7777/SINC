#include <stdint.h>

int64_t bench_bit_extract(void) {
    int64_t limit = 100000000;
    int64_t acc = 12345;
    int64_t mask = 63;
    for (int64_t idx = 0; idx < limit; idx++) {
        int64_t shift_amt = (idx & 7) + 1;
        int64_t t1 = acc << shift_amt;
        int64_t t2 = t1 >> shift_amt;
        int64_t sliced = (t2 >> 2) & mask;
        acc = acc + sliced + 1;
    }
    return acc;
}

int main(void) {
    return (int)(bench_bit_extract() & 255);
}
