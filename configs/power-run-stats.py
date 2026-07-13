### It's necessary for obtaining the commitInst_<name> counters from stats.txt
### to use the O3CPU model, due to being the only CPU that has the iew.cc and iew.hh files,
### which are necessary to count the number of committed instructions per instruction type.
"""
RISCV O3 CPU runner with post-simulation energy accounting.

Runs a user-provided binary on an O3 CPU, then parses the per-instruction
commitInst_<name> counters from stats.txt and computes energy, IPC, power
and latency metrics for a user-selected instruction (and, typically, its
approximate counterpart), writing the results to a CSV file.

Only instructions passed via --inst are considered, and only if their
commit count in stats.txt is nonzero.
"""
import argparse
import csv
import os
import re

import m5
from m5.objects import *

parser = argparse.ArgumentParser(
    description="Run a RISCV binary on an O3 CPU and report energy "
                 "consumption based on per-instruction cycle/power data."
)
parser.add_argument(
    "binary", type=str, help="Path to the binary to execute."
)
parser.add_argument(
    "--clock", type=str, default="1GHz",
    help="CPU clock frequency, e.g. '1GHz', '2GHz' (default: 1GHz)."
)
parser.add_argument(
    "--inst", type=str, required=True,
    help="Comma-separated list of instruction names to report on, e.g. "
         "'add,addx' or 'fmulx_s'. Only these instructions are included "
         "in the report/CSV, and only if their commit count is nonzero."
)
parser.add_argument(
    "--csv", type=str, default="energy_report.csv",
    help="Path to the output CSV file (default: energy_report.csv)."
)
args = parser.parse_args()

# Only 64-bit (RV64) is supported. The broader RISC-V community and
# toolchains (Linux distros, upstream compilers, most current cores)
# have largely dropped active RV32 support in favor of RV64, so this
# script no longer exposes a 32-bit code path.
XLEN = 64

# --- Cycles / power table -----------------------------------------------
# Power figures are in Watts. Keys are sanitized to match gem5 stat names
# (dots replaced with underscores, since gem5 stat leaf names cannot
# contain '.').
# Each of the power constant stats was obtained through experimental measurements
# prior to my entry year in the lab. Those might change in the future
INSTRUCTION_POWER_TABLE = {
    # name:          (cycles, power_64bit_W)
    "addi":        (1, 5.809836855),
    "sw":          (1, 3.370162992),
    "li":          (1, 3.563078126),
    "lw":          (1, 5.118893519),
    "jal":         (2, 4.544682106),
    "mv":          (1, 3.174765032),
    "bge":         (2, 4.843875097),
    "add":         (1, 5.601006041),
    "j":           (2, 4.842237504),
    "ret":         (2, 3.645425428),
    "beqz":        (2, 5.244648391),
    "mul":         (1, 6.188915991),
    "bnez":        (2, 4.934859221),
    "bltu":        (2, 4.990002522),
    "blt":         (2, 4.991772552),
    "bltz":        (2, 4.991772552),
    "bne":         (2, 4.934859221),
    "bgeu":        (2, 4.843875097),
    "sltu":        (1, 4.863286586),
    "slli":        (1, 5.125101431),
    "srai":        (1, 5.585422749),
    "sub":         (1, 5.731239419),
    "or":          (1, 5.61684595),
    "beq":         (2, 5.244648391),
    "andi":        (1, 5.809836855),
    "srli":        (1, 5.125101431),
    "xori":        (1, 5.809836855),
    "sltiu":       (1, 5.809836855),
    "lbu":         (1, 5.118893519),
    "lh":          (1, 5.118893519),
    "lhu":         (1, 5.118893519),
    "ori":         (1, 5.809836855),
    "jalr":        (2, 4.544682106),
    "and":         (1, 5.32),
    "sll":         (1, 4.916270617),
    "xor":         (1, 4.863286586),
    "sh":          (1, 3.370162992),
    "snez":        (1, 4.863286586),
    "blez":        (2, 4.843875097),
    "neg":         (1, 5.731239419),
    "jr":          (2, 4.544682106),
    "lui":         (2, 4.544682106),
    "epc":         (1, 3.645425428),
    "csrw":        (1, 3.370162992),
    "csrrw":       (1, 5.118893519),
    "csrr":        (1, 5.118893519),
    "auipc":       (1, 4.544682106),
    "fence":       (1, 5.809836855),
    "sfence_vma":  (1, 3.645425428),
    "bgez":        (2, 4.843875097),
    "sneg":        (1, 5.731239419),
    "sret":        (2, 3.645425428),
    "sb":          (1, 3.645425428),
    "not":         (1, 5.809836855),
    "ecall":       (1, 3.645425428),
    "zext_b":      (1, 3.645425428),
    "addx":        (1, 4.833668214),
    "subx":        (1, 5.490526906),
    "mulx":        (1, 4.975888456),
    "divx":        (1, 4.975888456),
    "m_addx":      (1, 5.564599502),
    "m_subx":      (1, 5.693986354),
    "m_mulx":      (1, 6.148688032),
    "m_divx":      (1, 6.148688032),
    "addx_m":      (1, 5.564599502),
    "subx_m":      (1, 5.693986354),
    "mulx_m":      (1, 6.148688032),
    "divx_m":      (1, 6.148688032),
    # float type instructions (the ones ending in _s) are always 32-bit,
    # even in 64-bit CPUs, so they keep a single fixed power figure.
    "faddx_s":     (2, 3.185852236),
    "fsubx_s":     (2, 3.349336317),
    "fmulx_s":     (2, 3.520255415),
    "fdivx_s":     (2, 3.616802505),
}


def build_system(binary_path):
    system = System()
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = args.clock
    system.clk_domain.voltage_domain = VoltageDomain()
    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange("512MiB")]

    system.cpu = RiscvO3CPU()
    system.membus = SystemXBar()
    system.cpu.icache_port = system.membus.cpu_side_ports
    system.cpu.dcache_port = system.membus.cpu_side_ports
    system.cpu.createInterruptController()

    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports
    system.system_port = system.membus.cpu_side_ports

    system.workload = SEWorkload.init_compatible(binary_path)
    process = Process()
    process.cmd = [binary_path]
    system.cpu.workload = process
    system.cpu.createThreads()

    return system


def parse_clock_period_seconds(clock_str):
    match = re.match(r"([0-9.]+)\s*(THz|GHz|MHz|kHz|Hz)$", clock_str)
    if not match:
        raise ValueError(
            f"Unsupported clock format '{clock_str}'; expected e.g. "
            f"'1GHz', '500MHz'."
        )
    value, unit = match.groups()
    value = float(value)
    multiplier = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12}[unit]
    return 1.0 / (value * multiplier)


def parse_commit_inst_counts(stats_path):
    """Parse all system.cpu.iew.commitInst_<name> counters from stats.txt."""
    counts = {}
    pattern = re.compile(r"^system\.cpu\.iew\.commitInst_(\S+)\s+(\d+)")
    with open(stats_path, "r") as f:
        for line in f:
            match = pattern.match(line)
            if match:
                inst_name, count = match.groups()
                counts[inst_name] = int(count)
    return counts


def parse_scalar_stat(stats_path, stat_name):
    """Parse a single scalar stat (e.g. system.cpu.numCycles) from stats.txt."""
    pattern = re.compile(rf"^{re.escape(stat_name)}\s+([0-9.eE+-]+)")
    with open(stats_path, "r") as f:
        for line in f:
            match = pattern.match(line)
            if match:
                return float(match.group(1))
    return None


def compute_energy_report(selected_names, counts, clock_period_s,
                           total_cycles, total_committed_insts):
    """
    Build one report row per selected instruction that actually committed
    (count > 0) and is present in the power table.
    """
    report = []

    # Overall CPU IPC across the whole run, used as shared context for
    # every row (not instruction-specific, but useful to correlate against
    # the per-instruction ideal IPC).
    global_ipc = (
        total_committed_insts / total_cycles if total_cycles else None
    )

    for inst_name in selected_names:
        count = counts.get(inst_name, 0)
        if count == 0:
            # Instruction never executed in this run -- excluded entirely.
            continue
        if inst_name not in INSTRUCTION_POWER_TABLE:
            print(f"Warning: '{inst_name}' has no entry in the power "
                  f"table, skipping.")
            continue

        cycles, power_w = INSTRUCTION_POWER_TABLE[inst_name]

        time_per_inst_s = cycles * clock_period_s       # == latency (s)
        total_time_s = time_per_inst_s * count           # execution time
        energy_per_inst_j = power_w * time_per_inst_s     # Joules / instr
        total_energy_j = energy_per_inst_j * count

        # Ideal, per-instruction-type IPC: how many of *this* instruction
        # could retire per cycle if the pipeline did nothing else.
        ideal_ipc = 1.0 / cycles if cycles else None

        avg_power_w = (
            total_energy_j / total_time_s if total_time_s else power_w
        )

        report.append({
            "instruction":        inst_name,
            "frequency":          count,          # commit count
            "instruction_count":  count,
            "cycles_per_inst":    cycles,
            "total_cycles":       cycles * count,
            "latency_s":          time_per_inst_s,
            "execution_time_s":   total_time_s,
            "power_w":            power_w,
            "avg_power_per_cycle_w": power_w,      # constant model: power/cycle == power
            "avg_power_w":        avg_power_w,
            "energy_per_inst_j":  energy_per_inst_j,
            "total_energy_j":     total_energy_j,
            "ipc_ideal":          ideal_ipc,
            "ipc_global":         global_ipc,
        })

    return report


def write_csv(report, csv_path):
    fieldnames = [
        "instruction", "frequency", "instruction_count",
        "cycles_per_inst", "total_cycles",
        "latency_s", "execution_time_s",
        "power_w", "avg_power_per_cycle_w", "avg_power_w",
        "energy_per_inst_j", "total_energy_j",
        "ipc_ideal", "ipc_global",
    ]
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for row in report:
            writer.writerow(row)


selected_names = [name.strip() for name in args.inst.split(",") if name.strip()]

binary = os.path.abspath(args.binary)
system = build_system(binary)
root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")

m5.stats.dump()

stats_path = os.path.join(m5.options.outdir, "stats.txt")
clock_period_s = parse_clock_period_seconds(args.clock)
counts = parse_commit_inst_counts(stats_path)

total_cycles = parse_scalar_stat(stats_path, "system.cpu.numCycles")
total_committed_insts = parse_scalar_stat(stats_path, "system.cpu.committedInsts")
if total_committed_insts is None:
    # Fallback: sum every commitInst_<name> counter as total committed insts.
    total_committed_insts = sum(counts.values())

report = compute_energy_report(
    selected_names, counts, clock_period_s,
    total_cycles, total_committed_insts,
)

print("\n" + "=" * 100)
print(f"ENERGY REPORT (xlen={XLEN}-bit, clock={args.clock}, "
      f"instructions={','.join(selected_names)})")
print("=" * 100)
if not report:
    print("None of the selected instructions committed a nonzero number "
          "of times in this run.")
else:
    header = (f"{'Instr':<12}{'Count':>8}{'Cycles':>8}{'Power(W)':>12}"
              f"{'AvgPow(W)':>12}{'E/inst(J)':>14}{'TotalE(J)':>14}"
              f"{'IPCideal':>10}{'IPCglobal':>11}{'Lat(s)':>12}{'ExecT(s)':>12}")
    print(header)
    for r in report:
        print(f"{r['instruction']:<12}{r['instruction_count']:>8}"
              f"{r['cycles_per_inst']:>8}{r['power_w']:>12.6f}"
              f"{r['avg_power_w']:>12.6f}{r['energy_per_inst_j']:>14.6e}"
              f"{r['total_energy_j']:>14.6e}"
              f"{(r['ipc_ideal'] or 0):>10.4f}"
              f"{(r['ipc_global'] or 0):>11.4f}"
              f"{r['latency_s']:>12.6e}{r['execution_time_s']:>12.6e}")

write_csv(report, args.csv)
print("-" * 100)
print(f"Total cycles (sim):           {total_cycles}")
print(f"Total committed insts (sim):  {total_committed_insts}")
print(f"CSV written/appended to:      {os.path.abspath(args.csv)}")
print("=" * 100)