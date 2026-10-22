long long bench_run() {
    long long sum = 0;
    long long i = 0;
    while (i < 100000000) {
        volatile long long seed = i;
        long long a = 1 + (seed & 7);
        long long b = 2 + (seed & 3);
        long long c = 3 + (seed & 1);
        sum = sum + (a + b) * c;
        i = i + 1;
    }
    return sum;
}
