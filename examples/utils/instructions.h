#ifndef APPROX_INSTRUCTIONS_H
#define APPROX_INSTRUCTIONS_H

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

#endif // APPROX_INSTRUCTIONS_H