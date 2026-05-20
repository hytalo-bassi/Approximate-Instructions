#!/usr/bin/env bash
###
### Facilitator script that tests the multiple adds example.
### It receives the number of iteractions as a required argument, and then the CPU type like
### AtomicSimpleCPU, TimingSimpleCPU, O3CPU, etc. as an optional argument
### (default is AtomicSimpleCPU). Then it runs multiple times the same script with different options
### and sends the stats to the outdir multiple_adds_example/<exact or approximate>/<CPU_type>/<iteractions>/. It runs the
### gem5 with something like:
### $GEM5_DIR/RISCV/gem5.fast \
###     $GEM5_DIR/configs/deprecated/example/se.py -c benchmark.out \
###     --options="-n <number of iteractions> [-x if approximate]" \
###     --cpu-type=<CPU type> [... options required for the cpu]
### It starts the interactions with 1, then multiplies by 10 until it reaches the number 1000000, it
### also switches between exact and approximate between each interaction. For example, it runs the first
### iteaction with 1 exact iteration, then 1 approximate iteraction, then 10 exact iteractions and so on.
### After all the iteractions have been made, it should change the CPU type and repeat the process.

set -euo pipefail

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    echo "Usage: $0 <max_iterations> [CPU_type [CPU_type2 ...]]"
    echo ""
    echo "  max_iterations   Maximum number of iterations to simulate (e.g. 1000000)."
    echo "                   Must be a power of 10 between 1 and 1000000."
    echo "  CPU_type         One or more gem5 CPU types (default: AtomicSimpleCPU)."
    echo "                   Examples: AtomicSimpleCPU TimingSimpleCPU O3CPU MinorCPU"
    echo ""
    echo "Environment variables:"
    echo "  GEM5_DIR         Path to gem5 directory (required)."
    echo "  BENCHMARK        Path to the benchmark binary (default: benchmark.out)."
    exit 1
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    echo "Error: max_iterations is required." >&2
    usage
fi

MAX_ITERATIONS="$1"
shift

# Validate max_iterations is a positive integer
if ! [[ "$MAX_ITERATIONS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: max_iterations must be a positive integer, got: '$MAX_ITERATIONS'" >&2
    usage
fi

# Collect CPU types (remaining arguments, or default)
if [[ $# -ge 1 ]]; then
    CPU_TYPES=("$@")
else
    CPU_TYPES=("AtomicSimpleCPU")
fi

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
if [[ -z "${GEM5_DIR:-}" ]]; then
    echo "Error: GEM5_DIR environment variable is not set." >&2
    exit 1
fi

GEM5_BIN="${GEM5_DIR}/build/RISCV/gem5.fast"
GEM5_CFG="${GEM5_DIR}/configs/deprecated/example/se.py"
BENCHMARK="${BENCHMARK:-benchmark.out}"

if [[ ! -x "$GEM5_BIN" ]]; then
    echo "Error: gem5 binary not found or not executable: $GEM5_BIN" >&2
    exit 1
fi

if [[ ! -f "$GEM5_CFG" ]]; then
    echo "Error: gem5 config script not found: $GEM5_CFG" >&2
    exit 1
fi

if [[ ! -f "$BENCHMARK" ]]; then
    echo "Error: benchmark binary not found: $BENCHMARK" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# CPU-specific extra options
# ---------------------------------------------------------------------------
cpu_extra_options() {
    local cpu_type="$1"
    case "$cpu_type" in
        O3CPU)
            echo "--caches --l2cache"
            ;;
        MinorCPU)
            echo "--caches"
            ;;
        TimingSimpleCPU)
            echo "--caches"
            ;;
        AtomicSimpleCPU)
            echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Helper: run a single gem5 simulation
# ---------------------------------------------------------------------------
run_gem5() {
    local cpu_type="$1"
    local iterations="$2"
    local mode="$3"          # "exact" or "approximate"

    local outdir="multiple_adds_example/${mode}/${cpu_type}/${iterations}"
    mkdir -p "$outdir"

    # Build --options string
    local benchmark_opts="-n ${iterations}"
    if [[ "$mode" == "approximate" ]]; then
        benchmark_opts="${benchmark_opts} -x"
    fi

    # Extra CPU-specific flags
    local extra_opts
    extra_opts="$(cpu_extra_options "$cpu_type")"

    echo "------------------------------------------------------------"
    echo "  CPU:        $cpu_type"
    echo "  Iterations: $iterations"
    echo "  Mode:       $mode"
    echo "  Output dir: $outdir"
    echo "------------------------------------------------------------"

    # shellcheck disable=SC2086
    "$GEM5_BIN" \
        --outdir="$outdir" \
        "$GEM5_CFG" \
        -c "$BENCHMARK" \
        --options="$benchmark_opts" \
        --cpu-type="$cpu_type" \
        $extra_opts

    echo "Done: $outdir"
    echo ""
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
for cpu_type in "${CPU_TYPES[@]}"; do
    echo "============================================================"
    echo "  Starting CPU type: $cpu_type"
    echo "============================================================"

    n=1
    while [[ $n -le $MAX_ITERATIONS ]]; do
        run_gem5 "$cpu_type" "$n" "exact"
        run_gem5 "$cpu_type" "$n" "approximate"
        n=$(( n * 10 ))
    done

    echo "============================================================"
    echo "  Finished CPU type: $cpu_type"
    echo "============================================================"
    echo ""
done

echo "All simulations completed."