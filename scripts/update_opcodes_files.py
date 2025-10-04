#!/bin/python3

# Formatted with `black`

import os
import sys
import re
from typing import List, Tuple
from pathlib import Path
import argparse


DEFAULT_BASE_DIR = "/root/riscv-dev"
DEFAULT_SUBDIRS = ["riscv-opcodes", "riscv-gnu-toolchain"]
RISCV_GUARD = "#define RISCV_ENCODING_H"
DECLARE_INSN = "#ifdef DECLARE_INSN"
RISCV_INSN_EXT_I = "riscv_insn_ext_i = \\"
RISCV_INSN_EXT_F = "riscv_insn_ext_f = \\"
DEFAULT_INTEGER_C_INSN = "\n".join(
    [
        '{"addx",    0, INSN_CLASS_I, "d,s,t", MATCH_ADDX, MASK_ADDX, match_opcode, 0},',
        '{"subx",    0, INSN_CLASS_I, "d,s,t", MATCH_SUBX, MASK_SUBX, match_opcode, 0},',
        '{"mulx",    0, INSN_CLASS_I, "d,s,t", MATCH_MULX, MASK_MULX, match_opcode, 0},',
        '{"divx",    0, INSN_CLASS_I, "d,s,t", MATCH_DIVX, MASK_DIVX, match_opcode, 0},',
        '{"remx",    0, INSN_CLASS_I, "d,s,t", MATCH_REMX, MASK_REMX, match_opcode, 0},',
    ]
)
DEFAULT_FLOAT_C_INSN_BINUTILS = "\n".join(
    [
        '{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FADDX_S|MASK_RM, MASK_FADDX_S|MASK_RM,   match_opcode, 0},',
        '{"faddx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FADDX_S,         MASK_FADDX_S,           match_opcode, 0},',
        '{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FSUBX_S|MASK_RM, MASK_FSUBX_S|MASK_RM,   match_opcode, 0},',
        '{"fsubx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FSUBX_S,         MASK_FSUBX_S,           match_opcode, 0},',
        '{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FMULX_S|MASK_RM, MASK_FMULX_S|MASK_RM,   match_opcode, 0},',
        '{"fmulx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FMULX_S,         MASK_FMULX_S,           match_opcode, 0},',
        '{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T",   MATCH_FDIVX_S|MASK_RM, MASK_FDIVX_S|MASK_RM,   match_opcode, 0},',
        '{"fdivx.s", 0, INSN_CLASS_F_INX, "D,S,T,m", MATCH_FDIVX_S,         MASK_FDIVX_S,           match_opcode, 0},',
    ]
)


def check_files_exist(file_paths: List[str]) -> List[Tuple[str, bool]]:
    """
    Check if files exist and return results.

    Args:
        file_paths: List of file paths to check

    Returns:
        List of tuples (file_path, exists)
    """
    results = []
    for file_path in file_paths:
        path = Path(file_path)
        exists = path.exists()
        results.append((str(path), exists))
    return results


def extract_opcodes(filename: str) -> List[str]:
    """
    Extract opcodes for each line, including '.' until next whitespace.
    Convert to uppercase and replace '.' with '_'.
    """
    opcodes = []

    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                match = re.match(r"^(\S+)", line)
                if match:
                    opcode = match.group(1)

                    processed_word = opcode.upper().replace(".", "_")
                    opcodes.append(processed_word)

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return []
    except Exception as e:
        print(f"Error reading file '{filename}': {e}")
        return []

    return opcodes


def find_matching_lines(
    encoding_file: str, search_strings: List[str], pattern: str = "#define MATCH_"
) -> str:
    matching_lines = []

    try:
        with open(encoding_file, "r") as f:
            content = f.read()

            for search_string in search_strings:
                current_pattern = f"{pattern}{search_string}".lower()
                for line in content.split("\n"):
                    if current_pattern in line.lower():
                        matching_lines.append(line.strip())
                        print(f"Found match for '{search_string}': {line.strip()}")

    except FileNotFoundError:
        print(f"Error: File '{encoding_file}' not found.")
        return ""
    except Exception as e:
        print(f"Error reading file '{encoding_file}': {e}")
        return ""

    return "\n".join(matching_lines)


def patch_file(
    filepath: str,
    patch: str,
    condition_string: str,
    position_string: str,
    after: bool = True,
    breaklines: bool = True,
) -> bool:
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        return False

    with open(filepath, "r") as f:
        content = f.read()

    if condition_string in content:
        insertion_point = content.find(position_string)
        if insertion_point != -1:
            last_index = (
                insertion_point + len(position_string) if after else insertion_point
            )
            patch = f"\n{patch}\n" if breaklines else patch
            new_content = content[:last_index] + patch + content[last_index:]

            with open(filepath, "w") as f:
                f.write(new_content)
            return True

    print(f"Error: Could not find insertion point in {filepath}")
    return False


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Configure RISC-V toolchain files with custom opcodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default paths
  %(prog)s --set-rv-file custom/rv_approx     # Use custom rv_approx file
        """,
    )

    parser.add_argument("--set-rv-file", type=Path, help="Path to rv_approx file")
    parser.add_argument(
        "--set-encoding-file", type=Path, help="Path to encoding.out.h file"
    )
    parser.add_argument(
        "--set-binutils-file", type=Path, help="Path to riscv-opc.c in binutils"
    )
    parser.add_argument("--set-gdb-file", type=Path, help="Path to riscv-opc.c in gdb")
    parser.add_argument(
        "--set-header-gdb-opcode",
        type=Path,
        help="Path to riscv-opc.h in gdb/include/opcode",
    )
    parser.add_argument(
        "--set-header-binutils-opcode",
        type=Path,
        help="Path to riscv-opc.h in binutils/include/opcode",
    )
    parser.add_argument(
        "--set-header-spike-opcode",
        type=Path,
        help="Path to encoding.h in riscv-isa-sim/riscv/encoding.h",
    )
    parser.add_argument(
        "--set-spike-mk",
        type=Path,
        help="Path to spike.mk.in in riscv-isa-sim/riscv/spike.mk.in",
    )

    return parser


if __name__ == "__main__":
    parser = create_argument_parser()
    args = parser.parse_args()

    base_dir = DEFAULT_BASE_DIR
    riscv_subdir = DEFAULT_SUBDIRS[1]
    opcodes_subdir = DEFAULT_SUBDIRS[0]

    rv_file = (
        args.set_rv_file
        or f"{base_dir}/{opcodes_subdir}/extensions/unratified/rv_approx"
    )
    encoding_file = (
        args.set_encoding_file or f"{base_dir}/{opcodes_subdir}/encoding.out.h"
    )
    binutils_file = (
        args.set_binutils_file
        or f"{base_dir}/{riscv_subdir}/binutils/opcodes/riscv-opc.c"
    )
    gdb_file = args.set_gdb_file or f"{base_dir}/{riscv_subdir}/gdb/opcodes/riscv-opc.c"
    header_gdb_opcode = (
        args.set_header_gdb_opcode
        or f"{base_dir}/{riscv_subdir}/gdb/include/opcode/riscv-opc.h"
    )
    header_binutils_opcode = (
        args.set_header_binutils_opcode
        or f"{base_dir}/{riscv_subdir}/binutils/include/opcode/riscv-opc.h"
    )
    header_spike_opcode = (
        args.set_header_spike_opcode
        or f"{base_dir}/{riscv_subdir}/spike/riscv/encoding.h"
    )
    spike_mk = (
        args.set_spike_mk
        or f"{base_dir}/{riscv_subdir}/spike/riscv/riscv.mk.in"
    )

    allowed_to_continue = True
    for file_status in check_files_exist(
        [
            rv_file,
            encoding_file,
            binutils_file,
            gdb_file,
            header_gdb_opcode,
            header_binutils_opcode,
        ]
    ):
        if not file_status[1]:
            print(f"ERROR: {file_status[0]} missing!")
            allowed_to_continue = False

    if not allowed_to_continue:
        print("Fix the errors first! Stopping...")
        exit(1)

    opcodes = extract_opcodes(rv_file)
    define_matches_header = find_matching_lines(encoding_file, opcodes)
    define_matches_header += "\n" + find_matching_lines(encoding_file, opcodes, "#define MASK_")
    declare_insn_header = find_matching_lines(encoding_file, opcodes, "DECLARE_INSN(")

    integer_instructions = DEFAULT_INTEGER_C_INSN
    float_instructions_binutils = DEFAULT_FLOAT_C_INSN_BINUTILS
    float_instructions_gdb = float_instructions_binutils.replace(
        "INSN_CLASS_F_INX", "INSN_CLASS_F"
    )

    template_header_patch = "/* Imported from update_opcodes_files script */"

    patch_file(
        binutils_file,
        f"{template_header_patch}\n{integer_instructions}\n{float_instructions_binutils}",
        "const struct riscv_opcode riscv_opcodes[]",
        "{0, 0, INSN_CLASS_NONE",
        False,
    )

    patch_file(
        gdb_file,
        f"{template_header_patch}\n{integer_instructions}\n{float_instructions_gdb}",
        "const struct riscv_opcode riscv_opcodes[]",
        "{0, 0, INSN_CLASS_NONE",
        False,
    )

    patch_file(
        header_gdb_opcode,
        f"{template_header_patch}\n{define_matches_header}",
        RISCV_GUARD,
        RISCV_GUARD,
    )

    patch_file(
        header_gdb_opcode,
        f"{template_header_patch}\n{declare_insn_header}",
        DECLARE_INSN,
        DECLARE_INSN,
    )

    patch_file(
        header_binutils_opcode,
        f"{template_header_patch}\n{define_matches_header}",
        RISCV_GUARD,
        RISCV_GUARD,
    )

    patch_file(
        header_binutils_opcode,
        f"{template_header_patch}\n{declare_insn_header}",
        DECLARE_INSN,
        DECLARE_INSN,
    )

    patch_file(
        header_spike_opcode,
        f"{template_header_patch}\n{define_matches_header}",
        RISCV_GUARD,
        RISCV_GUARD,
    )

    patch_file(
        header_spike_opcode,
        f"{template_header_patch}\n{declare_insn_header}",
        DECLARE_INSN,
        DECLARE_INSN,
    )

    # for opcode in opcodes:
    #     opcode = opcode.lower()
    #     if opcode[0] != "f":
    #         patch_file(
    #             spike_mk,
    #             f"\t{opcode} \\\n",
    #             RISCV_INSN_EXT_I,
    #             RISCV_INSN_EXT_I,
    #             breaklines=False,
    #         )
    #     else:
    #         patch_file(
    #             spike_mk,
    #             f"\t{opcode} \\\n",
    #             RISCV_INSN_EXT_F,
    #             RISCV_INSN_EXT_F,
    #             breaklines=False
    #         )
