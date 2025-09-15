#!/bin/bash

# Termina o programa em qualquer erro
set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

OLD_OPCODES_URL='https://github.com/riscv/riscv-opcodes/archive/7c3db437d8d3b6961f8eb2931792eaea1c469ff3.zip'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCESSO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_prerequisites() {
    print_status "Verificando pré-requisitos..."
    
    if ! command_exists git; then
        print_error "git não está instalado. Por favor, instale o git primeiro."
        exit 1
    fi
    
    if ! command_exists make; then
        print_warning "make não está instalado. Por favor, instale o make primeiro."
	exit 1
    fi

    if ! command_exists unzip; then
        print_warning "unzip não está instalado. Por favor, instale o unzip primeiro."
	exit 1
    fi

    print_success "Verificação de pré-requisitos concluída"
}

clone_repo() {
    local repo_url=$1
    local repo_name=$2
    local description=$3
    
    print_status "Instalando: $description"
    print_status "Repositório: $repo_url"
    
    if [ -d "$repo_name" ]; then
        print_warning "Diretório $repo_name já existe. Atualizando..."
        cd "$repo_name"
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || {
            print_warning "Não foi possível atualizar o repositório. Continuando com versão existente."
        }
        cd ..
    else
        print_status "Clonando $repo_name..."
        if git clone "$repo_url" "$repo_name"; then
            print_success "Clonado $repo_name com sucesso"
        else
            print_error "Falha ao clonar $repo_name"
            return 1
        fi
    fi
    
    echo
}

install_riscv_repos() {
    print_status "Iniciando instalação dos repositórios RISC-V..."
    echo
    
    INSTALL_DIR="riscv-dev"
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        print_status "Diretório de instalação criado: $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    
    repos=(
        "https://github.com/riscv/riscv-gnu-toolchain|riscv-gnu-toolchain|Toolchain GNU RISC-V - Compilador GCC completo para RISC-V"
        "https://github.com/riscv/riscv-opcodes.git|riscv-opcodes|Opcodes RISC-V - Definições da arquitetura de instruções"
        # "https://github.com/riscvarchive/riscv-fesvr.git|riscv-fesvr|Frontend Server RISC-V - Interface para simuladores RISC-V"
	    "https://github.com/riscv/riscv-pk.git|riscv-pk|Proxy Kernel e Boot Loader do RISC-V - Ambiente de execução de binários ELF"
	    "https://github.com/riscv-software-src/riscv-isa-sim.git|spike|Simulador de RISC-V ISA"
    )
    
    for repo_info in "${repos[@]}"; do
        IFS='|' read -r url name description <<< "$repo_info"
        clone_repo "$url" "$name" "$description"
    done
    
    cd ..
}

setup_toolchain() {
    print_status "Configurando o toolchain RISC-V..."
    
    cd riscv-dev/riscv-gnu-toolchain
    
    print_status "Configurando com arquitetura rv32imafdc e ABI ilp32..."
    if ./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32; then
        print_success "Configuração concluída"
    else
        print_error "Falha na configuração do toolchain"
        exit 1
    fi
    
    # Detecta número de cores para compilação paralela
    CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    print_status "Compilando toolchain com $CORES cores paralelos... (isso pode levar várias horas)"
    
    if make -j"$CORES"; then
        print_success "Toolchain compilado com sucesso"
    else
        print_error "Falha na compilação do toolchain"
        exit 1
    fi
    
    cd ../..
    
    print_status "Adicionando /opt/riscv/bin ao PATH..."
    export PATH=$PATH:/opt/riscv/bin
    
    print_success "Configuração do toolchain concluída!"
}

setup_opcodes() {
    print_status "Configurando riscv-opcodes..."

    cd riscv-dev/riscv-opcodes

    print_status "Mudando para versão antiga do RISC-V opcodes (7c3db437d8d3b6961f8eb2931792eaea1c469ff3)..."

    if git reset --hard 7c3db437d8d3b6961f8eb2931792eaea1c469ff3; then
	    print_success "Versão antiga instalada!"
    else
	    print_error "Não foi possível baixar versão antiga!"
	    exit 1
    fi

    print_success "Configuração do riscv-opcodes concluída!"
}

setup_fesvr() {
    # O fesvr foi depreciado e absorvido pelo spike.
    print_status "Configurando riscv-fesvr..."

    cd riscv-dev/riscv-fesvr

    mkdir build && cd build

    if ! ../configure --prefix=/opt/riscv; then
	    print_error "Configuração do riscv-fesvr falhou!"
	    exit 1
    fi

    print_status "Instalando riscv-fesvr..."

    CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    print_status "Compilando riscv-fesvr com $CORES cores paralelos..."
    
    if make install -j"$CORES"; then
        print_success "riscv-fesvr compilado com sucesso"
    else
        print_error "Falha na compilação do riscv-fesvr"
        exit 1
    fi

    cd ../..

    print_success "risc-fesvr instalado e configurado com sucesso!"
}

setup_pk() {
    print_status "Configurando riscv-pk..."

    cd riscv-dev/riscv-pk

    mkdir build
    cd build

    if ! ../configure --prefix=/opt/riscv --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei; then
	    print_error "Configuração do riscv-pk falhou!"
	    exit 1
    fi

    CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    print_status "Compilando riscv-pk com $CORES cores paralelos..."
    
    if make -j"$CORES"; then
        print_success "riscv-pk compilado com sucesso"
    else
        print_error "Falha na compilação do riscv-pk"
        exit 1
    fi

    print_status "Instalando riscv-pk..."

    if make install -j"$CORES"; then
        print_success "riscv-pk instalado com sucesso"
    else
        print_error "Falha na instalação do riscv-pk"
        exit 1
    fi

    cd ../../..
}


setup_spike() {
    print_status "Configurando riscv-spike..."

    cd riscv-dev/spike

    mkdir build
    cd build

    if ! ../configure --prefix=/opt/riscv; then
	    print_error "Configuração do spike falhou!"
	    exit 1
    fi

    # CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    # print_status "Compilando spike com $CORES cores paralelos..."
    
    print_status "Compilando spike..."
    
    # if make -j"$CORES"; then removes parallelism
    if make; then
        print_success "spike compilado com sucesso"
    else
        print_error "Falha na compilação do spike"
        exit 1
    fi

    print_status "Instalando spike..."

    # if make install -j"$CORES"; then removes parallelism
    if make install; then
        print_success "Spike instalado com sucesso"
    else
        print_error "Falha na compilação do spike"
        exit 1
    fi

    cd ../../..
}

setup_environment() {
	setup_toolchain
	setup_opcodes
	# setup_fesvr
	setup_pk
	setup_spike
}

show_post_install_info() {
    print_success "Instalação concluída!"
    echo
    print_status "Repositórios instalados no diretório: $PWD/riscv-dev"
    echo
    print_warning "Nota: A compilação do toolchain pode levar várias horas (4+ hrs) e requer muito espaço em disco."
}

download() {
    check_prerequisites
    install_riscv_repos
    show_post_install_info
}

all() {
    download    
    print_success "Repositórios RISC-V instalados com sucesso!"

    print_status "Instalando e configurando ambiente..."
    setup_environment
    print_success "Ambiente de desenvolvimento configurado e instalado!"
}

show_help() {
    echo "=================================================="
    echo "Configuração do Ambiente de Desenvolvimento RISC-V"
    echo "=================================================="
    echo
    echo -e "${GREEN}DESCRIÇÃO:${NC}"
    echo "  Este script automatiza a instalação e configuração de um ambiente completo"
    echo "  de desenvolvimento RISC-V, incluindo toolchain GNU, simulador Spike e"
    echo "  ferramentas associadas."
    echo
    echo -e "${GREEN}USO:${NC}"
    echo "  $0 <comando>"
    echo
    echo -e "${GREEN}COMANDOS DISPONÍVEIS:${NC}"
    echo
    echo -e "  ${YELLOW}all${NC}               Executa instalação completa (download + configuração)"
    echo "                     • Baixa todos os repositórios"
    echo "                     • Compila e instala o toolchain GNU"
    echo "                     • Configura opcodes, proxy kernel e Spike"
    echo "                     ${RED}AVISO: Pode levar várias horas!${NC}"
    echo
    echo -e "  ${YELLOW}download${NC}          Apenas baixa os repositórios sem compilar"
    echo "                     • Clona/atualiza todos os repositórios necessários"
    echo "                     • Verifica pré-requisitos do sistema"
    echo "                     • Útil para preparar o ambiente sem compilar"
    echo
    echo -e "  ${YELLOW}setup-env${NC}        Configura ambiente completo (sem download)"
    echo "                     • Executa todas as etapas de configuração"
    echo "                     • Use após 'download' ou se repositórios já existem"
    echo
    echo -e "${GREEN}COMANDOS INDIVIDUAIS DE CONFIGURAÇÃO:${NC}"
    echo
    echo -e "  ${YELLOW}setup-toolchain${NC}  Compila e instala o toolchain GNU RISC-V"
    echo "                     • Arquitetura: rv32imafdc"
    echo "                     • ABI: ilp32"
    echo "                     • Instala em: /opt/riscv"
    echo
    echo -e "  ${YELLOW}setup-opcodes${NC}    Configura definições de instruções RISC-V"
    echo "                     • Baixa versão específica compatível"
    echo "                     • Substitui encoding.h e parse-opcodes"
    echo
    echo -e "  ${YELLOW}setup-pk${NC}         Instala o Proxy Kernel RISC-V"
    echo "                     • Ambiente de execução para binários ELF"
    echo "                     • Necessário para executar programas no Spike"
    echo
    echo -e "  ${YELLOW}setup-spike${NC}      Instala o simulador Spike RISC-V"
    echo "                     • Simulador oficial da arquitetura RISC-V"
    echo "                     • Usado para executar e debugar programas"
    echo
    echo -e "${GREEN}PRÉ-REQUISITOS:${NC}"
    echo "  • git - Para clonagem dos repositórios"
    echo "  • make - Para compilação"
    echo "  • unzip - Para extração de arquivos"
    echo "  • wget - Para download de dependências"
    echo "  • Ferramentas de compilação (gcc, g++, etc.)"
    echo "  • Python 3 e pip (para algumas dependências)"
    echo
    echo -e "${GREEN}ESTRUTURA DE DIRETÓRIOS CRIADA:${NC}"
    echo "  riscv-dev/"
    echo "  ├── riscv-gnu-toolchain/    # Toolchain GNU completo"
    echo "  ├── riscv-opcodes/          # Definições de instruções"
    echo "  ├── riscv-fesvr/            # Frontend server (depreciado)"
    echo "  ├── riscv-pk/               # Proxy kernel"
    echo "  └── spike/                  # Simulador RISC-V"
    echo
    echo -e "${GREEN}EXEMPLO DE USO:${NC}"
    echo "  # Instalação completa (recomendado para primeira vez)"
    echo "  $0 all"
    echo
    echo "  # Instalação em etapas"
    echo "  $0 download          # Baixa repositórios"
    echo "  $0 setup-toolchain   # Compila toolchain (demorado)"
    echo "  $0 setup-spike       # Configura simulador"
    echo
    echo -e "${GREEN}NOTAS IMPORTANTES:${NC}"
    echo "  • A compilação completa pode levar ${RED}4+ horas${NC} dependendo do hardware"
    echo "  • Necessário ${RED}10+ GB${NC} de espaço livre em disco"
    echo "  • Requer permissões de root para escrever em /opt/riscv"
    echo "  • O PATH será automaticamente configurado para /opt/riscv/bin"
    echo
    echo -e "${GREEN}APÓS A INSTALAÇÃO:${NC}"
    echo "  Para usar as ferramentas, certifique-se de que /opt/riscv/bin está no PATH:"
    echo "  ${BLUE}export PATH=\$PATH:/opt/riscv/bin${NC}"
    echo
    echo "  Ferramentas disponíveis:"
    echo "  • riscv32-unknown-elf-gcc    # Compilador C/C++"
    echo "  • riscv32-unknown-elf-as     # Assembler"
    echo "  • riscv32-unknown-elf-ld     # Linker"
    echo "  • spike                      # Simulador"
    echo "  • pk                         # Proxy kernel"
    echo
    echo -e "${GREEN}PARA MAIS INFORMAÇÕES:${NC}"
    echo "  Visite: https://github.com/riscv/riscv-gnu-toolchain"
    echo "          https://github.com/riscv-software-src/riscv-isa-sim"
    echo
}

case "$1" in
    all)
        all
	;;
    download)
        download
	;;
    setup-env)
	setup_environment
	;;
    setup-toolchain)
	setup_toolchain
	;;
    setup-opcodes)
	setup_opcodes
	;;
    setup-pk)
	setup_pk
	;;
    setup-spike)
	setup_spike
	;;
    *)
	show_help
	exit 1
	;;
esac
