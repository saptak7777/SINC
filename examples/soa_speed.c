#include <stdint.h>

#define N 4096

double bench_run(double* x, double* y) {
    double sum = 0.0;
    int64_t i = 0;
    const double dt = 0.000001;

    while (i < 100000000) {
        int64_t idx = i & (N - 1);
        double xv = x[idx];
        double yv = y[idx];
        double nx = xv + yv * dt;
        double ny = yv + xv * dt;
        x[idx] = nx;
        y[idx] = ny;
        sum += nx;
        i += 1;
    }

    return sum;
}

