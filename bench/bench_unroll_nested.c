#include <stdint.h>

int main(void) {
    int64_t limit = 10000000;
    int64_t sum = 0;
    for (int64_t outer = 0; outer < limit; outer++) {
        for (int64_t k = 0; k < 4; k++) {
            sum = sum + k * 3 + 1;
        }
    }
    return (int)(sum & 255);
}
