double poly(double x) {
    return x * x + 2.0 * x + 3.0;
}

double bench_run() {
    double sum = 0.0;
    double x = 1.0;
    long long i = 0;
    while (i < 10) {
        sum = sum + poly(x);
        x = x + 1.0;
        i = i + 1;
    }
    return sum;
}

int old_main() {
    bench_run();
    return 0;
}
