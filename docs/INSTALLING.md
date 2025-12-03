# RISC-V Tools Installation Guide

This guide provides step-by-step instructions for installing all required tools to work with RISC-V approximate instructions.

## Prerequisites

### System 
- Linux
- Windows with WSL
- Mac with Docker

### Hardware
- **Disk space:** Minimum 20-25 GB free (the RISC-V toolchain compilation is large).
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
# if you are going to need gem5
docker compose -f docker/compose.yaml up riscv-gem5 -d
# if you do not a simulator, you can build only the toolchain
docker compose -f docker/compose.yaml up base -d

```

After the script is done, you are ready to start using it:

#### Using the container

The docker creates a folder called `'workspace/'` and some sub-folders like:

- `opcodes/` here are the custom opcodes
- `binutils-patches/` the binutils patches
- `gcc-patches/` the gcc patches
- `tests/` useful for testing the instructions
- `projects/` useful to develop approximate computing software.

You can write your test files to `workspace/tests/`, like `addx.c`. Now, to compile it you need to enter the container  and run these commands:

```bash
riscv32-unknown-linux-gnu-gcc file.c -o file

# Then simulate it:
cd /opt/gem5/
build/RISCV/gem5.opt simple_config.py file
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
    ca-certificates \
    pre-commit \
    zlib1g \
    libprotobuf-dev \
    protobuf-compiler \
    libprotoc-dev \
    libgoogle-perftools-dev \
    libboost-all-dev \
    libhdf5-serial-dev \
    python3-pydot \
    python3-tk \
    mypy \
    m4 \
    libcapstone-dev \
    libpng-dev \
    libelf-dev \
    pkg-config \
    doxygen \
    clang-format \
    scons
```

**Notes:** this command will change depending on your system. More informations are available [here](https://github.com/riscv-collab/riscv-gnu-toolchain).

### 1. Downloading the repositories

First, we need to download the following repositories:

* [RISC-V Toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain)
* [binutils-gdb](https://github.com/bminor/binutils-gdb/tree/2bc7af1ff7732451b6a7b09462a815c3284f9613)
* [gcc](https://github.com/gcc-mirror/gcc)
* [gem5](https://github.com/gem5/gem5)
* [RISC-V SPIKE (optional if using gem5)](https://github.com/riscv-software-src/riscv-isa-sim)
* [RISC-V Proxy Kernel (only needed when using SPIKE)](https://github.com/riscv-software-src/riscv-pk)


Run this command to download them:

```bash
cd ~/.local/opt
git clone --single-branch https://github.com/riscv/riscv-gnu-toolchain.git &&
    cd riscv-gnu-toolchain &&
    git checkout 75b35f8 && 
    git submodule update --init --depth=1 --recursive binutils gcc gdb &&
    # or if using spike
    # git submodule update --init --depth=1 --recursive binutils gcc gdb spike pk
    cd ../

git clone --single-branch https://github.com/gem5/gem5.git && 
    cd gem5 && 
    git checkout ddd4ae3 &&
    cd ../
```

### 3. Patching the toolchain

In order to set up our custom instructions we need to change several files:
- `riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c`
- `riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h`
- `riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h`
- `gem5/src/arch/riscv/isa/decoder.isa`

**If using spike:**
- `riscv-gnu-toolchain/spike/riscv/riscv.mk.in`
- `riscv-gnu-toolchain/spike/softfloat/softfloat.mk.in`
- `riscv-gnu-toolchain/spike/softfloat/internals.h`
- `riscv-gnu-toolchain/spike/softfloat/softfloat.h`

#### 3.1 Copying the patches

To use the approximate instructions, just run this command to copy the patches to riscv-gnu-toolchain and gem5:

```bash
cp patches/riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h ~/.local/opt/riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h

cp patches/riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c ~/.local/opt/riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c

cp patches/riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h ~/.local/opt/riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h

cp patches/riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c ~/.local/opt/riscv-gnu-toolchainbinutils/opcodes/riscv-opc.c

cp config/simple_config.py ~/.local/opt/gem5/

cp patches/gem5/decoder.isa ~/.local/opt/gem5/src/arch/riscv/isa/decoder.isa
```

#### 3.2 Adding the instructions in spike

> If you are not using spike simulator, you can skip this section and go to section 4

First, copy all the header files at `Approx_Instructions/` directory and place them at `riscv-gnu-toolchain/spike/riscv/insns/`:
```bash
cp Approx_Instructions/*.h ~/.local/opt/riscv-gnu-toolchain/spike/riscv/insns/ # execute this command on project's root
```

Second, copy all the C files  in `Approx_Instructions/` directory and place them at `riscv-gnu-toolchain/spike/softfloat/`:
```bash
cp Approx_Instructions/*.c ~/.local/opt/riscv-gnu-toolchain/spike/softfloat/
```

### 4. RISCV-GNU-TOOLCHAIN

This is the most important part, and also the most time-taking one. Guarantee that you have done all the last steps correctly. This tool will produce all the remaining tools for us to build new softwares using custom instructions in RISC-V!

In order to set it up, run this command:

```bash
cd ~/.local/opt/riscv-gnu-toolchain

cd gcc/ &&
    ./contrib/download_prerequisites &&
    cd ../

sudo ./configure --prefix=/opt/riscv-linux --with-arch=rv32imafdc --with-abi=ilp32d --disable-multilib
sudo make linux -j$(nproc)
```

Export the riscv-gnu-toolchain for linux `bin/` folder:
```bash
export PATH=$PATH:/opt/riscv-linux/bin
```

#### 4.2. Bare-metal

> If you are not going to use Bare-metal, you should skip this section and start installing gem5 in section 5.

If you already did the first steps of section 4.1, just run the command below. Otherwise, do exactly the same as in section 4.1. The only difference is to run this command:

```bash
./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32
sudo make -j$(nproc)
```

Export the riscv-gnu-toolchain `bin/` folder:
```bash
export PATH=$PATH:/opt/riscv/bin
```

### 5. gem5

gem5 is a modern, versatile and modular tool for testing different architectures. To this date, we are primarily focused on going entirely to gem5 instead of spike.

> If you are not interested in gem5, you can skip this section and follow section 6.

Build gem5 with this command:

```bash
scons build/RISCV/gem5.opt -j $(nproc)
```

### 6. RISCV-PK (Only needed for SPIKE)

- Enter the `riscv-gnu-toolchain/pk` folder.
- Run the command below to configure and build:

```bash
mkdir build && cd build
../configure --prefix=/opt/riscv --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei
make -j$(nproc)
sudo make install
```

### 7. RISCV-ISA-SIM (SPIKE)

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
riscv32-unknown-linux-gnu-gcc -v

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
riscv32-unknown-linux-gnu-gcc file.c -o file 
./~/.local/opt/gem5/build/RISCV/gem5.opt ~/.local/opt/gem5/simple_config.py file
```

## Important Notes

- Ensure `/opt/riscv-linux/bin` is added to your PATH environment variable
- The installation process may take considerable time, especially for the toolchain compilation


## Troubleshooting

> `g++ unrecognized command line option '-std=c++2a'; did you mean '-std=c++03'?.`

**Solution**: update to gcc 13 and g++ 13

```bash
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install -y gcc-13 g++-13
```
