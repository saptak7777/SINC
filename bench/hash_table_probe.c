#include <stdint.h>
#include <sys/mman.h>

int64_t bench_hash_probe(void) {
    int64_t *table = (int64_t *)mmap(0, 524288, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);

    for (int64_t i = 0; i < 65536; i++) {
        table[i] = (i * 2654435761LL) & 65535;
    }

    int64_t hits = 0;
    int64_t queries = 2000000;
    for (int64_t q = 0; q < queries; q++) {
        int64_t key = (q * 1103515245 + 12345) & 65535;
        int64_t idx = key;
        for (int64_t step = 0; step < 8; step++) {
            int64_t curr = table[idx];
            if (curr == key) {
                hits = hits + 1;
            }
            idx = (idx + step * 2 + 1) & 65535;
        }
    }

    return hits & 255;
}

int main(void) {
    return (int)bench_hash_probe();
}
