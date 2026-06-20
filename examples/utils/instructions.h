#ifndef APPROX_INSTRUCTIONS_H
#define APPROX_INSTRUCTIONS_H

/* Integer approximate instructions */
static inline int mulx(int a, int b) {
    int result;
    asm volatile (
        "mulx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r"  (a), [y] "r" (b)
    );
    return result;
}

static inline int addx(int a, int b) {
    int result;
    asm volatile (
        "addx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r"  (a), [y] "r" (b)
    );
    return result;
}

static inline int subx(int a, int b) {
    int result;
    asm volatile (
        "subx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r"  (a), [y] "r" (b)
    );
    return result;
}

static inline int divx(int a, int b) {
    int result;
    asm volatile (
        "divx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r"  (a), [y] "r" (b)
    );
    return result;
}

/* Floating-point approximate instructions */
static inline float faddx(float a, float b) {
    float result;
    asm volatile (
        "faddx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f"  (a), [y] "f" (b)
    );
    return result;
}

static inline double fsubx(double a, double b) {
    double result;
    asm volatile (
        "fsubx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f"  (a), [y] "f" (b)
    );
    return result;
}

static inline double fmulx(double a, double b) {
    double result;
    asm volatile (
        "fmulx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f"  (a), [y] "f" (b)
    );
    return result;
}

static inline double fdivx(double a, double b) {
    double result;
    asm volatile (
        "fdivx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f"  (a), [y] "f" (b)
    );
    return result;
}

#endif // APPROX_INSTRUCTIONS_H