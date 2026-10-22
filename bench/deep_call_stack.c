#include <stdint.h>

static inline int64_t leaf(int64_t a, int64_t b) {
    return (a * 3 + b * 5 + 7) & 65535;
}

static inline int64_t mid2(int64_t a, int64_t b, int64_t c) {
    int64_t l1 = leaf(a, b);
    int64_t l2 = leaf(b, c);
    return (l1 ^ l2) + 11;
}

static inline int64_t mid1(int64_t a, int64_t b, int64_t c, int64_t d) {
    int64_t m1 = mid2(a, b, c);
    int64_t m2 = mid2(b, c, d);
    return (m1 + m2 * 3) & 65535;
}

int64_t bench_deep_call(void) {
    int64_t limit = 5000003;
    int64_t sum = 0;
    for (int64_t i = 0; i < limit; i++) {
        int64_t x = i & 255;
        int64_t r = mid1(x, x + 1, x + 2, x + 3);
        sum = sum + r;
    }
    return sum & 255;
}

int main(void) {
    return (int)bench_deep_call();
}
