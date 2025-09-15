# RISC-V Tools Installation Guide

This guide provides step-by-step instructions for installing all required tools to work with RISC-V approximate instructions.

## Required Tools

They're two (or three if you like) possible ways to install the tools:
- Docker (recommended)
- By hand (or script in debian-based OSes)

### Docker

To install the tools in a docker container you first need to install Docker and Docker compose. [Click here to install Docker](https://docs.docker.com/engine/install/) and follow the steps to download it in your platform. After downloading docker you should download docker-compose following [these steps](https://docs.docker.com/compose/install/)

After installing docker and docker-compose, you can start the installation process by running:

```bash
./scripts/dev start
```

After the script is done, you are ready to start testing it. Also, the docker creates a folder called `'workspace/'` and some sub-folders like:

- `opcodes/` here are the custom opcodes (must be activated at compose.yaml)
- `binutils-patches/` the binutils patches
- `gcc-patches/` the gcc patches
- `tests/` useful for testing the instructions
- `projects/` useful to develop approximate computing software.

#### Downgrading opcodes

The project is currently working with a old version of opcodes and we need to downgrade it in the docker container. In order to do so, the opcodes binding should be disabled (it already is by default) and then:

```bash
./scripts/dev shell                                         # enters the container
cd /root/riscv-dev/riscv-opcodes/                           # enters the opcode git repo
git reset --hard 7c3db437d8d3b6961f8eb2931792eaea1c469ff3   # downgrades the opcode
```

**Note**: If this code raises a warning, it's probably because the `opcodes/` binding is yet enabled.

After downgrading the opcodes, you can re-enable the `opcodes/` binding:
```bash
exit                # quits the container
./scripts/dev stop  # stops the container
    # 1. opens the docker/compose.yaml
    # 2. replace the following line:
    # # - ../workspace/opcodes:/root/riscv-dev/riscv-opcodes/opcodes:rw
    # with:
    # - ../workspace/opcodes:/root/riscv-dev/riscv-opcodes/opcodes:rw
./scripts/dev start # start container, the binding should be enabled
```

### Using `Autoinstall.sh` script

Another way of downloading and setting everything up is by using the installation script.

In Ubuntu:
```bash
sudo ./docker/autoinstall.sh download
sudo ./docker/autoinstall.sh setup-env # this can take really long
```

If you are not in Ubuntu, then the installation is done by hand following each step described below:

### 1. RISC-V Toolchain

Available at: [RISC-V Toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain)

**Install dependencies:**
```bash
sudo apt-get install autoconf automake autotools-dev curl python3 libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev git
```

**Clone and build:**
```bash
git clone https://github.com/riscv/riscv-gnu-toolchain
cd riscv-gnu-toolchain
./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32
sudo make
cd ..
export PATH=$PATH:/opt/riscv/bin
```

### 2. RISCV-OPCODES

**Installation:**
- Access: https://github.com/riscv/riscv-opcodes.git
- Download and copy contents to the riscv-opcodes folder (replace existing encoding.h file)
- Use version: https://github.com/riscv/riscv-opcodes/tree/7c3db437d8d3b6961f8eb2931792eaea1c469ff3

### 3. RISCV-OPENOCD

```bash
git clone https://github.com/riscv/riscv-openocd.git
```

### 4. RISCV-PK

```bash
export PATH=$PATH:/opt/riscv/bin
git clone https://github.com/riscv/riscv-pk.git
cd riscv-pk
mkdir build && cd build
../configure --prefix=/opt/riscv --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei
```

**Complete the build:**
```bash
make
sudo make install
cd ../..
```

### 6. RISCV-ISA-SIM (SPIKE)

```bash
git clone https://github.com/riscv-software-src/riscv-isa-sim.git
cd riscv-isa-sim
sudo apt-get install device-tree-compiler
mkdir build && cd build
../configure --prefix=/opt/riscv
make
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

## Important Notes

- Ensure `/opt/riscv/bin` is added to your PATH environment variable
- Some configurations may require Python 2.7 for certain operations
- All tools should be installed with the same prefix (`/opt/riscv`) for consistency
- The installation process may take considerable time, especially for the toolchain compilation


## Troubleshooting

> `g++ unrecognized command line option '-std=c++2a'; did you mean '-std=c++03'?.`

**Solution**: update to gcc 13 and g++ 13

```bash
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install -y gcc-13 g++-13
```
