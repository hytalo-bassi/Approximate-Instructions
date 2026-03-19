# Installing SPIKE Simulator

> **⚠️ Deprecation Notice:** SPIKE has been dropped in favour of **gem5** and is no longer recommended. This guide may be partially outdated. The custom version described here only supports **rv32**.

---

## Overview

This guide covers:
1. Generating custom opcodes via `riscv-opcodes`
2. Patching the GNU toolchain with custom instruction definitions
3. Building the 32-bit RISC-V toolchain
4. Installing Spike and PK
5. Applying the approximate instructions patch
6. Building and testing

---

## 1. Generating Custom Opcodes

Clone and configure `riscv-opcodes` to produce a custom `encoding.h`:

```bash
git clone https://github.com/riscv/riscv-opcodes
cd riscv-opcodes
git checkout 15cc83e
cp ../patches/riscv-opcodes/extensions/unratified/rv32_approx extensions/unratified
./parse.py -c 'unratified/rv32_approx'
```

---

## 2. Patching the GNU Toolchain

### 2.1 — `riscv-opc.h` (both `binutils` and `gdb`)

Open each of the following files:
- `riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h`
- `riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h`

**After** the line `#define RISCV_ENCODING_H`, add the `MATCH`/`MASK` macros from `encoding.h`:

```c
#define MATCH_ADDX    0x200002b
#define MASK_ADDX     0xfe00707f
#define MATCH_SUBX    0x200002f
#define MASK_SUBX     0xfe00707f
#define MATCH_MULX    0x2000073
#define MASK_MULX     0xfe00707f
#define MATCH_DIVX    0x2000077
#define MASK_DIVX     0xfe00707f
#define MATCH_REMX    0x200007b
#define MASK_REMX     0xfe00707f
#define MATCH_FADDX_S 0x80000053
#define MASK_FADDX_S  0xfe00007f
#define MATCH_FSUBX_S 0x88000053
#define MASK_FSUBX_S  0xfe00007f
#define MATCH_FMULX_S 0x90000053
#define MASK_FMULX_S  0xfe00007f
#define MATCH_FDIVX_S 0x98000053
#define MASK_FDIVX_S  0xfe00007f
```

> **Note:** The hex values above may differ from what `parse.py` generates. Always use the values from your generated `encoding.h`.

**After** the line `#ifdef DECLARE_INSN`, add the `DECLARE_INSN` entries:

```c
DECLARE_INSN(addx,    MATCH_ADDX,    MASK_ADDX)
DECLARE_INSN(subx,    MATCH_SUBX,    MASK_SUBX)
DECLARE_INSN(mulx,    MATCH_MULX,    MASK_MULX)
DECLARE_INSN(divx,    MATCH_DIVX,    MASK_DIVX)
DECLARE_INSN(remx,    MATCH_REMX,    MASK_REMX)
DECLARE_INSN(faddx_s, MATCH_FADDX_S, MASK_FADDX_S)
DECLARE_INSN(fsubx_s, MATCH_FSUBX_S, MASK_FSUBX_S)
DECLARE_INSN(fmulx_s, MATCH_FMULX_S, MASK_FMULX_S)
DECLARE_INSN(fdivx_s, MATCH_FDIVX_S, MASK_FDIVX_S)
```

### 2.2 — `riscv-opc.c` (both `binutils` and `gdb`)

Open each of the following files:
- `riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c`

Add the instruction table entries for the custom opcodes:

```c
{"addx",    0, INSN_CLASS_I,     "d,s,t",   MATCH_ADDX,                    MASK_ADDX,                    match_opcode, 0},
{"subx",    0, INSN_CLASS_I,     "d,s,t",   MATCH_SUBX,                    MASK_SUBX,                    match_opcode, 0},
{"mulx",    0, INSN_CLASS_I,     "d,s,t",   MATCH_MULX,                    MASK_MULX,                    match_opcode, 0},
{"divx",    0, INSN_CLASS_I,     "d,s,t",   MATCH_DIVX,                    MASK_DIVX,                    match_opcode, 0},
{"remx",    0, INSN_CLASS_I,     "d,s,t",   MATCH_REMX,                    MASK_REMX,                    match_opcode, 0},
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FADDX_S|MASK_RM,        MASK_FADDX_S|MASK_RM,         match_opcode, 0},
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FADDX_S,                MASK_FADDX_S,                 match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FSUBX_S|MASK_RM,        MASK_FSUBX_S|MASK_RM,         match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FSUBX_S,                MASK_FSUBX_S,                 match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FMULX_S|MASK_RM,        MASK_FMULX_S|MASK_RM,         match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FMULX_S,                MASK_FMULX_S,                 match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FDIVX_S|MASK_RM,        MASK_FDIVX_S|MASK_RM,         match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FDIVX_S,                MASK_FDIVX_S,                 match_opcode, 0},
```

> **Important:** In the `gdb/` version of `riscv-opc.c`, the floating-point entries must use `INSN_CLASS_F` instead of `INSN_CLASS_F_INX` (drop the `_INX` suffix).

> **Note:** Since these entries match the pre-patched files under `/patches`, you can skip manual editing and use those directly (see [Section 5](#5-applying-the-approximate-instructions-patch)).

---

## 3. Building the 32-bit Toolchain

Fetch the toolchain sources as described in [INSTALLING.md — Section 4: RISCV-GNU-Toolchain](./INSTALLING.md#4-riscv-gnu-toolchain), then build:

```bash
cp ../riscv-opcodes/encoding.h .
./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32
sudo make
export PATH=$PATH:/opt/riscv/bin
```

---

## 4. Installing Spike and PK

### 4.1 — Spike

```bash
sudo apt-get install device-tree-compiler git
git clone https://github.com/riscv-software-src/riscv-isa-sim.git
cd riscv-isa-sim
git checkout 76ced61
cp ../riscv-opcodes/encoding.h riscv/encoding.h
```

### 4.2 — PK (Proxy Kernel)

PK is a required runtime dependency for Spike:

```bash
git clone https://github.com/riscv/riscv-pk.git
cd riscv-pk
cp ../riscv-opcodes/encoding.h machine/encoding.h
mkdir build && cd build
../configure --prefix=/opt/riscv --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei
cd ..
```

---

## 5. Applying the Approximate Instructions Patch

The required patched files are already provided under `/patches`. Copy them into the Spike source tree:

```bash
cd riscv-isa-sim
cp ../Approx_Instructions/* riscv/insns/
cp ../patches/riscv-gnu-toolchain/spike/riscv/riscv.mk.in        riscv/riscv.mk.in
cp ../patches/riscv-gnu-toolchain/spike/softfloat/softfloat.mk.in softfloat/softfloat.mk.in
cp ../patches/riscv-gnu-toolchain/spike/softfloat/internals.h     softfloat/internals.h
cp ../patches/riscv-gnu-toolchain/spike/softfloat/softfloat.h     softfloat/softfloat.h
```

> If you need to modify the approximate instructions patch, update the source files here before building.

---

## 6. Building Spike

```bash
# Run from inside riscv-isa-sim/
mkdir build
cd build
../configure --prefix=/opt/riscv
sudo make install
```

---

## 7. Testing

Verify your installation by running a binary through Spike with PK:

```bash
spike --isa=RV32I /opt/riscv/riscv32-unknown-elf/bin/pk <your_binary>
```