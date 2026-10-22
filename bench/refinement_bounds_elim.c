#include <stdint.h>
#include <sys/mman.h>

int64_t bench_refinement_bounds(void) {
    int64_t limit = 50000000;
    int64_t *table = (int64_t *)mmap(0, 64, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    for (int64_t i = 0; i < 8; i++) {
        table[i] = i * 7 + 3;
    }

    int64_t sum = 0;
    for (int64_t k = 0; k < limit; k++) {
        int64_t idx = k & 7;
        sum = sum + table[idx];
    }

    return sum & 255;
}

int main(void) {
    return (int)bench_refinement_bounds();
}
