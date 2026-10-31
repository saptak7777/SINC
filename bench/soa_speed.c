#include <stdint.h>
#include <sys/mman.h>

int64_t bench_soa(void) {
    int64_t *arena = (int64_t*)mmap(0, 262144, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int64_t *pos_x = arena;
    int64_t *vel_x = arena + (65536 / 8);
    int64_t *pos_y = arena + (131072 / 8);
    int64_t *vel_y = arena + (196608 / 8);

    for (int64_t i = 0; i < 8192; i++) {
        pos_x[i] = i;
        vel_x[i] = 1;
        pos_y[i] = i * 2;
        vel_y[i] = 2;
    }

    for (int64_t step = 0; step < 5000; step++) {
        for (int64_t i = 0; i < 8192; i++) {
            pos_x[i] = pos_x[i] + vel_x[i];
            pos_y[i] = pos_y[i] + vel_y[i];
        }
    }

    int64_t checksum = pos_x[0] + pos_x[8191] + pos_y[0] + pos_y[8191];
    return checksum;
}

int main(void) {
    return (int)(bench_soa() & 255);
}
