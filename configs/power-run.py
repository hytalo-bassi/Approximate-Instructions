### It's necessary for obtaining the commitInst_<name> counters from stats.txt
### to use the O3CPU model, due to being the only CPU that has the iew.cc and iew.hh files,
### which are necessary to count the number of committed instructions per instruction type.
"""
RISCV O3 CPU runner with post-simulation energy accounting.
Runs a user-provided binary on an O3 CPU, then parses the per-instruction
commitInst_<name> counters from stats.txt and computes total energy
consumed using a static cycles/power table (64-bit only).
"""
import argparse
import os
import re
import shlex

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
    "-c",
    "--cmd",
    type=str,
    default="",
    help="Options/arguments to pass directly to the binary, e.g. -c \"arg1 arg2\"",
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


def build_system(binary_path, extra_args=None):
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

    # Build the command line: binary followed by any extra args passed via -c/--cmd
    cmd = [binary_path]
    if extra_args:
        cmd.extend(extra_args)
    process.cmd = cmd

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
    counts = {}
    pattern = re.compile(r"^system\.cpu\.iew\.commitInst_(\S+)\s+(\d+)")
    with open(stats_path, "r") as f:
        for line in f:
            match = pattern.match(line)
            if match:
                inst_name, count = match.groups()
                counts[inst_name] = int(count)
    return counts


def compute_energy_report(counts, clock_period_s):
    report = []
    total_energy_j = 0.0
    total_dynamic_time_s = 0.0

    for inst_name, count in counts.items():
        if count == 0 or inst_name not in INSTRUCTION_POWER_TABLE:
            continue

        cycles, power_w = INSTRUCTION_POWER_TABLE[inst_name]
        time_per_inst_s = cycles * clock_period_s
        inst_total_energy_j = power_w * time_per_inst_s * count
        inst_total_time_s = time_per_inst_s * count

        total_energy_j += inst_total_energy_j
        total_dynamic_time_s += inst_total_time_s

        report.append({
            "name": inst_name, "count": count, "cycles": cycles,
            "power_w": power_w, "energy_j": inst_total_energy_j,
        })

    return report, total_energy_j, total_dynamic_time_s


binary = os.path.abspath(args.binary)
extra_args = shlex.split(args.cmd) if args.cmd else []
system = build_system(binary, extra_args)
root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")

m5.stats.dump()

stats_path = os.path.join(m5.options.outdir, "stats.txt")
clock_period_s = parse_clock_period_seconds(args.clock)
counts = parse_commit_inst_counts(stats_path)
report, total_energy_j, total_dynamic_time_s = compute_energy_report(
    counts, clock_period_s
)

print("\n" + "=" * 70)
print(f"ENERGY REPORT (xlen={XLEN}-bit, clock={args.clock})")
print("=" * 70)
print(f"{'Instruction':<14}{'Count':>10}{'Cycles':>8}"
      f"{'Power(W)':>14}{'Energy(J)':>16}")
for entry in sorted(report, key=lambda r: -r["energy_j"]):
    print(f"{entry['name']:<14}{entry['count']:>10}{entry['cycles']:>8}"
          f"{entry['power_w']:>14.6f}{entry['energy_j']:>16.9e}")
print("-" * 70)
print(f"Total dynamic execution time: {total_dynamic_time_s:.9e} s")
print(f"Total energy consumed:        {total_energy_j:.9e} J")
if total_dynamic_time_s > 0:
    avg_power_w = total_energy_j / total_dynamic_time_s
    print(f"Average power (dynamic):      {avg_power_w:.6f} W")
print("=" * 70)