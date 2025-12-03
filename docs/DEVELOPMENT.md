# Developing Approximate-Instructions

This repository houses a comprehensive environment for RISC-V simulation, focusing on approximate computing and custom instruction set modifications. It provides a structured workflow for running simulations using **gem5** and **Spike**, utilizing containerized environments and automated utility scripts.

## Tools & Environment

The project relies on specific toolchains and simulators to ensure consistent execution across bare metal and Linux environments.

  * **Architecture:** RISC-V 32-bit (`riscv32`).
  * **RISC-V tools:** riscv-opcodes.
  * **Simulators:**
      * **gem5 (recommended):** Used for full-system simulation using the **Linux MUSL** library.
      * **Spike:** Used primarily for **Bare Metal** execution verification.
  * **Languages:** Python (Utilities), C/C++ (Source), Shell.
  * **Docker (recommended):** setting up all of these tools by hand is hard, and can possibly make the project platform-dependent. That's why we encourage you to use Docker primarily.

### Generating opcodes

If you need to add more custom instructions, you'll also need the opcodes of them. For that reason,
we use riscv-opcodes generation tool:

#### Downloading

```bash
git clone --single-branch https://github.com/riscv/riscv-opcodes &&
  cd riscv-opcodes &&
  git checkout 3deaa8c &&
```

**Generating:**
- Run the command:

```bash
cp <your_custom_rv> ~/.local/opt/riscv-opcodes/extensions/unratified &&
  cd ~/.local/opt/riscv-opcodes &&
  make EXTENSIONS='unratified/rv*'
```

Change `<your_custom_rv>` to your rv containing the new custom instructions.

## Project Structure

The repository is organized to separate configuration, modifications, and utility logic.

```text
.
├── Approx_Instructions/  # Patches/Modifications for the RISC-V GNU Toolchain
├── config/               # Tool configurations (e.g., 'simple_config' for gem5)
├── docker/               # Dockerfiles and container orchestration scripts
├── patches/              # Source code patches for standard tools (e.g., gem5 mods)
└── scripts/              # Python utilities for automation and data processing
```

### Directory Details

  * **`config/`**: Centralizes configuration files required to initialize simulators. This includes the `simple_config` setup required for custom gem5 runs.
  * **`docker/`**: Contains the environment definitions. We strongly recommend building the provided Docker images to ensure toolchain compatibility.
  * **`patches/`**: specific modifications applied to the upstream gem5 repository to support custom requirements.
  * **`Approx_Instructions/`**: Contains specific patches and build instructions targeting the RISC-V GNU Toolchain, enabling support for custom or approximate instructions.
  * **`scripts/`**: A collection of Python scripts used to automate simulation runs, parse outputs, and manage artifacts.

## Git Conventions

To maintain a clean and semantic history, this project adheres to the following Git standards.

### Commit Messages

We follow the **Conventional Commits** specification to automate changelogs and versioning.

  * **Structure**: `<type>(<scope>): <subject>`
  * **Types**:
      * `feat`: A new feature.
      * `fix`: A bug fix.
      * `docs`: Documentation only changes.
      * `style`: Formatting changes (white-space, missing semi-colons, etc).
      * `refactor`: A code change that neither fixes a bug nor adds a feature.
      * `chore`: Maintanance tasks, dependency updates, etc.

> **Example:** `feat(gem5): add support for approximate multiplier in simple_config`


## Language

This project started in UFMS, a brazilian university that speaks portuguese by default. But now, as this project gains traction, it's necessary to mantain a standard, international language. That means that all modifications, additions, or removements in any part of this project must be documented in **english first**.

Anyway, we encourage you to also have a portuguese version documentation, only if the english version is already available.
