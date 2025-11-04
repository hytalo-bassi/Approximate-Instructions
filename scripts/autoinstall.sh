#!/bin/bash

# Termina o programa em qualquer erro
set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detecta número de cores para compilação paralela
INSTALL_DIR="riscv-dev"
CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
OLD_OPCODES_URL='https://github.com/riscv/riscv-opcodes/archive/7c3db437d8d3b6961f8eb2931792eaea1c469ff3.zip'
DECLARATIONS_HEADER_PATCH="
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
#define MASK_FDIVX_S  0xfe00007f"
INTEGER_INSTRUCTIONS_C_PATCH="
{"addx",    0, INSN_CLASS_I, "d,s,t", MATCH_ADDX, MASK_ADDX, match_opcode, 0},
{"subx",    0, INSN_CLASS_I, "d,s,t", MATCH_SUBX, MASK_SUBX, match_opcode, 0},
{"mulx",    0, INSN_CLASS_I, "d,s,t", MATCH_MULX, MASK_MULX, match_opcode, 0},
{"divx",    0, INSN_CLASS_I, "d,s,t", MATCH_DIVX, MASK_DIVX, match_opcode, 0},
{"remx",    0, INSN_CLASS_I, "d,s,t", MATCH_REMX, MASK_REMX, match_opcode, 0},
"
FLOAT_INSTRUCTIONS_C_BINUTILS_PATCH="
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FADDX_S|MASK_RM, MASK_FADDX_S|MASK_RM,   match_opcode, 0},
{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FADDX_S,         MASK_FADDX_S,           match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FSUBX_S|MASK_RM, MASK_FSUBX_S|MASK_RM,   match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FSUBX_S,         MASK_FSUBX_S,           match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FMULX_S|MASK_RM, MASK_FMULX_S|MASK_RM,   match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FMULX_S,         MASK_FMULX_S,           match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FDIVX_S|MASK_RM, MASK_FDIVX_S|MASK_RM,   match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FDIVX_S,         MASK_FDIVX_S,           match_opcode, 0},
"
FLOAT_INSTRUCTIONS_C_GDB_PATCH="
{"faddx.s", 0, INSN_CLASS_F, "D,S,T",   MATCH_FADDX_S|MASK_RM, MASK_FADDX_S|MASK_RM,   match_opcode, 0},
{"faddx.s", 0, INSN_CLASS_F, "D,S,T,m", MATCH_FADDX_S,         MASK_FADDX_S,           match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F, "D,S,T",   MATCH_FSUBX_S|MASK_RM, MASK_FSUBX_S|MASK_RM,   match_opcode, 0},
{"fsubx.s", 0, INSN_CLASS_F, "D,S,T,m", MATCH_FSUBX_S,         MASK_FSUBX_S,           match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F, "D,S,T",   MATCH_FMULX_S|MASK_RM, MASK_FMULX_S|MASK_RM,   match_opcode, 0},
{"fmulx.s", 0, INSN_CLASS_F, "D,S,T,m", MATCH_FMULX_S,         MASK_FMULX_S,           match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F, "D,S,T",   MATCH_FDIVX_S|MASK_RM, MASK_FDIVX_S|MASK_RM,   match_opcode, 0},
{"fdivx.s", 0, INSN_CLASS_F, "D,S,T,m", MATCH_FDIVX_S,         MASK_FDIVX_S,           match_opcode, 0},
"
RISCV_I_MK_IN_PATCH="
    addx \\
    subx \\
    mulx \\
    divx \\
    remx \\
"

RISCV_F_MK_IN_PATCH="
    faddx_s \\
    fsubx_s \\
    fmulx_s \\
    fdivx_s \\
"
SOFTFLOAT_MK_IN_PATCH="
    f32_addx.c \\
    f32_subx.c \\
    s_addMagsF32x.c \\
    s_subMagsF32x.c \\
    f32_mulx.c \\
    s_roundPackToF32x.c \\
    s_shortShiftRightJam64x \\
    f32_divx.c \\
"
INTERNALS_H_PATCH="
// For faddx and fsubx
float32_t softfloat_addMagsF32x(uint_fast32_t, uint_fast32_t);
float32_t softfloat_subMagsF32x(uint_fast32_t, uint_fast32_t);

// For fmulx
float32_t softfloat_roundPackToF32x(bool, int_fast16_t, uint_fast32_t);
"
SOFTFLOAT_H_PATCH="
float32_t f32_addx(float32_t, float32_t);
float32_t f32_subx(float32_t, float32_t);
float32_t f32_mulx(float32_t, float32_t);
float32_t f32_divx(float32_t, float32_t);
"
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
    print_status "Checking requirements..."
    
    if ! command_exists git; then
        print_error "git not installed. Please, install git first."
        exit 1
    fi
    
    if ! command_exists make; then
        print_warning "make not installed. Please, install make first."
	exit 1
    fi

    if ! command_exists unzip; then
        print_warning "unzip not installed. Please, install unzip first."
	exit 1
    fi

    if ! command_exists python3; then
        print_warning "python3 not installed. Please, install python3 first."
	exit 1
    fi

    print_success "All requirements found!"
}

clone_repo() {
    local repo_url=$1
    local repo_name=$2
    local description=$3
    
    print_status "Installing: $description"
    print_status "Repo: $repo_url"
    
    if [ -d "$repo_name" ]; then
        print_warning "Directory $repo_name already exists. Updating..."
        cd "$repo_name"
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || {
            print_warning "Unable to update. Mantaning current version."
        }
        cd ..
    else
        print_status "Cloning $repo_name..."
        if git clone --depth=1 --single-branch "$repo_url" "$repo_name"; then
            print_success "Cloned $repo_name successfully"
        else
            print_error "Failed to clone $repo_name"
            return 1
        fi
    fi
    
    echo
}

install_riscv_repos() {
    print_status "Instaling RISC-V repos..."
    echo
    
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        print_status "Installation directory: $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    
    repos=(
        "https://github.com/riscv/riscv-gnu-toolchain|riscv-gnu-toolchain|Toolchain GNU RISC-V - RISC-V GCC compiler"
        "https://github.com/riscv/riscv-opcodes.git|riscv-opcodes|Opcodes RISC-V - Architecture definitions and instructions"
    )
    
    for repo_info in "${repos[@]}"; do
        IFS='|' read -r url name description <<< "$repo_info"
        clone_repo "$url" "$name" "$description"
    done
    
    print_status "Installing binutils, gcc, gdb, spike, pk submodules..."
    
    cd riscv-gnu-toolchain
    git submodule update --init --depth=1 --recursive binutils gcc gdb spike pk
    
    cd ../..
}

patch_files() {
    print_status "Patching binutils and gdb headers..."
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/gdb/include/opcode/riscv-opc.h \
        "$DECLARATIONS_HEADER_PATCH" \
        "#define RISCV_ENCODING_H" -a
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/binutils/include/opcode/riscv-opc.h \
        "$DECLARATIONS_HEADER_PATCH" \
        "#ifdef DECLARE_INSN" -a

    print_success "Patched binutils and gdb successfully!"

    print_status "Patching binutils and gdb c files..."
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/binutils/opcodes/riscv-opc.c \
        "$INTEGER_INSTRUCTIONS_C_PATCH\n$FLOAT_INSTRUCTIONS_C_BINUTILS_PATCH" \
        "{0, 0, INSN_CLASS_NONE, 0, 0, 0, 0, 0}"
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/gdb/opcodes/riscv-opc.c \
        "$INTEGER_INSTRUCTIONS_C_PATCH\n$FLOAT_INSTRUCTIONS_C_GDB_PATCH" \
        "{0, 0, INSN_CLASS_NONE, 0, 0, 0, 0, 0}"

    print_success "Patched binutils and gdb C files successfully!"

    print_status "Patching spike files..."
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/spike/riscv/riscv.mk.in \
        "$RISCV_I_MK_IN_PATCH" \
        "riscv_insn_ext_i = \\" -a
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/spike/riscv/riscv.mk.in \
        "$RISCV_F_MK_IN_PATCH" \
        "riscv_insn_ext_f = \\" -a
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/spike/softfloat/softfloat.mk.in \
        "$SOFTFLOAT_MK_IN_PATCH" \
        "softfloat_c_srcs = \\" -a
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/spike/softfloat/internals.h \
        "$INTERNALS_H_PATCH" \
        "float32_t softfloat_roundPackToF32( bool, int_fast16_t, uint_fast32_t );" -a
    python3 ./scripts/patch.py $INSTALL_DIR/riscv-gnu-toolchain/spike/softfloat/softfloat.h \
        "$SOFTFLOAT_H_PATCH" \
        "float32_t f32_add( float32_t, float32_t ); " -a -b  

    print_status "Adding approximate instruction's header and C files..."
    cp ./Approx_Instructions/*.h $INSTALL_DIR/riscv-gnu-toolchain/spike/riscv/insns/
    cp ./Approx_Instructions/*.c $INSTALL_DIR/riscv-gnu-toolchain/spike/softfloat/
    print_success "Approximate instructions added"

    print_success "Patched spike files successfully!"
}

setup_toolchain() {
    print_status "Setting up RISC-V toolchain..."
    
    cd $INSTALL_DIR/riscv-gnu-toolchain
    
    print_status "Using architecture rv32imafdc and ABI ilp32..."
    if ./configure --prefix=/opt/riscv --with-arch=rv32imafdc --with-abi=ilp32; then
        print_success "Configuration complete!"
    else
        print_error "Failed to configure toolchain!"
        exit 1
    fi
    
    print_status "Compiling toolchain with $CORES parallel cores... (may take several hours)"
    
    if make -j"$CORES"; then
        print_success "Toolchain compiled successfully"
    else
        print_error "Failed to compile toolchain"
        exit 1
    fi
    
    cd ../..
    
    print_status "Adding /opt/riscv/bin to PATH..."
    export PATH=$PATH:/opt/riscv/bin
    
    print_success "Toolchain's configuration complete"
}

setup_opcodes() {
    # Not needed at this version due to hardcoding patch
    # print_status "Configurando riscv-opcodes..."

    # cd riscv-dev/riscv-opcodes

    # print_success "Configuração do riscv-opcodes concluída!"
}

setup_pk() {
    print_status "Setting riscv-pk up..."

    cd $INSTALL_DIR/riscv-gnu-toolchain/riscv-pk

    mkdir build
    cd build

    if ! ../configure --prefix=/opt/riscv --host=riscv32-unknown-elf --with-arch=rv32imafdc_zicsr_zifencei; then
	    print_error "Failed to configure riscv-pk!"
	    exit 1
    fi

    print_status "Compiling riscv-pk with $CORES parallel cores..."
    
    if make -j"$CORES"; then
        print_success "riscv-pk compiled successfully"
    else
        print_error "Failed to compile riscv-pk"
        exit 1
    fi

    print_status "Installing riscv-pk..."

    if make install; then
        print_success "riscv-pk installed successfully"
    else
        print_error "Failed to install riscv-pk"
        exit 1
    fi

    cd ../../../..
}


setup_spike() {
    print_status "Configurando riscv-spike..."

    cd $INSTALL_DIR/riscv-gnu-toolchain/spike

    mkdir build
    cd build

    if ! ../configure --prefix=/opt/riscv; then
	    print_error "Failed to configure spike!"
	    exit 1
    fi

    print_status "Compiling spike with $CORES parallel cores..."
    
    if make -j"$CORES"; then
        print_success "spike compiled successfully"
    else
        print_error "Failed to compile spike"
        exit 1
    fi

    print_status "Installing spike..."

    if make install; then
        print_success "Spike installed successfully"
    else
        print_error "Failed to install spike"
        exit 1
    fi

    cd ../../../..
}

setup_environment() {
	setup_toolchain
	setup_opcodes
	setup_pk
	setup_spike
}

show_post_install_info() {
    print_success "Downloaded successfully!"
    echo
    print_status "Repositories downloaded to: $PWD/$INSTALL_DIR"
    echo
    print_warning "Compiling the toolchain can take up to 4 hours and need a lot of free space."
}

download() {
    check_prerequisites
    install_riscv_repos
    show_post_install_info
}

all() {
    download    
    print_success "RISC-V repos downloaded"
    
    print_status "Patching files and adding approximate instructions"
    patch_files
    print_success "Patched successfully!"

    print_status "Installing and setting environment up..."
    setup_environment
    print_success "Environment installation and configuration complete!"
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
    echo -e "  ${YELLOW}patch${NC}      Faz o patch dos arquivos para instalar as instruções aproximadas"
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
    echo "  $INSTALL_DIR/"
    echo "  ├── riscv-gnu-toolchain/        # Toolchain GNU completo"
    echo "  │ 	├── riscv-pk/               # Proxy kernel"
    echo "  │ 	└── spike/                  # Simulador RISC-V"
    echo "  └── riscv-opcodes/              # Definições de instruções"
    echo
    echo -e "${GREEN}EXEMPLO DE USO:${NC}"
    echo "  # Instalação completa (recomendado para primeira vez)"
    echo "  $0 all"
    echo
    echo "  # Instalação em etapas"
    echo "  $0 download          # Baixa repositórios"
    echo "  $0 patch             # Faz patch e adiciona as instruções aproximadas"
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
    "all")
        all
	;;
    "download")
        download
	;;
    "setup-env")
	    setup_environment
	;;
    "setup-toolchain")
	    setup_toolchain
	;;
    "setup-opcodes")
	    setup_opcodes
	;;
    "setup-pk")
	    setup_pk
	;;
    "setup-spike")
	    setup_spike
	;;
    "patch")
        patch_files
    ;;
    *)
	    show_help
	    exit 1
	;;
esac
