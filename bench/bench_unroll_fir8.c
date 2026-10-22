#include <stdint.h>

int main(void) {
    int64_t limit = 5000000;
    int64_t acc = 0;
    for (int64_t sample = 0; sample < limit; sample++) {
        for (int64_t tap = 0; tap < 8; tap++) {
            int64_t term = tap * 5 + 3;
            acc = acc + term;
        }
    }
    return (int)(acc & 255);
}
