# RISC-V Approximate Instructions Implementation

**Author:** Daniela Luiza Catelan  
**Affiliation:** Professor at Federal University of Mato Grosso do Sul (UFMS)

---

Versão em português disponível [aqui](./docs/README_pt.md)

This repository demonstrates how to integrate approximate instructions into the RISC-V instruction set and GEM5 simulator.

The approximate instruction project includes both integer (addx, subx, mulx, divx) and floating-point (faddx, fsubx, fmulx, fdivx) operations, which are part of my doctoral thesis on "Design Space Exploration with Approximate Computing."

## Overview

This repository provides a comprehensive guide for developing and implementing approximate instructions for both integer and floating-point operations in RISC-V architecture and GEM5 simulator.

## Requirements

The following guide should be followed in order to download, setup and use all the tools: [INSTALLING.md](./docs/INSTALLING.md)


## Development

You are welcome to contribute to this project! Take a look at our [development guide](./docs/DEVELOPMENT.md) before and make your PR!


## How to use it

After installing every tool, you can start using it by:
```bash
# Compile the file you want
riscv64-unknown-linux-musl-gcc -O0 -static 
    -march=rv64imafdc 
    -pthread file.c                                     # Change file.c to your c file

# Simulate it
build/RISCV/gem5.opt configs/deprecated/example/se.py
    -c a.out
    # Change only the --num-cpus >= 1. Any other flag
    # mantain the same, since they are all dependent on 
    # each other
    --num-cpus=3 --cpu-type=O3CPU --caches --l1d_size=32kB 
    --l1d_assoc=2 --l1i_size=32kB --l1i_assoc=2 --l2_size=256kB 
    --l2_assoc=2 --cpu-clock=1GHz
```

### Output

After running a simulation, gem5 automatically generates several statistics files in the `m5out/` directory. The most relevant files are:

- **config.ini**: Contains information about the CPU type, ISA, available cache, bit width, and more. This helps verify that your simulation setup matches your expectations.
- **stats.txt**: The main statistics file, including simulation time, number of ticks, CPU cycles, CPU IPC (Instructions Per Cycle), L1 cache information, and more.

#### Understanding the Metrics

In `stats.txt`, you will find many metrics. While not all are necessary for every use case, metrics like simulation time and cache usage are commonly useful.

The metrics follow this format:

```
<metric name>       <metric value>
```

**Example:**
```
simSeconds                      0.000076
simInsts                        111732
...
```

**Most useful metrics:**

- `system.cpu.numCycles`: Total number of CPU cycles
- `simSeconds`: Total simulation time in seconds
- `simInsts`: Total number of simulated instructions
- `system.cpu.ipc`: Instructions per cycle (IPC)

**Other potentially useful metrics:**

- `system.cpu.commitStats0.numFpInsts`: Number of floating-point instructions
- `system.cpu.commitStats0.numIntInsts`: Number of integer instructions
- `system.cpu.commitStats0.numLoadInsts`: Number of load instructions
- `system.cpu.commitStats0.numStoreInsts`: Number of store instructions
- `system.cpu.commitStats0.numVecInsts`: Number of vector instructions

#### Energy Statistics

By default, gem5 does not collect energy consumption statistics.

## References

### Surveys

- Vasileios Leon, Muhammad Abdullah Hanif, Giorgos Armeniakos, Xun Jiao, Muhammad Shafique, Kiamal Pekmestzi, Dimitrios Soudris (2025). [*Approximate Computing Survey, Part I: Terminology and Software & Hardware Approximation Techniques*](https://dl.acm.org/doi/10.1145/3716845).

-  Vasileios Leon, Muhammad Abdullah Hanif, Giorgos Armeniakos, Xun Jiao, Muhammad Shafique, Kiamal Pekmestzi, Dimitrios Soudris (2025). [*Approximate Computing Survey, Part II: Application-Specific & Architectural Approximation Techniques and Applications*](https://dl.acm.org/doi/10.1145/3711683).

### Others

- Daniela Catelan, Ricardo Santos, Liana Duenha (2022). [*Evaluation and characterization of approximate arithmetic circuits*](https://onlinelibrary.wiley.com/doi/10.1002/cpe.6865).

- Daniela Catelan, Felipe Sovernigo, Liana Duenha, Ricardo Santos (2024). [*An Instruction-Set Extension to Support Approximate Multicore Processors*](https://ieeexplore.ieee.org/document/10764671).

## Contact

**Daniela Luiza Catelan**  
Email: daniela.catelan@ufms.br  
Federal University of Mato Grosso do Sul (UFMS)
