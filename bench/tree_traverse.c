#include <stdint.h>

int64_t bench_tree_traverse(void) {
    int64_t limit = 100000000;
    int64_t acc = 0;
    int64_t curr = 1;
    for (int64_t i = 0; i < limit; i++) {
        int64_t left = (curr * 2) & 1023;
        int64_t right = (left + 1) & 1023;
        if ((curr & 1) == 0) {
            curr = left + 1;
        } else {
            curr = right + 2;
        }
        acc = acc + curr;
    }
    return acc & 255;
}

int main(void) {
    return (int)(bench_tree_traverse() & 255);
}
