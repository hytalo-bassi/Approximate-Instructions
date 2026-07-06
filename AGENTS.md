# AGENTS.md - AI Assistant Guidelines

## Project Overview

This repository implements approximate instructions for RISC-V architecture and GEM5 simulator. It extends the RISC-V ISA with approximate computing operations (addx, subx, mulx, divx, faddx, fsubx, fmulx, fdivx) for energy-efficient computation trade-offs.

## Build Commands

### Docker (Recommended)

```bash
# Build and run with gem5
docker compose -f docker/compose.yaml build riscv-gem5
docker compose -f docker/compose.yaml up riscv-gem5 -d
docker exec -it riscv-gem5 bash

# Build toolchain only
docker compose -f docker/compose.yaml build base
docker compose -f docker/compose.yaml up base -d
```

### Compilation

```bash
# Compile C programs
riscv64-unknown-linux-musl-gcc -O0 -static -march=rv64imafdc -pthread file.c -o file

# Run simulation in gem5 (inside container)
build/RISCV/gem5.opt configs/deprecated/example/se.py -c file \
    --num-cpus=3 --cpu-type=O3CPU --caches \
    --l1d_size=32kB --l1d_assoc=2 --l1i_size=32kB \
    --l1i_assoc=2 --l2_size=256kB --l2_assoc=2 --cpu-clock=1GHz
```

## Code Style

### C/C++

- Use 4-space indentation
- Follow K&R brace style
- No trailing whitespace
- Use meaningful variable names
- Keep functions focused and modular

### Python

- Follow PEP 8 conventions
- Use 4-space indentation
- Prefer type hints where applicable
- Use descriptive function and variable names

### Documentation

- Document in English first (required)
- Portuguese translations welcome after English docs exist
- Use clear, concise language

## Git Conventions

Follow Conventional Commits specification:

```
<type>(<scope>): <subject>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `chore`

**Example:** `feat(gem5): add support for approximate multiplier in simple_config`

## Project Structure

```
├── Approx_Instructions/   # Approximate instruction implementations
├── configs/               # gem5 and simulation configurations
├── docker/                # Docker environment definitions
│   ├── build/             # Development Dockerfiles
│   └── prod/              # Production Dockerfiles
├── docs/                  # Documentation (English required)
├── examples/              # Example programs and benchmarks
│   ├── axbench/           # AxBench benchmark suite
│   ├── basic/             # Simple test programs
│   └── matrices/          # Matrix operation examples
├── patches/               # Source patches for toolchain/gem5
└── scripts/               # Automation and utility scripts
```

## Testing

### Verify Installation

After installation, verify tools work:

```bash
riscv64-unknown-linux-musl-gcc -v
```

### Test Approximate Instructions

Create a test file using approximate instructions:

```c
#include <stdio.h>

int main() {
    int a = 5, b = 2, result;
    asm volatile (
        "addx   %[z], %[x], %[y]\n\t"
        : [z] "=r" (result)
        : [x] "r" (a), [y] "r" (b)
    );
    printf("ADDX => 5+2=%d\n", result);
    return 0;
}
```

Compile and simulate:

```bash
riscv64-unknown-linux-musl-gcc -march=rv64imafdc -static test.c -o test
build/RISCV/gem5.opt configs/deprecated/example/se.py -c test --num-cpus=3 --cpu-type=O3CPU --caches
```

## Adding New Instructions

1. Define instruction encoding in `patches/riscv-opcodes/extensions/unratified/rv32_approx`
2. Use riscv-opcodes to generate encoding headers
3. Update patches in:
   - `patches/riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h`
   - `patches/riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c`
   - `patches/riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h`
   - `patches/gem5/src/arch/riscv/isa/decoder.isa`
4. Reference `docs/BITFIELDS.md` for bitfield encoding guidance

## Docker Guidelines

- Use Docker for consistent development environment
- Build images: `docker compose -f docker/compose.yaml build <service>`
- Development uses `docker/build/` Dockerfiles
- Production uses `docker/prod/` Dockerfiles
- Workspace mounted at `/workspace` inside container

## Important Files

- `README.md` - Project overview and quick start
- `docs/INSTALLING.md` - Full installation guide
- `docs/DEVELOPMENT.md` - Development conventions and workflow
- `docs/BITFIELDS.md` - Instruction bitfield encoding guide

## Notes

- Minimum 20-25 GB disk space for toolchain compilation
- 8 GB RAM recommended for parallel compilation
- Build process can take 30 minutes to several hours
- Always test changes inside Docker container for consistency
