#include <stdint.h>
#include <sys/mman.h>

int64_t bench_dram_stream(void) {
    int64_t *arena = (int64_t *)mmap(0, 16777216, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int64_t *a = arena;
    int64_t *b = arena + 1048576;

    for (int64_t i = 0; i < 1048576; i++) {
        a[i] = 1;
        b[i] = 2;
    }

    int64_t steps = 20;
    for (int64_t step = 0; step < steps; step++) {
        for (int64_t i = 0; i < 1048576; i++) {
            a[i] = a[i] + b[i] * 3;
        }
    }

    return a[0] & 255;
}

int main(void) {
    return (int)bench_dram_stream();
}
