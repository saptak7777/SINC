#include <stdint.h>

int64_t bench_gemm_dot(void) {
    int64_t limit = 100000000;
    int64_t sum = 0;
    for (int64_t i = 0; i < limit; i++) {
        int64_t a = (i * 3 + 7) & 255;
        int64_t b = (i * 5 + 11) & 255;
        int64_t c = (i * 7 + 13) & 255;
        sum = sum + a * b + b * c;
    }
    return sum & 255;
}

int main(void) {
    return (int)bench_gemm_dot();
}
