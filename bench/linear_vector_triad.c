#include <stdint.h>
#include <sys/mman.h>

int64_t bench_linear_triad(void) {
    int64_t *arena = (int64_t *)mmap(0, 196608, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int64_t *a = arena;
    int64_t *b = arena + 8192;
    int64_t *c = arena + 16384;

    for (int64_t i = 0; i < 8192; i++) {
        a[i] = 0;
        b[i] = i & 255;
        c[i] = (i * 2) & 255;
    }

    int64_t steps = 5000;
    for (int64_t step = 0; step < steps; step++) {
        for (int64_t i = 0; i < 8192; i++) {
            a[i] = (a[i] + b[i] + c[i] * 3) & 255;
        }
    }

    int64_t checksum = a[0] + a[8191];
    return checksum & 255;
}

int main(void) {
    return (int)bench_linear_triad();
}
