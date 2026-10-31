long long bench_run() {
    volatile long long limit = 100000000;
    long long sum = 0;
    long long i = 0;
    long long x = 1;
    while (i < limit) {
        if ((x & 1) == 0) {
            sum = sum + 3;
        } else {
            sum = sum + 7;
        }
        x = x + i + 1;
        i = i + 1;
    }
    return sum;
}
