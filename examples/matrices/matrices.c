#include <stdio.h>

int main() {
    int a = 10, b = 20, res = 0;
    
    // --- Initialization Code ---
    // (Prepare arrays, images, etc.)

    // Reset statistics before the kernel
    m5_reset_stats(0, 0); 

    res = addx(a, b);

    // Dump statistics immediately after the kernel
    m5_dump_stats(0, 0); 

    return 0;
}