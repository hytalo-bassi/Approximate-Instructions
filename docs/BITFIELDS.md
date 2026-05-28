# BITFIELDS — Custom approximate bitfield arithmetic (R-type)

This document describes a small custom instruction group that performs approximate arithmetic over bitfields in registers. All instructions are encoded in R-type format (31..0):

- funct7  (31:25)
- rs2     (24:20)
- rs1     (19:15)
- funct3  (14:12)
- rd      (11:7)
- opcode  (6:0)

The low 2 bits of the opcode (bits [1:0]) put them in quadrant 3.

If you want to extract another bitfield from a 32‑bit instruction, take the instruction as a string of 32 characters and apply this regex substitution:
#### Pattern:
```regex
^(.{7})(.{10})(.{3})(.{5})(.{5})(.{2})$
```

#### Replacement:
```regex
\1 \3 \5 \6
```

#### What it does
- `(.{7})` → captures the first 7 bits (funct7).
- `(.{10})` → skips the next 10 bits (not needed in output).
- `(.{3})`→ captures 3 bits (funct3).
- `(.{5})`→ captures 5 bits (opcode).
- `(.{5})`→ captures 5 bits (quadrant).
- `(.{2})`→ captures the last 2 bits.
The replacement string \1 \3 \5 \6 outputs funct7, funct3, opcode, and quadrant, separated by spaces.

Here is the [regex101](https://regex101.com/substitution?regex=%5E%28.%7B7%7D%29%28.%7B10%7D%29%28.%7B3%7D%29%28.%7B5%7D%29%28.%7B5%7D%29%28.%7B2%7D%29%24&testString=00000010111001111000011111110111&flags=gm&flavor=pcre2&delimiter=%2F&substitution=%5C1+%5C3+%5C5+%5C6) state with that substitution.

## Summary table

| Instr | funct7 (31..25) | funct3 (14..12) | Opcode (6..2) | Quadrant (1..0)| Description                        |
|-------|-----------------|-----------------|---------------|----------------|------------------------------------|
| addx  | 0000001 (0x1)   | 000 (0x0)       | 01010 (0xA)   | 11 (0x3)       | Approximate bitfield addition.      |
| subx  | 0000001 (0x1)   | 000 (0x0)       | 01011 (0xB)   | 11 (0x3)       | Approximate bitfield subtraction.   |
| mulx  | 0000001 (0x1)   | 000 (0x0)       | 11100 (0x1C)  | 11 (0x3)       | Approximate bitfield multiplication.|
| divx  | 0000001 (0x1)   | 000 (0x0)       | 11101 (0x1D)  | 11 (0x3)       | Approximate bitfield division.      |
| faddx.s | 1000000 (0x40)   | 111 (0x7)       | 10100 (0x14)  | 11 (0x3)       | Approximate bitfield floating point add. |
| fsubx.s | 1000100 (0x44)   | 111 (0x7)       | 10100 (0x14)  | 11 (0x3)       | Approximate bitfield floating point subtraction. |
| fmulx.s | 1001000 (0x48)   | 111 (0x7)       | 10100 (0x14)  | 11 (0x3)       | Approximate bitfield floating point multiplication. |

