#include <stdint.h>
#include <sys/mman.h>

int64_t bench_multi_loop(void) {
    int64_t *buf = (int64_t *)mmap(0, 65536, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);

    for (int64_t i = 0; i < 8192; i++) {
        buf[i] = (i * 3 + 1) & 255;
    }

    for (int64_t i = 0; i < 8192; i++) {
        int64_t val = buf[i];
        buf[i] = (val * 5 + 7) & 255;
    }

    int64_t outer = 10000;
    int64_t sum = 0;
    for (int64_t k = 0; k < outer; k++) {
        for (int64_t i = 0; i < 8192; i++) {
            sum = sum + buf[i];
        }
    }

    return sum & 255;
}

int main(void) {
    return (int)bench_multi_loop();
}
