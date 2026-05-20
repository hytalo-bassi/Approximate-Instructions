#include "../utils/instructions.h"

int main() {
    int a = 10, b = 5;

    int sum  = addx(a, b);
    int diff = subx(a, b);
    int prod = mulx(a, b);
    int quot = divx(a, b);

    return 0;
}