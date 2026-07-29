#!/usr/bin/env python3
"""
run_batch.py

Compiles every source file in a folder with riscv64-unknown-linux-musl-gcc
and runs each resulting binary through GEM5 (power-run.py), collecting
per-file energy stats into a single consolidated CSV.

Usage:
    python3 run_batch.py --gem5_path gem5.fast --clock 1GHz --folder ./benchmarks \
        --watch ema,alpha

Flags:
    --gem5_path  Path/name of the GEM5 executable to invoke (e.g. gem5.fast, or
                 /path/to/build/RISCV/gem5.fast)
    --clock   CPU clock frequency to pass to the GEM5 config script (e.g. 1GHz)
    --folder  Folder containing the source files (.c) to compile and run
    -w, --watch  Comma-separated list of metadata keys to watch. Each key is
                 read out of the report JSON produced by the benchmark itself
                 (via common_api_output) and recorded as its own column in
                 the consolidated summary CSV, alongside a column identifying
                 which source file it came from.

For each source file <name>.c found in --folder, this script will:
  1. Compile:
       riscv64-unknown-linux-musl-gcc -O0 -static <name>.c -o <name>.c.out
  2. Run:
       <gem5_path> configs/power-run.py <name>.c.out
            --clock <clock> -c <name>.c.out

     power-run.py's -c/--cmd flag is passed straight through as the
     simulated binary's own argv[1] (it does NOT create a gem5-side sample
     file). So the benchmark itself receives <name>.c.out as its filename
     argument and, via common_api_output(), writes its own JSON report to
     <name>.c.out.json alongside the binary.

     GEM5's stdout is captured (and still echoed to the terminal) so the
     "ENERGY REPORT" summary footer can be parsed. The three summary
     values (total dynamic execution time, total energy consumed, and
     average dynamic power) for EVERY file are collected and written, at
     the end of the run, to a single consolidated CSV: <folder>/energy-summary.csv
     (one row per source file). If --watch/-w is given, the requested
     metadata keys are read out of <name>.c.out.json and added as extra
     columns in that same row.

Results (compiled binaries, per-benchmark JSON reports, and the
consolidated energy summary CSV) are left alongside the source files in
--folder.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

COMPILER = "riscv64-unknown-linux-musl-gcc"
GEM5_CONFIG = "configs/power-run.py"

# Extensions considered as "source files" to compile. Adjust if needed.
SOURCE_EXTENSIONS = {".c"}

# Name of the single consolidated CSV written at the end of the run.
SUMMARY_CSV_NAME = "energy-summary.csv"

# Regexes to pull the summary lines out of the ENERGY REPORT footer, e.g.:
#   Total dynamic execution time: 5.090000000e-07 s
#   Total energy consumed:        2.557951521e-06 J
#   Average power (dynamic):      5.025445 W
FLOAT_RE = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
TIME_RE = re.compile(r"Total dynamic execution time:\s*" + FLOAT_RE)
ENERGY_RE = re.compile(r"Total energy consumed:\s*" + FLOAT_RE)
POWER_RE = re.compile(r"Average power \(dynamic\):\s*" + FLOAT_RE)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compile and run a folder of RISC-V benchmarks under GEM5."
    )
    parser.add_argument(
        "--gem5_path",
        required=True,
        help="GEM5 executable to invoke (e.g. gem5.fast or full path to it).",
    )
    parser.add_argument(
        "--clock",
        required=True,
        help="Clock frequency to pass to the GEM5 config script (e.g. 1GHz).",
    )

    parser.add_argument(
        "--folder",
        required=True,
        type=Path,
        help="Folder containing source files to compile and run.",
    )
    parser.add_argument(
        "-w", "--watch",
        default="",
        help="Comma-separated list of metadata keys to watch and record from "
             "each benchmark's own JSON report (e.g. 'ema,alpha').",
    )
    return parser.parse_args()


def run_step(cmd_list, description, capture=False):
    """Run a subprocess command, streaming/capturing output, and raise on failure.

    If capture=True, stdout is captured to a string (and still printed to the
    terminal as it arrives) so it can be parsed afterwards. Returns the
    captured stdout text (or "" if capture=False).
    """
    print(f"    -> {description}")
    print(f"       $ {' '.join(str(c) for c in cmd_list)}")

    if not capture:
        result = subprocess.run(cmd_list)
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}: "
                f"{' '.join(str(c) for c in cmd_list)}"
            )
        return ""

    # Stream to terminal while also capturing to a buffer.
    proc = subprocess.Popen(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines = []
    for line in proc.stdout:
        print(line, end="")
        lines.append(line)
    proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {proc.returncode}: "
            f"{' '.join(str(c) for c in cmd_list)}"
        )
    return "".join(lines)


def compile_source(src_path: Path) -> Path:
    """Compile src_path with the RISC-V musl gcc toolchain. Returns output binary path."""
    out_path = Path(str(src_path) + ".out")
    cmd = [
        COMPILER,
        "-O0",
        "-static",
        str(src_path),
        "-o",
        str(out_path),
    ]
    run_step(cmd, f"Compiling {src_path.name}")
    return out_path


def parse_energy_summary(output: str):
    """Extract total time, total energy, and average power from GEM5 stdout.

    Returns a dict with keys 'time_s', 'energy_j', 'avg_power_w', or None if
    the summary footer could not be found (e.g. GEM5 run without the energy
    report, or an unexpected output format).
    """
    time_match = TIME_RE.search(output)
    energy_match = ENERGY_RE.search(output)
    power_match = POWER_RE.search(output)

    if not (time_match and energy_match and power_match):
        return None

    return {
        "time_s": time_match.group(1),
        "energy_j": energy_match.group(1),
        "avg_power_w": power_match.group(1),
    }


def read_watched_metadata(report_json_path: Path, watch_keys: list):
    """Read the benchmark's own common_api JSON report and pull out the
    requested metadata keys.

    Returns a dict {key: value} for every requested key. Keys not present in
    the report's "metadata" object are recorded as "" (empty). If the report
    file itself is missing or not valid JSON, every requested key is recorded
    as "" and a warning is printed.
    """
    values = {key: "" for key in watch_keys}

    if not watch_keys:
        return values

    if not report_json_path.is_file():
        print(f"    WARNING: watched report file not found: {report_json_path}",
              file=sys.stderr)
        return values

    try:
        with open(report_json_path, "r") as f:
            report = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"    WARNING: could not parse {report_json_path}: {e}", file=sys.stderr)
        return values

    metadata = report.get("metadata", {}) if isinstance(report, dict) else {}

    for key in watch_keys:
        if key in metadata:
            values[key] = metadata[key]
        else:
            print(f"    WARNING: metadata key '{key}' not found in {report_json_path.name}",
                  file=sys.stderr)

    return values


def write_summary_csv(summary_csv_path: Path, rows: list, watch_keys: list):
    """Write all collected per-file results into a single consolidated CSV.

    Each row identifies which source file it came from ("source_file"), the
    energy summary columns, and (if watch_keys is non-empty) one extra column
    per watched metadata key.
    """
    fieldnames = ["source_file", "total_time_s", "total_energy_j", "avg_power_w"] + watch_keys
    with open(summary_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in rows:
            base = [row["source_file"], row["time_s"], row["energy_j"], row["avg_power_w"]]
            watched = [row.get(key, "") for key in watch_keys]
            writer.writerow(base + watched)


def run_gem5(gem5_path: str, binary_path: Path, clock: str):
    """Run the compiled binary through GEM5, producing the energy summary dict.

    power-run.py's -c/--cmd flag passes its value straight through as the
    simulated binary's own argv (process.cmd = [binary_path] + shlex.split(cmd)).
    So the binary's filename argument (used by common_api_output()) must be
    passed via -c, not as a trailing positional gem5 arg -- power-run.py only
    accepts (binary, --clock, -c/--cmd) and rejects anything else with exit
    code 2.

    We pass the binary's own path (without extension) as that argument, so
    the binary writes its common_api JSON report to <binary_path>.json.
    """
    report_json_path = Path(str(binary_path) + ".json")
    report_base = str(binary_path)

    cmd = [
        gem5_path,
        GEM5_CONFIG,
        str(binary_path),
        "--clock", str(clock),
        "-c", report_base,
    ]
    output = run_step(cmd, f"Running GEM5 on {binary_path.name}", capture=True)

    summary = parse_energy_summary(output)
    if summary is None:
        print(f"    WARNING: could not find ENERGY REPORT summary in GEM5 "
              f"output for {binary_path.name}", file=sys.stderr)

    return report_json_path, summary


def main():
    args = parse_args()

    folder: Path = args.folder
    if not folder.is_dir():
        print(f"Error: folder '{folder}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    source_files = sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix in SOURCE_EXTENSIONS
    )

    if not source_files:
        print(f"No source files ({', '.join(SOURCE_EXTENSIONS)}) found in '{folder}'.")
        sys.exit(0)

    watch_keys = [k.strip() for k in args.watch.split(",") if k.strip()]
    if watch_keys:
        print(f"Watching metadata keys: {', '.join(watch_keys)}\n")

    print(f"Found {len(source_files)} source file(s) in '{folder}'.\n")

    failures = []
    summary_rows = []

    for src_path in source_files:
        print(f"[{src_path.name}]")
        try:
            binary_path = compile_source(src_path)
            report_json_path, summary = run_gem5(
                args.gem5_path, binary_path, args.clock
            )

            watched_values = read_watched_metadata(report_json_path, watch_keys)

            if summary is not None:
                summary_rows.append({
                    "source_file": src_path.name,
                    **summary,
                    **watched_values,
                })
                print(f"    OK -> {report_json_path.name} (energy stats recorded)\n")
            else:
                print(f"    OK -> {report_json_path.name} (no energy stats recorded)\n")
        except RuntimeError as e:
            print(f"    FAILED: {e}\n", file=sys.stderr)
            failures.append(src_path.name)

    summary_csv_path = folder / SUMMARY_CSV_NAME
    if summary_rows:
        write_summary_csv(summary_csv_path, summary_rows, watch_keys)
        print(f"Wrote consolidated energy summary -> {summary_csv_path}")
    else:
        print("No energy summaries were collected; skipping consolidated CSV.")

    print("=" * 50)
    print(f"Done. {len(source_files) - len(failures)}/{len(source_files)} succeeded.")
    if failures:
        print("Failed files:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()