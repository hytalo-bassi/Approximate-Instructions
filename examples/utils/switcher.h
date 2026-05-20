#ifndef SWITCHER_H
#define SWITCHER_H
#include "instructions.h"

typedef int (*op_fn)(int, int);

// Exact operations
int exact_add(int x, int y)  { return x + y; }
int exact_sub(int x, int y)  { return x - y; }
int exact_mul(int x, int y)  { return x * y; }

// Approximate operations
int approx_add(int x, int y) { return addx(x, y); }
int approx_sub(int x, int y) { return subx(x, y); }
int approx_mul(int x, int y) { return mulx(x, y); }

typedef struct {
    op_fn add, sub, mul;
} OpSet;

static const OpSet EXACT  = { exact_add,  exact_sub,  exact_mul  };
static const OpSet APPROX = { approx_add, approx_sub, approx_mul };

static inline const OpSet* get_ops(bool approximate) {
    return approximate ? &APPROX : &EXACT;
}

#endif