# Must be build from the root of the project
# FROM ubuntu:22.04 AS base
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    RISCV="/opt/riscv" \
    PATH="/opt/riscv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/riscv-dev
WORKDIR /root/riscv-dev

RUN git clone --depth=1 --single-branch https://github.com/riscv/riscv-gnu-toolchain.git && \
    git clone --depth=1 --single-branch https://github.com/riscv/riscv-opcodes && \
    cd riscv-gnu-toolchain && \
    git submodule update --init --depth=1 --recursive binutils gcc gdb spike pk

# We encodes in base64 the Strings to ensure Docker won't interpret it wrong.
# you can encode strings to base64 by running the command:
#   echo "<YOUR_STRING>" | base64
ARG SOFTFLOAT_MK_IN_PATCH="CiAgICBmMzJfYWRkeC5jIFwKICAgIGYzMl9zdWJ4LmMgXAogICAgc19hZGRNYWdzRjMyeC5jIFwKICAgIHNfc3ViTWFnc0YzMnguYyBcCiAgICBmMzJfbXVseC5jIFwKICAgIHNfcm91bmRQYWNrVG9GMzJ4LmMgXAogICAgc19zaG9ydFNoaWZ0UmlnaHRKYW02NHguYyBcCiAgICBmMzJfZGl2eC5jIFw="
ARG SOFTFLOAT_INTERNALS_PATCH="ZmxvYXQzMl90IHNvZnRmbG9hdF9hZGRNYWdzRjMyeCh1aW50X2Zhc3QzMl90LCB1aW50X2Zhc3QzMl90KTsKZmxvYXQzMl90IHNvZnRmbG9hdF9zdWJNYWdzRjMyeCh1aW50X2Zhc3QzMl90LCB1aW50X2Zhc3QzMl90KTsKZmxvYXQzMl90IHNvZnRmbG9hdF9yb3VuZFBhY2tUb0YzMngoYm9vbCwgaW50X2Zhc3QxNl90LCB1aW50X2Zhc3QzMl90KTsK"
ARG SOFTFLOAT_HEADERS_PATCH="ZmxvYXQzMl90IGYzMl9hZGR4KGZsb2F0MzJfdCwgZmxvYXQzMl90KTsKZmxvYXQzMl90IGYzMl9zdWJ4KGZsb2F0MzJfdCwgZmxvYXQzMl90KTsKZmxvYXQzMl90IGYzMl9tdWx4KGZsb2F0MzJfdCwgZmxvYXQzMl90KTsKZmxvYXQzMl90IGYzMl9kaXZ4KGZsb2F0MzJfdCwgZmxvYXQzMl90KTsK"
ARG SPIKE_RISCV_MK_PATCH="CglyZW14IFwKCWRpdnggXAoJbXVseCBcCglzdWJ4IFwKCWFkZHggXA=="
ARG SPIKE_RISCV_MK_FLOAT_PATCH="CglmZGl2eF9zIFwKCWZtdWx4X3MgXAoJZnN1YnhfcyBcCglmYWRkeF9zIFw="

ARG SOFTFLOAT_C_SRCS_PATTERN="softfloat_c_srcs = \\"
ARG SOFTFLOAT_INTERNALS_PATTERN="float32_t softfloat_roundPackToF32( bool, int_fast16_t, uint_fast32_t );"
ARG SOFTFLOAT_HEADERS_PATTERN="float32_t f32_add( float32_t, float32_t );"
ARG SPIKE_RISCV_MK_PATTERN="riscv_insn_ext_i = \\"
ARG SPIKE_RISCV_MK_FLOAT_PATTERN="riscv_insn_ext_f = \\"

COPY rv_approx riscv-opcodes/extensions/unratified/
RUN cd riscv-opcodes && ./parse.py -c 'unratified/rv_*'

COPY ./Approx_Instructions/*.h riscv-gnu-toolchain/spike/riscv/insns/
COPY ./scripts/update_opcodes_files.py /tmp/update_opcodes_files.py
COPY ./scripts/patch.py /tmp/patch.py
# Patches riscv-gnu-toolchain and riscv-isa-sim
RUN python3 /tmp/update_opcodes_files.py

COPY Approx_Instructions/f*.c riscv-gnu-toolchain/spike/softfloat/
COPY Approx_Instructions/s_*.c riscv-gnu-toolchain/spike/softfloat/
RUN cd riscv-gnu-toolchain/spike && \
    python3 /tmp/patch.py softfloat/softfloat.mk.in \
    "$(echo -n ${SOFTFLOAT_MK_IN_PATCH} | base64 -d)" \
    "$SOFTFLOAT_C_SRCS_PATTERN" \
    -a -b && \
    python3 /tmp/patch.py softfloat/internals.h \
    "$(echo -n ${SOFTFLOAT_INTERNALS_PATCH} | base64 -d)" \
    "${SOFTFLOAT_INTERNALS_PATTERN}" \
    -a && \
    python3 /tmp/patch.py softfloat/softfloat.h \
    "$(echo -n ${SOFTFLOAT_HEADERS_PATCH} | base64 -d)" \
    "${SOFTFLOAT_HEADERS_PATTERN}" && \
    python3 /tmp/patch.py riscv/riscv.mk.in \
    "$(echo -n ${SPIKE_RISCV_MK_PATCH} | base64 -d)" \
    "${SPIKE_RISCV_MK_PATTERN}" -a -b && \
    python3 /tmp/patch.py riscv/riscv.mk.in \
    "$(echo -n ${SPIKE_RISCV_MK_FLOAT_PATCH} | base64 -d)" \
    "${SPIKE_RISCV_MK_FLOAT_PATTERN}" -a -b


RUN cd riscv-gnu-toolchain && \
    ./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32 && \
    make -j$(nproc)

RUN cd riscv-gnu-toolchain/pk && \
    mkdir -p build && \
    cd build && \
    ../configure --prefix=${RISCV} --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei && \
    make -j$(nproc) && \
    make install

RUN cd riscv-gnu-toolchain/spike && \
    mkdir build && \
    cd build/ && \
    ../configure --prefix=${RISCV} && \
    make -j$(nproc) && \
    make install

RUN mkdir -p /workspace

# Metadata
LABEL maintainer="RISC-V Development Environment" \
      description="RISC-V toolchain with approximate computing instructions" \
      version="1.0" \
      base_os="ubuntu:22.04" \
      toolchain_arch="rv32imafdc"
