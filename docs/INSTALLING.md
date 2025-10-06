# RISC-V Tools Installation Guide

This guide provides step-by-step instructions for installing all required tools to work with RISC-V approximate instructions.

## Prerequisites

### System 
- Linux
- Windows with WSL
- Mac with Docker

### Hardware
- **Disk space:** Minimum 10-15 GB free (the RISC-V toolchain compilation is large).
- **RAM**: At least 4 GB (8 GB recommended for parallel compilation with -j$(nproc))
- **CPU**: Multi-core processor recommended (compilation can take 30 minutes to several hours)

### Software
If using Docker (recommended path):

- Docker Engine (latest stable version)
- Docker Compose
- Basic familiarity with Docker commands

If installing manually:

- Root/sudo access
- Git (for cloning repositories)
- Internet connection (for downloading repositories and dependencies)
- Basic command-line proficiency
- Text editor for patching files

### Knowledge

Basic understanding of:

- Command line operations
- File navigation and editing
- Environment variables (PATH)
- C/C++ compilation concepts (helpful)

### Time Requirement

Docker method: 30 minutes to 2.5 hours (depending on system performance)
Manual installation: 4+ hours (depending on system performance)

## Installation options

There are two possible ways to install the tools:
- Docker (recommended)
- By hand

### Docker

To install the tools in a docker container you first need to install Docker and Docker compose. [Click here to install Docker](https://docs.docker.com/engine/install/) and follow the steps to download it in your platform. After downloading docker you should download docker-compose following [these steps](https://docs.docker.com/compose/install/)

After installing docker and docker-compose, you can start the installation process by running:

```bash
./scripts/dev start
```

After the script is done, you are ready to start using it:

#### Using the container

The docker creates a folder called `'workspace/'` and some sub-folders like:

- `opcodes/` here are the custom opcodes
- `binutils-patches/` the binutils patches
- `gcc-patches/` the gcc patches
- `tests/` useful for testing the instructions
- `projects/` useful to develop approximate computing software.

You can write your test files to `workspace/tests/`, like `addx.c`. Now, to compile it you need to enter the container (run `./scripts/dev shell` to enter shell) and run these commands:

```bash
riscv32-unknown-elf-gcc /path/to/file.c -O1 -march=rv32imafdc -o file -lm 
spike --isa=RV32IMAFDC /opt/riscv/riscv32-unknown-elf/bin/pk file
```

If you do not want to use Docker Compose, then the installation is done by hand following each step described below:

### 0. Install dependencies

You can install the dependencies running the command below (Debian-based OSes):
```bash
sudo apt-get update && sudo apt-get install \
    build-essential \
    gcc \
    g++ \
    autoconf \
    automake \
    autotools-dev \
    libtool \
    git \
    make \
    cmake \
    bison \
    flex \
    gawk \
    texinfo \
    gperf \
    patchutils \
    bc \
    libmpc-dev \
    libmpfr-dev \
    libgmp-dev \
    zlib1g-dev \
    libexpat1-dev \
    libzstd-dev \
    libpthread-stubs0-dev \
    libisl-dev \
    unzip \
    python3 \
    python3-matplotlib \
    python3-dev \
    python3-pip \
    python3-venv \
    device-tree-compiler \
    curl \
    wget \
    libboost-system-dev \
    libboost-regex-dev \
    ca-certificates 
```

**Notes:** this command will change depending on your system. More informations are available [here](https://github.com/riscv-collab/riscv-gnu-toolchain).

### 1. Downloading the repositories

First, we need to download the following repositories:

* [RISC-V Toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain)
* [RISC-V SPIKE](https://github.com/riscv-software-src/riscv-isa-sim)
* [RISC-V Proxy Kernel](https://github.com/riscv-software-src/riscv-pk)
* [RISC-V Opcodes](https://github.com/riscv/riscv-opcodes)
* [binutils-gdb](https://github.com/bminor/binutils-gdb/tree/2bc7af1ff7732451b6a7b09462a815c3284f9613)
* [gcc](https://github.com/gcc-mirror/gcc)

Run this command to download them:
```bash
git clone --depth=1 --single-branch https://github.com/riscv/riscv-gnu-toolchain.git && \
git clone --depth=1 --single-branch https://github.com/riscv/riscv-opcodes && \
cd riscv-gnu-toolchain && \
git submodule update --init --depth=1 --recursive binutils gcc gdb spike pk
```

### 2. RISCV-OPCODES

We are going to use that tool to generate the opcodes header file.

**Generating:**
- Enter the recently downloaded repository `riscv-opcodes`
- Copy the `rv_approx` file from project's root and move it to the riscv-opcodes' `extensions/unratified` folder.
- Run the command below:

```bash
./parse.py -c 'unratified/rv_*'
```

### 3. Patching the toolchain

In order to set up our custom instructions we need to change several files:
- `riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h`
- `riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h`
- `riscv-gnu-toolchain/spike/riscv/riscv.mk.in`
- `riscv-gnu-toolchain/spike/softfloat/softfloat.mk.in`
- `riscv-gnu-toolchain/spike/softfloat/internals.h`
- `riscv-gnu-toolchain/spike/softfloat/softfloat.h`

Copy the custom instructions' definitions from the generated `riscv-opcodes/encoding.out.h`, they should look like:
```c
...
// These comments are not really present at the encoding file, they're here to help you know where to place each code.
// DECLARATION SECTION
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
#define MATCH_FADDX_S 0x80000053
#define MASK_FADDX_S  0xfe00007f
#define MATCH_FSUBX_S 0x88000053
#define MASK_FSUBX_S  0xfe00007f
#define MATCH_FMULX_S 0x90000053
#define MASK_FMULX_S  0xfe00007f
#define MATCH_FDIVX_S 0x98000053
#define MASK_FDIVX_S  0xfe00007f
// END OF DECLARATION SECTION
...
// INSTRUCTIONS SECTION
DECLARE_INSN(addx, MATCH_ADDX, MASK_ADDX)
DECLARE_INSN(subx, MATCH_SUBX, MASK_SUBX)
DECLARE_INSN(mulx, MATCH_MULX, MASK_MULX)
DECLARE_INSN(divx, MATCH_DIVX, MASK_DIVX)
DECLARE_INSN(remx, MATCH_REMX, MASK_REMX)
DECLARE_INSN(faddx_s, MATCH_FADDX_S, MASK_FADDX_S)
DECLARE_INSN(fsubx_s, MATCH_FSUBX_S, MASK_FSUBX_S)
DECLARE_INSN(fmulx_s, MATCH_FMULX_S, MASK_FMULX_S)
DECLARE_INSN(fdivx_s, MATCH_FDIVX_S, MASK_FDIVX_S)
// END OF INSTRUCTIONS SECTION
...
```

#### 3.1 Patching binutils and gdb headers

Enter the files
- `riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h`
- `riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h`

And find for the `#define RISCV_ENCODING_H` line in each file, copy the contents of the `// DECLARATIONS SECTION` after the line you found, ensure that you are following the header syntax.

Then, look for the `#ifdef DECLARE_INSN` line in each file, copy the contents of the `// INSTRUCTIONS SECTION` after the line you found, ensure that you are following the header syntax.


#### 3.2 Patching binutils and gdb c files

Enter the files
- `riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c`

Look for `{0, 0, INSN_CLASS_NONE, 0, 0, 0, 0, 0}` line in each file, copy the following content BEFORE the line you found, ensure that you are following the C syntax, (for the `gdb` file remove the `_INX` ending):

```c
// Integer instructions
{"addx",    0, INSN_CLASS_I, "d,s,t", MATCH_ADDX, MASK_ADDX, match_opcode, 0},
{"subx",    0, INSN_CLASS_I, "d,s,t", MATCH_SUBX, MASK_SUBX, match_opcode, 0},
{"mulx",    0, INSN_CLASS_I, "d,s,t", MATCH_MULX, MASK_MULX, match_opcode, 0},
{"divx",    0, INSN_CLASS_I, "d,s,t", MATCH_DIVX, MASK_DIVX, match_opcode, 0},
{"remx",    0, INSN_CLASS_I, "d,s,t", MATCH_REMX, MASK_REMX, match_opcode, 0},
// Float instructions (remove the _INX ending in gdb files)
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FADDX_S|MASK_RM, MASK_FADDX_S|MASK_RM,   match_opcode, 0},
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FADDX_S,         MASK_FADDX_S,           match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FSUBX_S|MASK_RM, MASK_FSUBX_S|MASK_RM,   match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FSUBX_S,         MASK_FSUBX_S,           match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FMULX_S|MASK_RM, MASK_FMULX_S|MASK_RM,   match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FMULX_S,         MASK_FMULX_S,           match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FDIVX_S|MASK_RM, MASK_FDIVX_S|MASK_RM,   match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FDIVX_S,         MASK_FDIVX_S,           match_opcode, 0},
```

**Notes:** do not forget to remove the `_INX` ending from `gdb` files.


#### 3.3 Patching spike files


First, enter `riscv-gnu-toolchain/spike/riscv/riscv.mk.in` file, find the lines containing `riscv_insn_ext_i = \` and `riscv_insn_ext_f = \` and update it to look like this:
```makefile
riscv_insn_ext_i = \ # append before the list
    addx \
    subx \
    mulx \
    divx \
    remx \
    # ... other instructions

riscv_insn_ext_f = \ # append before the list
    faddx_s \
    fsubx_s \
    fmulx_s \
    fdivx_s \
    # ... other instructions
```

Second, enter `riscv-gnu-toolchain/spike/softfloat/softfloat.mk.in` find the line containing `softfloat_c_srcs = \` then edit:

```makefile
softfloat_c_srcs = \
    # append these before the list
    f32_addx.c \
    f32_subx.c \
    s_addMagsF32x.c \
    s_subMagsF32x.c \
    f32_mulx.c \
    s_roundPackToF32x.c \
    s_shortShiftRightJam64x \
    f32_divx.c \
```

Third, enter `riscv-gnu-toolchain/spike/softfloat/internals.h` and edit:
```c
...
float32_t softfloat_roundPackToF32( bool, int_fast16_t, uint_fast32_t ); // place the content after this line
// For faddx and fsubx
float32_t softfloat_addMagsF32x(uint_fast32_t, uint_fast32_t);
float32_t softfloat_subMagsF32x(uint_fast32_t, uint_fast32_t);

// For fmulx
float32_t softfloat_roundPackToF32x(bool, int_fast16_t, uint_fast32_t);
```

Fourth, do the same to `riscv-gnu-toolchain/spike/softfloat/softfloat.h`:

```c

// Add these functions
float32_t f32_addx(float32_t, float32_t);
float32_t f32_subx(float32_t, float32_t);
float32_t f32_mulx(float32_t, float32_t);
float32_t f32_divx(float32_t, float32_t);

// Before this line
float32_t f32_add( float32_t, float32_t ); 

```

### 4. RISCV-GNU-TOOLCHAIN

- Enter the `riscv-gnu-toolchain` folder.
- Check if the files `binutils/opcodes/riscv-opc.c`, `gdb/opcodes/riscv-opc.c`, `gdb/include/opcode/riscv-opc.h`, `binutils/include/opcode/riscv-opc.h` have the custom instructions definitions (see section 3.2).
- Run the command below:

```bash
./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32
sudo make -j$(nproc)
```


Export the riscv-gnu-toolchain `bin/` folder:
```bash
export PATH=$PATH:/opt/riscv/bin
```

### 5. RISCV-PK

- Enter the `riscv-gnu-toolchain/pk` folder.
- Run the command below to configure and build:

```bash
mkdir build && cd build
../configure --prefix=/opt/riscv --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei
make -j$(nproc)
sudo make install
```

### 6. RISCV-ISA-SIM (SPIKE)

- Enter the `riscv-gnu-toolchain/spike` folder.
- Check if the files `riscv/riscv.mk.in`, `softfloat/softfloat.mk.in`, `softfloat/internals.h`, `softfloat/softfloat.h` have the custom instructions modifications (see section 3.3).
- Run the command below to configure and build:

```bash
mkdir build && cd build
../configure --prefix=/opt/riscv
make -j$(nproc)
sudo make install
```

## Verification

After installation, verify that all tools are properly installed by checking their versions:

```bash
# Check RISC-V GCC
riscv32-unknown-elf-gcc --version

# Check SPIKE
spike --help

# Verify PATH
echo $PATH
```

Then verify if the approximate instructions are properly set by writing a test `addx.c` file:

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

Test it (should not raise any error):
```bash
riscv32-unknown-elf-gcc addx.c -O1 -march=rv32imafdc -o addx -lm 
spike --isa=RV32IMAFDC /opt/riscv/riscv32-unknown-elf/bin/pk addx
```

## Important Notes

- Ensure `/opt/riscv/bin` is added to your PATH environment variable
- The installation process may take considerable time, especially for the toolchain compilation


## Troubleshooting

> `g++ unrecognized command line option '-std=c++2a'; did you mean '-std=c++03'?.`

**Solution**: update to gcc 13 and g++ 13

```bash
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install -y gcc-13 g++-13
```

> `Error when compiling riscv-gnu-toolchain: make: *** [Makefile:609: stamps/build-binutils-newlib] Error 2`

**Solution**: check the header files and c-files changed at Step 3 and 4, their content might be out of position; specially for the header files: `DECLARE_INSN*` should be within `#ifdef DECLARE_INSN` and the last `#endif`.

> When building Spike, if build errors occur (e.g., `HGATP_MODE_SV57X4` out of scope), check for missing declarations in the new instruction implementations (see section 3. Patching the toolchain).
