#include <math.h>

double bench_run() {
    double sum = 0.0;
    long long i = 0;
    double x = 1.0;
    while (i < 100000000) {
        double s = sin(x);
        double c = cos(x);
        sum = sum + (s * s + c * c);
        i = i + 1;
    }
    return sum;
}
