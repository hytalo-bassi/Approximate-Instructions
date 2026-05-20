/**
 * @file main.c
 * @brief Benchmark and demonstration of switchable exact vs. approximate arithmetic.
 *
 * This program exercises add from the OpSet abstraction
 * in switcher.h, running a configurable number of iterations so you can compare
 * the performance and numerical accuracy of exact vs. approximate hardware ops.
 * 
 * Obs: this test is terrible for the approximate addx, since it eventually computes x~+x that gives
 * 0, so even numbers of successive additions always turn to 0.
 * Usage:
 *   ./main [-x] [-n <iterations>] [-v]
 *
 *   -x            Enable approximate arithmetic (uses approx ops from instructions.h)
 *   -n <count>    Number of loop iterations (default: 1,000,000)
 *   -v            Verbose mode: print result of each operation type
 *
 * Example:
 *   ./main              # exact arithmetic, 1M iterations
 *   ./main -x           # approximate arithmetic, 1M iterations
 *   ./main -x -n 500 -v # approximate, 500 iterations, verbose output
 */

#include "../utils/switcher.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* -------------------------------------------------------------------------
 * Constants & defaults
 * ---------------------------------------------------------------------- */

#define DEFAULT_ITERATIONS 1000000
#define DEFAULT_A          10
#define DEFAULT_B           5

/* -------------------------------------------------------------------------
 * Helpers
 * ---------------------------------------------------------------------- */

/**
 * Print usage instructions to stderr and exit with a non-zero code.
 * @param prog  argv[0], the program name shown in the help text.
 */
static void usage(const char *prog)
{
    fprintf(stderr,
        "Usage: %s [-x] [-n <iterations>] [-v]\n"
        "\n"
        "  -x            Use approximate arithmetic (default: exact)\n"
        "  -n <count>    Iteration count (default: %d)\n"
        "  -v            Verbose: print per-operation results\n",
        prog, DEFAULT_ITERATIONS);
    exit(EXIT_FAILURE);
}

/**
 * Parse a positive integer from a string, exiting on failure.
 * @param s     The string to parse.
 * @param dest  Pointer to the int that receives the parsed value.
 */
static void parse_positive_int(const char *s, int *dest)
{
    char *end;
    long val = strtol(s, &end, 10);
    if (*end != '\0' || val <= 0) {
        fprintf(stderr, "Error: expected a positive integer, got \"%s\"\n", s);
        exit(EXIT_FAILURE);
    }
    *dest = (int)val;
}

/* -------------------------------------------------------------------------
 * Benchmark runner
 * ---------------------------------------------------------------------- */

/**
 * Run a single operation in a tight loop and return the accumulated result.
 *
 * This isolates the hot path so the compiler cannot hoist the ops->fn
 * call out of the loop, giving a meaningful cycle count.
 *
 * @param fn         The binary integer operation to benchmark.
 * @param a          Left operand (held constant each iteration).
 * @param b          Right operand (held constant each iteration).
 * @param iters      Number of iterations.
 * @param elapsed_s  Output: wall-clock seconds taken (may be NULL).
 * @return           Accumulated result after all iterations.
 */
static int run_benchmark(op_fn fn, int a, int b, int iters, double *elapsed_s)
{
    int accumulator = 0;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    for (int i = 0; i < iters; i++) {
        /* Accumulate so the compiler cannot dead-code the loop body. */
        accumulator = fn(fn(a, b), accumulator)+1;
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);

    if (elapsed_s) {
        *elapsed_s = (t1.tv_sec  - t0.tv_sec)
                   + (t1.tv_nsec - t0.tv_nsec) * 1e-9;
    }

    return accumulator;
}

/* -------------------------------------------------------------------------
 * Entry point
 * ---------------------------------------------------------------------- */

/**
 * @note  The standard C signature is `int main(int argc, char *argv[])`.
 *        The original code had the arguments swapped — corrected here.
 */
int main(int argc, char *argv[])
{
    /* --- Parse command-line arguments ---------------------------------- */
    bool approximate = false;
    bool verbose      = false;
    int  iterations   = DEFAULT_ITERATIONS;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-x") == 0) {
            approximate = true;
        } else if (strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (strcmp(argv[i], "-n") == 0) {
            if (++i >= argc) {
                fprintf(stderr, "Error: -n requires an argument\n");
                usage(argv[0]);
            }
            parse_positive_int(argv[i], &iterations);
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            usage(argv[0]);
        }
    }

    /* --- Select operation set ------------------------------------------ */
    const OpSet *ops = get_ops(approximate);

    printf("Mode      : %s\n", approximate ? "approximate" : "exact");
    printf("Iterations: %d\n", iterations);
    printf("Operands  : a=%d, b=%d\n\n", DEFAULT_A, DEFAULT_B);

    /* --- Benchmark add only --------------------------------------------- */
    double elapsed = 0.0;
    int    result  = run_benchmark(ops->add, DEFAULT_A, DEFAULT_B,
                                   iterations, &elapsed);

    printf("add : result = %11d  |  time = %.4f s  |  throughput = %.2f Mops/s\n",
           result, elapsed, (iterations / 1e6) / elapsed);

    if (verbose) {
        /* Show a single-shot result so the user can eyeball correctness. */
        int single = ops->add(DEFAULT_A, DEFAULT_B);
        printf("      single-shot %d + %d = %d\n", DEFAULT_A, DEFAULT_B, single);
    }

    return EXIT_SUCCESS;
}