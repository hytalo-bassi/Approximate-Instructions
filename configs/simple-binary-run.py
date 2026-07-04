"""
This is the general binary runner for RISCV equivalent to `simple.py`
(which is designed to run using the X86 ISA). More detailed documentation can be found
in `simple.py`.
"""
import argparse
import os

import m5
from m5.objects import *

parser = argparse.ArgumentParser(
    description="A script to run an arbitrary RISCV binary."
)
parser.add_argument(
    "binary", type=str, help="Path to the binary to execute."
)
args = parser.parse_args()

system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MiB")]
system.cpu = RiscvTimingSimpleCPU()
system.membus = SystemXBar()
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports
system.cpu.createInterruptController()
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports
system.system_port = system.membus.cpu_side_ports

binary = os.path.abspath(args.binary)

system.workload = SEWorkload.init_compatible(binary)
process = Process()
process.cmd = [binary]
system.cpu.workload = process
system.cpu.createThreads()
root = Root(full_system=False, system=system)
m5.instantiate()
print(f"Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")