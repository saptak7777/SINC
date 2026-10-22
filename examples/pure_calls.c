#include <math.h>

double main_func() {
    double x = 1.0;
    double s = sin(x);
    double c = cos(x);
    return s * s + c * c;
}

int main() {
    main_func();
    return 0;
}
