#include <stdint.h>

int64_t bench_magic_bitboard(void) {
    int64_t limit = 50000000;
    uint64_t occ = 12345678901234567ULL;
    int64_t moves = 0;
    for (int64_t i = 0; i < limit; i++) {
        uint64_t blockers = occ & 72340172838076673ULL;
        uint64_t idx = ((blockers * 35184372088832ULL) >> 56) & 63;
        moves = moves + (idx ^ (occ & 255)) + ((occ >> 12) & 15);
        occ = occ + 1000000007ULL;
    }
    return moves & 255;
}

int main(void) {
    return (int)bench_magic_bitboard();
}
