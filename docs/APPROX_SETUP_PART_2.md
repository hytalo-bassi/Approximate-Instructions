# Setup Spike to include approximate instructions

### Step 1: Update Encoding Header

Add the definitions to `riscv-isa-sim/riscv/encoding.h`:

**Note:** Verify that `riscv-pk/machine/encoding.h` is also updated. If not, update it and rebuild riscv-pk.

Copy the same definitions from Part 1, Step 2.

### Step 2: Create Instruction Implementation Files

Create `.h` files defining the functionality of each approximate instruction.

**Note:** Implementation files are available in the `Approx_Instructions` folder.

Files should be placed in: `riscv-isa-sim/riscv/insns/`

**Example - addx.h:**
```c
WRITE_RD(sext_xlen(RS1 ^ RS2 ^ 0x00000000)); // ADDX with InXA1 adder
```

### Floating-Point Instructions

For floating-point instructions, create:
- Instruction files: `fxxx_s.h` in `riscv-isa-sim/riscv/insns/`
- Implementation files: `.c` files in `riscv-isa-sim/softfloat/`

**Required files for floating-point instructions:**

**faddx_s.h:**
- `f32_addx.c`
  - `s_subMagsF32x.c`
  - `s_addMagsF32x.c`

**fsubx_s.h:**
- `f32_subx.c`
  - `s_subMagsF32x.c`
  - `s_addMagsF32x.c`

**fmulx_s.h:**
- `f32_mulx.c`
  - `s_roundPackToF32x.c`
  - `s_shortShiftRightJam64x`

**fdivx_s.h:**
- `f32_divx.c`

### Step 3: Update Makefile

Add instruction names to `riscv-isa-sim/riscv/riscv.mk.in`:

```makefile
riscv_insn_ext_i = \
    # ... existing instructions ...
    addx \
    subx \
    mulx \
    divx \
    remx \
    # ... other instructions ...

riscv_insn_ext_f = \
    # ... existing instructions ...
    faddx_s \
    fsubx_s \
    fmulx_s \
    fdivx_s \
    # ... other instructions ...
```

### Step 4: Update SoftFloat Makefile

Add source files to `riscv-isa-sim/softfloat/softfloat.mk.in`:

```makefile
# Add these files
f32_addx.c \
f32_subx.c \
s_addMagsF32x.c \
s_subMagsF32x.c \
f32_mulx.c \
s_roundPackToF32x.c \
s_shortShiftRightJam64x \
f32_divx.c
```

### Step 5: Update Internal Headers

Add function declarations to `riscv-isa-sim/softfloat/internals.h`:

```c
// For faddx and fsubx
float32_t softfloat_addMagsF32x(uint_fast32_t, uint_fast32_t);
float32_t softfloat_subMagsF32x(uint_fast32_t, uint_fast32_t);

// For fmulx
float32_t softfloat_roundPackToF32x(bool, int_fast16_t, uint_fast32_t);
```

### Step 6: Update SoftFloat Header

Add function declarations to `riscv-isa-sim/softfloat/softfloat.h`:

```c
float32_t f32_addx(float32_t, float32_t);
float32_t f32_subx(float32_t, float32_t);
float32_t f32_mulx(float32_t, float32_t);
float32_t f32_divx(float32_t, float32_t);
```

### Step 7: Rebuild SPIKE

```bash
cd riscv-isa-sim/build
sudo make install
```

**Troubleshooting:** If build errors occur (e.g., `HGATP_MODE_SV57X4` out of scope), check for missing declarations in the new instruction implementations.

### Step 8: Test SPIKE

```bash
spike --isa=RV32I /opt/riscv/riscv32-unknown-elf/bin/pk addx
```

For comprehensive testing with the example from the RISC-V section:

```bash
riscv32-unknown-elf-gcc addx.c -O1 -march=rv32imafdc -o addx -lm 
spike --isa=RV32IMAFDC /opt/riscv/riscv32-unknown-elf/bin/pk addx
```

## Usage Notes

- Approximate instructions are invoked using inline assembly with the `asm volatile` directive
- Variables `[x]`, `[y]`, and `[z]` represent source and destination registers
- All implementation files referenced are available in the `Approx_Instructions` folder
- Ensure proper path substitution in commands (replace `/home/dani/` or `/home/suporte/` with your actual paths)
