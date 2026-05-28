#include "../utils/instructions.h"

int main() {
    int a = 10, b = 5;

    int sum  = addx(a, b);
    int diff = subx(a, b);
    int prod = mulx(a, b);
    int quot = divx(a, b);

    double fa = 10.0, fb = 5.0;
    double fsum  = faddx(fa, fb);
    double fdiff = fsubx(fa, fb);
    double fprod = fmulx(fa, fb);
    double fquot = fdivx(fa, fb);
    
    return 0;
}