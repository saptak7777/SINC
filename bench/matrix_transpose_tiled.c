#include <stdint.h>
#include <sys/mman.h>

int64_t bench_matrix_tiled(void) {
    int64_t *arena = (int64_t *)mmap(0, 1048576, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int64_t *mat_a = arena;
    int64_t *mat_b = arena + 65536;

    for (int64_t i = 0; i < 256; i++) {
        for (int64_t j = 0; j < 256; j++) {
            int64_t idx = i * 256 + j;
            mat_a[idx] = (i * 3 + j * 7) & 255;
        }
    }

    int64_t passes = 50;
    for (int64_t pass = 0; pass < passes; pass++) {
        for (int64_t ti = 0; ti < 16; ti++) {
            for (int64_t tj = 0; tj < 16; tj++) {
                for (int64_t i = 0; i < 16; i++) {
                    for (int64_t j = 0; j < 16; j++) {
                        int64_t row = ti * 16 + i;
                        int64_t col = tj * 16 + j;
                        int64_t src_idx = row * 256 + col;
                        int64_t dst_idx = col * 256 + row;
                        mat_b[dst_idx] = (mat_a[src_idx] + pass) & 255;
                    }
                }
            }
        }
    }

    int64_t checksum = mat_b[0] + mat_b[255] + mat_b[65535];
    return checksum & 255;
}

int main(void) {
    return (int)bench_matrix_tiled();
}
