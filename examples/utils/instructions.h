#ifndef APPROX_INSTRUCTIONS_H
#define APPROX_INSTRUCTIONS_H

/* ============================================================
 * Integer approximate instructions
 * ============================================================ */
static inline int mulx(int a, int b) {
    int result;
    asm volatile (
        "mulx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

static inline int addx(int a, int b) {
    int result;
    asm volatile (
        "addx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

static inline int subx(int a, int b) {
    int result;
    asm volatile (
        "subx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

static inline int divx(int a, int b) {
    int result;
    asm volatile (
        "divx %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

/* ============================================================
 * Integer exact instructions (for comparison against approximate)
 * ============================================================ */
static inline int mul(int a, int b) {
    int result;
    asm volatile (
        "mul %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

static inline int add(int a, int b) {
    int result;
    asm volatile (
        "add %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

static inline int sub(int a, int b) {
    int result;
    asm volatile (
        "sub %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

static inline int divi(int a, int b) {
    int result;
    asm volatile (
        "div %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    return result;
}

/* ============================================================
 * Floating-point approximate instructions
 * ============================================================ */
static inline float faddx(float a, float b) {
    float result;
    asm volatile (
        "faddx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

static inline float fsubx(float a, float b) {
    float result;
    asm volatile (
        "fsubx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

static inline float fmulx(float a, float b) {
    float result;
    asm volatile (
        "fmulx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

static inline float fdivx(float a, float b) {
    float result;
    asm volatile (
        "fdivx.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

/* ============================================================
 * Floating-point exact instructions (for comparison against approximate)
 * ============================================================ */
static inline float fadd(float a, float b) {
    float result;
    asm volatile (
        "fadd.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

static inline float fsub(float a, float b) {
    float result;
    asm volatile (
        "fsub.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

static inline double fmul(double a, double b) {
    double result;
    asm volatile (
        "fmul.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

static inline double fdiv(double a, double b) {
    double result;
    asm volatile (
        "fdiv.s %[z], %[x], %[y]\n\t"
        : [z] "=f" (result)
        : [x] "f" (a), [y] "f" (b)
    );
    return result;
}

#endif // APPROX_INSTRUCTIONS_H