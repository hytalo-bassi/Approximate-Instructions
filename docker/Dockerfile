# Estágio base para instalação das deps
FROM ubuntu:18.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Instala as dependências necessárias e atualiza
RUN apt-get update && \
    apt-get install -y \
    binutils \
    autoconf \
    automake \
    autotools-dev \
    curl \
    python3 \
    libmpc-dev \
    libmpfr-dev \
    libgmp-dev \
    gawk \
    build-essential \
    software-properties-common \
    bison \
    flex \
    texinfo \
    gperf \
    libtool \
    patchutils \
    bc \
    zlib1g-dev \
    libexpat-dev \
    unzip \
    wget \
    git \
    device-tree-compiler && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instala o g++ e gcc 13
RUN add-apt-repository ppa:ubuntu-toolchain-r/test
RUN apt-get update
RUN apt-get install -y gcc-13 g++-13

# Configura o g++ e gcc 13 como padrão
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100
RUN update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 100

ENV DEBIAN_FRONTEND=
WORKDIR /root
RUN mkdir -p /workspace

# Estágio de download dos repositórios
FROM base AS download
COPY autoinstall.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/autoinstall.sh
RUN /usr/local/bin/autoinstall.sh download

# Estágio de configuração da toolchain
FROM download AS toolchain
ENV PATH="/opt/riscv/bin:${PATH}"
RUN /usr/local/bin/autoinstall.sh setup-toolchain

# Estágio de configuração dos opcodes
FROM toolchain AS opcodes
RUN /usr/local/bin/autoinstall.sh setup-opcodes

# Estágio de configuração do riscv-pk
FROM toolchain AS pk
RUN /usr/local/bin/autoinstall.sh setup-pk

# Estágio de configuração do spike
FROM pk AS spike
RUN /usr/local/bin/autoinstall.sh setup-spike

# Muda para o python2
RUN apt-get install -y python-minimal

CMD ["/bin/bash"]
