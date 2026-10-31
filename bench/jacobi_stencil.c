#include <stdint.h>

int64_t bench_jacobi_stencil(void) {
    int64_t limit = 50000000;
    int64_t acc = 0;
    int64_t u = 10, d = 20, l = 30, r = 40, f = 50, b = 60;
    for (int64_t step = 0; step < limit; step++) {
        int64_t center = (u + d + l + r + f + b) >> 3;
        acc = acc + center;
        u = (d + 1) & 255;
        d = (l + 2) & 255;
        l = (r + 3) & 255;
        r = (f + 4) & 255;
        f = (b + 5) & 255;
        b = (center + 6) & 255;
    }
    return acc & 255;
}

int main(void) {
    return (int)bench_jacobi_stencil();
}
