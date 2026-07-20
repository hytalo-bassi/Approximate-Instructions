"""
Batch driver for the O3 energy runner.

This is a *plain* Python script (run with your normal system `python3`, not
`gem5.opt`). gem5 itself only performs one simulation per process, so to run
a whole folder of binaries we invoke `gem5.opt` once per binary as a
subprocess, each time pointing it at its own --outdir.

For every binary found in the input folder this script:
  1. Picks a destination .txt file named "<binary_name>.txt".
  2. Runs:
       gem5.opt --outdir=<per-binary outdir> o3_energy_runner.py <binary> \
           --clock <clock> -c "<dest.txt>"
     The `-c` value is forwarded verbatim as an argument to the *simulated*
     binary (see o3_energy_runner.py), so the binary itself is expected to
     write its A / B / epoch line to that path.
  3. Parses that .txt file with a regex to pull out EPOCH, A and B from:
       Treinamento concluido apos %d epocas!
       Reta com FLOAT : y = %f x + %f
  4. Loads energy_summary.json (written by o3_energy_runner.py into the
     per-binary outdir) to get per-instruction counts/energy and totals.
  5. Adds one row to the final CSV, identified by the binary's name.
"""
import argparse
import csv
import json
import os
import re
import shlex
import stat
import subprocess
import sys

# Regexes for the two lines produced by the simulated binary.
EPOCH_RE = re.compile(r"Treinamento concluido apos (\d+) epocas!")
FLOAT = r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"
AB_RE = re.compile(rf"Reta com FLOAT\s*:\s*y\s*=\s*({FLOAT})\s*x\s*\+\s*({FLOAT})")


def find_binaries(folder):
    """Return sorted list of absolute paths to executable, regular files
    directly inside `folder` (non-recursive)."""
    binaries = []
    for entry in sorted(os.listdir(folder)):
        if entry.startswith("."):
            continue
        full_path = os.path.join(folder, entry)
        if not os.path.isfile(full_path):
            continue
        mode = os.stat(full_path).st_mode
        if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            binaries.append(full_path)
    return binaries


def parse_dest_txt(dest_txt_path):
    """Extract epoch/A/B from the binary's own output file."""
    epoch = a = b = None
    if not os.path.exists(dest_txt_path):
        return epoch, a, b

    with open(dest_txt_path, "r") as f:
        content = f.read()

    epoch_match = EPOCH_RE.search(content)
    if epoch_match:
        epoch = int(epoch_match.group(1))

    ab_match = AB_RE.search(content)
    if ab_match:
        a = float(ab_match.group(1))
        b = float(ab_match.group(2))

    return epoch, a, b


def run_one_binary(gem5_bin, script_path, binary_path, clock, outdir, dest_txt):
    os.makedirs(outdir, exist_ok=True)
    cmd = [
        gem5_bin,
        f"--outdir={outdir}",
        script_path,
        binary_path,
        "--clock", clock,
        "-c", dest_txt,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def load_energy_summary(outdir):
    summary_path = os.path.join(outdir, "energy_summary.json")
    if not os.path.exists(summary_path):
        return None
    with open(summary_path, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Run the gem5 O3 energy runner against every binary in "
                     "a folder and collect the results into one CSV."
    )
    parser.add_argument(
        "binaries_dir", type=str,
        help="Folder containing the binaries to execute."
    )
    parser.add_argument(
        "--gem5-bin", type=str, default="build/RISCV/gem5.opt",
        help="Path to the gem5 executable (default: build/RISCV/gem5.opt)."
    )
    parser.add_argument(
        "--script", type=str,
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "o3_energy_runner.py"),
        help="Path to o3_energy_runner.py (default: alongside this script)."
    )
    parser.add_argument(
        "--clock", type=str, default="1GHz",
        help="CPU clock frequency forwarded to o3_energy_runner.py."
    )
    parser.add_argument(
        "--work-dir", type=str, default="power_suite_results",
        help="Where per-binary outdirs and destination .txt files are kept."
    )
    parser.add_argument(
        "--output-csv", type=str, default="power_suite.csv",
        help="Path to the aggregated CSV to produce."
    )
    args = parser.parse_args()

    binaries = find_binaries(args.binaries_dir)
    if not binaries:
        print(f"No executable binaries found in {args.binaries_dir}")
        sys.exit(1)

    os.makedirs(args.work_dir, exist_ok=True)

    # Fixed columns first, then one count_/energy_ pair per instruction seen
    # across all binaries (so the CSV stays consistent even if different
    # binaries exercise different instruction mixes).
    fixed_columns = [
        "binary", "epoch", "A", "B",
        "total_energy_j", "total_dynamic_time_s", "avg_power_w",
        "status",
    ]
    rows = []
    instruction_columns = set()

    for binary_path in binaries:
        name = os.path.basename(binary_path)
        print(f"Running {name} ...")

        dest_txt = os.path.join(args.work_dir, f"{name}.txt")
        outdir = os.path.join(args.work_dir, f"m5out_{name}")

        result = run_one_binary(
            args.gem5_bin, args.script, binary_path, args.clock,
            outdir, dest_txt,
        )

        row = {col: "" for col in fixed_columns}
        row["binary"] = name

        if result.returncode != 0:
            print(f"  ! gem5 failed for {name} (exit {result.returncode})")
            print(result.stderr[-2000:])
            row["status"] = f"gem5_error_{result.returncode}"
            rows.append(row)
            continue

        epoch, a, b = parse_dest_txt(dest_txt)
        row["epoch"] = epoch if epoch is not None else ""
        row["A"] = a if a is not None else ""
        row["B"] = b if b is not None else ""

        summary = load_energy_summary(outdir)
        if summary is None:
            print(f"  ! No energy_summary.json found for {name}")
            row["status"] = "missing_energy_summary"
            rows.append(row)
            continue

        row["total_energy_j"] = summary.get("total_energy_j", "")
        row["total_dynamic_time_s"] = summary.get("total_dynamic_time_s", "")
        row["avg_power_w"] = summary.get("avg_power_w", "")
        row["status"] = "ok"

        for entry in summary.get("report", []):
            inst = entry["name"]
            count_col = f"count_{inst}"
            energy_col = f"energy_{inst}"
            instruction_columns.add(count_col)
            instruction_columns.add(energy_col)
            row[count_col] = entry["count"]
            row[energy_col] = entry["energy_j"]

        rows.append(row)

    all_columns = fixed_columns + sorted(instruction_columns)

    with open(args.output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns, restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\nWrote {len(rows)} rows to {args.output_csv}")


if __name__ == "__main__":
    main()