#include <stdint.h>

int64_t scalar_reference(int64_t a, int64_t b) {
    return ((a + b * 2) - 5) / 3;
}

int main(void) {
    return (int)scalar_reference(12, 6);
}
