"""
This script configures and runs a gem5 simulation of a multi-core RISC-V system
in syscall emulation (SE) mode. It allows users to specify a binary to execute
and the number of cores to simulate.

The simulation uses:
- AtomicSimpleCPU cores with RV32 ISA
- 1GHz clock frequency
- 8192 MiB memory with DDR3_1600_8x8 configuration
- Atomic memory mode for faster simulation
- System crossbar (SystemXBar) for interconnect

Author: Hytalo Bassi
Date: November 13, 2025

Usage:
    python3 script.py [-c CORE_NUMBER] binary_path
    
Examples:
    python3 script.py /path/to/binary
    python3 script.py -c 4 /path/to/binary
    python3 script.py --core_number 2 /path/to/riscv/program
"""

import m5
from m5.objects import *
import argparse
import sys


def create_parser():
    """
    Create and configure the command-line argument parser.
    
    Creates an ArgumentParser object with two arguments:
    - binary_path: Required positional argument for the path to the executable
    - core_number: Optional argument to specify number of CPU cores (default: 1)
    
    Returns:
        argparse.ArgumentParser: Configured argument parser ready to parse CLI arguments
        
    Examples:
        >>> parser = create_parser()
        >>> args = parser.parse_args(['-c', '4', '/path/to/binary'])
        >>> print(args.core_number)
        4
    """
    parser = argparse.ArgumentParser(
        description='Run a binary with specified core number',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'binary_path',
        type=str,
        help='Path to the binary file (required)'
    )
    
    parser.add_argument(
        '-c', '--core_number',
        type=int,
        default=1,
        help='Number of cores to use (default: 1)'
    )

    return parser


def main():
    """
    Main function to configure and run the gem5 simulation.
    
    This function performs the following steps:
    1. Parses command-line arguments to get binary path and core count
    2. Creates a System object with clock domain and memory configuration
    3. Instantiates the specified number of AtomicSimpleCPU cores with RV32 ISA
    4. Configures memory system with DDR3 controller and system crossbar
    5. Sets up the workload and process for syscall emulation mode
    6. Instantiates and runs the simulation
    
    The simulation runs until the binary completes execution or encounters
    a simulation exit event.
    
    Raises:
        SystemExit: If invalid arguments are provided or binary path doesn't exist
        
    Side Effects:
        - Prints simulation statistics to stdout upon completion
        - May generate simulation output files in m5out directory
        
    Returns:
        None
    """
    args = create_parser().parse_args()
    
    binary = args.binary_path
    num_cores = args.core_number

    system = System()
    system.clk_domain = SrcClockDomain(clock='1GHz', voltage_domain=VoltageDomain())
    system.mem_mode = 'atomic'
    system.mem_ranges = [AddrRange('8192MiB')]
    system.membus = SystemXBar()

    system.cpu = [AtomicSimpleCPU(cpu_id=i) for i in range(num_cores)]

    for cpu in system.cpu:
        cpu.numThreads = 1
        cpu.isa = [RiscvISA(riscv_type='RV32')]
        cpu.interrupts = [RiscvInterrupts()]
        cpu.icache_port = system.membus.cpu_side_ports
        cpu.dcache_port = system.membus.cpu_side_ports

    system.system_port = system.membus.cpu_side_ports
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

    system.workload = SEWorkload.init_compatible(binary)

    process = Process()
    process.cmd = [binary]

    for cpu in system.cpu:
        cpu.workload = process
        cpu.createThreads()

    root = Root(full_system=False, system=system)
    m5.instantiate()
    m5.simulate()

main()
