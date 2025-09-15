# Setup RISC-V GNU Toolchain to include approximate instructions

### Step 1: Add Opcodes

**Notes: you should downgrade the opcodes repo before adding the instructions! Follow the [instalation guide](./docs/INSTALLING.md) to downgrade it.**

Navigate to the `riscv-opcodes` directory and add the following opcodes to `riscv-opcodes/opcodes`:

Write the content below in some file called `"opcodes.txt"`:
**Integer Instructions:**
```
addx    rd rs1 rs2 31..25=1  14..12=0 6..2=0x0A 1..0=3
subx    rd rs1 rs2 31..25=1  14..12=0 6..2=0x0B 1..0=3
mulx    rd rs1 rs2 31..25=1  14..12=0 6..2=0x1C 1..0=3
divx    rd rs1 rs2 31..25=1  14..12=0 6..2=0x1D 1..0=3
remx    rd rs1 rs2 31..25=1  14..12=0 6..2=0x1E 1..0=3
```

**Floating-Point Instructions:**
```
faddx.s   rd rs1 rs2      31..27=0x10 rm       26..25=0 6..2=0x14 1..0=3
fsubx.s   rd rs1 rs2      31..27=0x11 rm       26..25=0 6..2=0x14 1..0=3
fmulx.s   rd rs1 rs2      31..27=0x12 rm       26..25=0 6..2=0x14 1..0=3
fdivx.s   rd rs1 rs2      31..27=0x13 rm       26..25=0 6..2=0x14 1..0=3
```

**Generate instruction information:**

Change `/path/to/opcodes` with the actual path to the `opcodes.txt` file you wrote before.

```bash
cd  /root/riscv-dev/riscv-opcodes # if you are using the docker
cat /path/to/opcodes/opcodes.txt |  python2 parse-opcodes -c > /path/to/opcodes/instructionInfo.h
```

A new file called `"instructionInfo.h"` should have been created along with `opcodes.txt`.

### Step 2: Verify Generated Definitions

Check that `instructionInfo.h` contains the following definitions:

**Integer Instructions:**
```c
#define MATCH_ADDX 0x200002b
#define MASK_ADDX  0xfe00707f
#define MATCH_SUBX 0x200002f
#define MASK_SUBX  0xfe00707f
#define MATCH_MULX 0x2000073
#define MASK_MULX  0xfe00707f
#define MATCH_DIVX 0x2000077
#define MASK_DIVX  0xfe00707f
#define MATCH_REMX 0x200007b
#define MASK_REMX  0xfe00707f

// Declarations
DECLARE_INSN(addx, MATCH_ADDX, MASK_ADDX)
DECLARE_INSN(subx, MATCH_SUBX, MASK_SUBX)
DECLARE_INSN(mulx, MATCH_MULX, MASK_MULX)
DECLARE_INSN(divx, MATCH_DIVX, MASK_DIVX)
DECLARE_INSN(remx, MATCH_REMX, MASK_REMX)
```

**Floating-Point Instructions:**
```c
#define MATCH_FADDX_S 0x80000053
#define MASK_FADDX_S  0xfe00007f
#define MATCH_FSUBX_S 0x88000053
#define MASK_FSUBX_S  0xfe00007f
#define MATCH_FMULX_S 0x90000053
#define MASK_FMULX_S  0xfe00007f
#define MATCH_FDIVX_S 0x98000053
#define MASK_FDIVX_S  0xfe00007f

// Declarations
DECLARE_INSN(faddx_s, MATCH_FADDX_S, MASK_FADDX_S)
DECLARE_INSN(fsubx_s, MATCH_FSUBX_S, MASK_FSUBX_S)
DECLARE_INSN(fmulx_s, MATCH_FMULX_S, MASK_FMULX_S)
DECLARE_INSN(fdivx_s, MATCH_FDIVX_S, MASK_FDIVX_S)
```

### Step 3: Update Header Files

Add the definitions to the following files:
- `riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h`
- `riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h`

Copy the same definitions from Step 2 into these files.

If you are using the docker:

```bash
./scripts/dev shell # starts and enter the docker shell
cat /path/to/opcodes/instructionInfo.h >> /root/riscv-dev/riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h
cat /path/to/opcodes/instructionInfo.h >> /root/riscv-dev/riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h
# appends to the bottom of both files the content of instructionInfo.h
```

### Step 4: Update Opcode Files

Add instruction specifications just as before to:
- `riscv-gnu-toolchain/riscv-gdb/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/riscv-binutils/opcodes/riscv-opc.c`

**Note:** For riscv-gdb, remove `_INX` from `INSN_CLASS_F_INX`.

**Integer Instructions:**
```c
{"addx",    0, INSN_CLASS_I, "d,s,t", MATCH_ADDX, MASK_ADDX, match_opcode, 0},
{"subx",    0, INSN_CLASS_I, "d,s,t", MATCH_SUBX, MASK_SUBX, match_opcode, 0},
{"mulx",    0, INSN_CLASS_I, "d,s,t", MATCH_MULX, MASK_MULX, match_opcode, 0},
{"divx",    0, INSN_CLASS_I, "d,s,t", MATCH_DIVX, MASK_DIVX, match_opcode, 0},
{"remx",    0, INSN_CLASS_I, "d,s,t", MATCH_REMX, MASK_REMX, match_opcode, 0},
```

**Floating-Point Instructions:**
```c
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FADDX_S|MASK_RM, MASK_FADDX_S|MASK_RM, match_opcode, 0},
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FADDX_S, MASK_FADDX_S, match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FSUBX_S|MASK_RM, MASK_FSUBX_S|MASK_RM, match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FSUBX_S, MASK_FSUBX_S, match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FMULX_S|MASK_RM, MASK_FMULX_S|MASK_RM, match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FMULX_S, MASK_FMULX_S, match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FDIVX_S|MASK_RM, MASK_FDIVX_S|MASK_RM, match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FDIVX_S, MASK_FDIVX_S, match_opcode, 0},
```

### Step 5: Rebuild RISC-V GNU Toolchain

```bash
cd riscv-gnu-toolchain
make clean
./configure --prefix=/opt/riscv --with-arch=rv32i --with-abi=ilp32
# OR
./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32
sudo make
```

**Note:** using the autoinstall.sh setup-toolchain will also work.

### Step 6: Test Toolchain Installation

Create a test file `test/addx.c`:

```c
#include <stdio.h>

int main(){
    int a, b, addx_result, subx_result;
    a = 5;
    b = 2;
    
    asm volatile (
        "addx   %[z], %[x], %[y]\n\t"
        : [z] "=r" (addx_result)
        : [x] "r" (a), [y] "r" (b)
    );
    
    asm volatile ( 
        "subx   %[z], %[x], %[y]\n\t"
        : [z] "=r" (subx_result)
        : [x] "r" (a), [y] "r" (b)
    );
    
    printf("ADDX => 5+2=%d\n", addx_result);
    printf("SUBX => 5-2=%d\n", subx_result);
    return 0;
}
```

**Compile and test:**
```bash
riscv32-unknown-elf-gcc addx.c -O1 -march=rv32imafdc -o addx 
riscv32-unknown-elf-objdump -dC addx > addx.dump
```
