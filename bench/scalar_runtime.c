#include <stdint.h>

int main(int argc, char **argv) {
    int64_t limit = 10000000 + (argc > 100);
    int64_t acc = 1;
    for (int64_t i = 0; i < limit; i++) {
        acc = acc + i * 2 - i;
    }
    return (int)(acc & 255);
}
