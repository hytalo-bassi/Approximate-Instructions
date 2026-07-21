"""
Python translation of SoftFloat (release 3d) F32 magnitude add/subtract
routines, including the experimental bitwise approximate substitutions
present in the original C source (uncommented/active variants only).

Platform-independent: uses struct for IEEE-754 bit-pattern conversion
instead of C unions.
"""

import struct
import math

SIGN_MASK_32 = 0x80000000
EXP_MASK_32 = 0xFF
FRAC_MASK_32 = 0x7FFFFF
DEFAULT_NAN_F32UI = 0x7FC00000


def expF32UI(ui: int) -> int:
    return (ui >> 23) & EXP_MASK_32


def fracF32UI(ui: int) -> int:
    return ui & FRAC_MASK_32


def signF32UI(ui: int) -> bool:
    return (ui & SIGN_MASK_32) != 0


def packToF32UI(sign: bool, exp: int, sig: int) -> int:
    """
    Mirrors C's `packToF32UI` macro, which is plain integer ADDITION, not
    OR-with-masking:
        ((sign<<31) + (exp<<23) + sig)  [mod 2**32, via uint32_t wraparound]

    Critically, `sig` is NOT masked to 23 bits here. When rounding produces
    a `sig` whose bit 23 is set (a 24-bit value, since bit 23 is normally
    the implicit leading 1), that bit deliberately carries into the
    exponent field via the addition -- this is how SoftFloat naturally
    increments the exponent after a rounding carry, without a separate
    branch for it. Masking `sig` here (as an earlier version of this file
    did) silently drops that carry and corrupts every result whose
    rounded significand overflows 23 bits.
    """
    return ((int(sign) << 31) + ((exp & EXP_MASK_32) << 23) + sig) & 0xFFFFFFFF


def countLeadingZeros32(x: int) -> int:
    x &= 0xFFFFFFFF
    if x == 0:
        return 32
    return 32 - x.bit_length()


def bits_to_f32(bits: int) -> float:
    return struct.unpack('<f', struct.pack('<I', bits & 0xFFFFFFFF))[0]


def f32_to_bits(f):
    try:
        return struct.unpack('<I', struct.pack('<f', f))[0]
    except OverflowError:
        return struct.unpack('<I', struct.pack('<f', math.inf if f > 0 else -math.inf))[0]



# ---------------------------------------------------------------------------
# Routines referenced by both add/sub paths but not defined in the two
# snippets provided. Stubbed so the file imports cleanly; replace with
# real translations once you share their source.
# ---------------------------------------------------------------------------
def softfloat_shiftRightJam32(a: int, dist: int) -> int:
    """
    a: uint32_t, dist: uint_fast16_t (treated here as a Python int, may be
    passed negative by callers the same way the C does implicit wraparound
    via `-dist & 31`).

    Shifts `a` right by `dist`, OR-ing in a "sticky" bit if any 1-bits were
    shifted out (jammed), used so rounding decisions see whether info was
    lost. If dist >= 31, collapses to whether `a` was nonzero at all.
    """
    a &= 0xFFFFFFFF
    if dist < 31:
        neg_dist_and_31 = (-dist) & 31
        shifted_out_nonzero = ((a << neg_dist_and_31) & 0xFFFFFFFF) != 0
        return ((a >> dist) | int(shifted_out_nonzero)) & 0xFFFFFFFF
    else:
        return int(a != 0)


def softfloat_normRoundPackToF32(sign: bool, exp: int, sig: int) -> float:
    shiftDist = countLeadingZeros32(sig) - 1
    exp -= shiftDist

    # `(unsigned int) exp < 0xFD`: emulate C's unsigned comparison. A
    # negative exp reinterpreted as unsigned is huge, so it would fail
    # this check (not < 0xFD) — i.e. the fast path only applies for
    # exp in [0, 0xFD).
    unsigned_exp_lt_0xFD = (0 <= exp < 0xFD)

    if (7 <= shiftDist) and unsigned_exp_lt_0xFD:
        uiZ = packToF32UI(sign, exp if sig else 0, (sig << (shiftDist - 7)) & 0xFFFFFFFF)
        return bits_to_f32(uiZ)
    else:
        return softfloat_roundPackToF32(sign, exp, (sig << shiftDist) & 0xFFFFFFFF)


def softfloat_isSigNaNF32UI(ui: int) -> bool:
    """
    True if `ui` is the bit pattern of a signaling NaN: exponent all 1s,
    fraction's MSB (bit 22) is 0 (signaling, vs 1 for quiet), and the
    remaining fraction bits are not all 0 (otherwise it'd be infinity).
    """
    return (
        ((ui & 0x7FC00000) == 0x7F800000)
        and (ui & 0x003FFFFF) != 0
    )


def softfloat_propagateNaNF32UI(uiA: int, uiB: int) -> int:
    if softfloat_isSigNaNF32UI(uiA) or softfloat_isSigNaNF32UI(uiB):
        softfloat_raiseFlags(softfloat_flag_invalid)
    return DEFAULT_NAN_F32UI


# ---------------------------------------------------------------------------
# Rounding-mode / exception-flag state (module-level globals mirroring the
# C library's global state). softfloat_exceptionFlags is a bitmask that
# accumulates flags across calls, just like the C original.
# ---------------------------------------------------------------------------
softfloat_round_near_even = "near_even"
softfloat_round_min = "min"
softfloat_round_max = "max"
softfloat_round_near_maxMag = "near_maxMag"
softfloat_round_odd = "odd"

softfloat_tininess_beforeRounding = "before_rounding"
softfloat_tininess_afterRounding = "after_rounding"

softfloat_flag_invalid = 0x01
softfloat_flag_overflow = 0x02
softfloat_flag_underflow = 0x04
softfloat_flag_inexact = 0x08

# Global state (mutable module-level "registers", as in the C library)
softfloat_roundingMode = softfloat_round_near_even
softfloat_detectTininess = softfloat_tininess_beforeRounding
softfloat_exceptionFlags = 0


def softfloat_raiseFlags(flag: int):
    global softfloat_exceptionFlags
    softfloat_exceptionFlags |= flag


def softfloat_roundPackToF32(sign: bool, exp: int, sig: int) -> float:
    global softfloat_exceptionFlags

    roundingMode = softfloat_roundingMode
    roundNearEven = (roundingMode == softfloat_round_near_even)
    roundIncrement = 0x40

    if (not roundNearEven) and (roundingMode != softfloat_round_near_maxMag):
        roundIncrement = (
            0x7F
            if roundingMode == (softfloat_round_min if sign else softfloat_round_max)
            else 0
        )

    roundBits = sig & 0x7F

    # `0xFD <= (unsigned int) exp`: emulate the C unsigned comparison, since
    # exp is stored as a signed int but compared as unsigned. A negative exp
    # becomes a huge unsigned value, so it also satisfies `0xFD <= exp`.
    unsigned_exp_ge_0xFD = (exp < 0) or (0xFD <= exp)

    if unsigned_exp_ge_0xFD:
        if exp < 0:
            isTiny = (
                (softfloat_detectTininess == softfloat_tininess_beforeRounding)
                or (exp < -1)
                or (sig + roundIncrement < 0x80000000)
            )
            sig = softfloat_shiftRightJam32(sig, -exp)
            exp = 0
            roundBits = sig & 0x7F
            if isTiny and roundBits:
                softfloat_raiseFlags(softfloat_flag_underflow)
        elif (0xFD < exp) or (0x80000000 <= sig + roundIncrement):
            softfloat_raiseFlags(softfloat_flag_overflow | softfloat_flag_inexact)
            uiZ = (packToF32UI(sign, 0xFF, 0) - (0 if roundIncrement else 1)) & 0xFFFFFFFF
            return bits_to_f32(uiZ)

    sig = (sig + roundIncrement) >> 7

    if roundBits:
        softfloat_exceptionFlags |= softfloat_flag_inexact
        if roundingMode == softfloat_round_odd:
            sig |= 1
            uiZ = packToF32UI(sign, exp, sig)
            return bits_to_f32(uiZ)

    # sig &= ~(!(roundBits ^ 0x40) & roundNearEven)
    # i.e. clear sig to 0 exactly when roundBits == 0x40 (tie) and we're
    # rounding to nearest-even (ties-to-even clears the tie-breaking bit).
    if (roundBits == 0x40) and roundNearEven:
        sig = 0

    if not sig:
        exp = 0

    uiZ = packToF32UI(sign, exp, sig)
    return bits_to_f32(uiZ)


# ---------------------------------------------------------------------------
# softfloat_addMagsF32x
# ---------------------------------------------------------------------------
def softfloat_addMagsF32x(uiA: int, uiB: int) -> float:
    expA = expF32UI(uiA)
    sigA = fracF32UI(uiA)
    expB = expF32UI(uiB)
    sigB = fracF32UI(uiB)

    # Cenário 5 (exponent diff bitwise form) left commented in original -> plain subtraction used
    expDiff = expA - expB

    if expDiff == 0:
        if not expA:
            uiZ = (uiA + sigB) & 0xFFFFFFFF
            return bits_to_f32(uiZ)

        if expA == 0xFF:
            if sigA | sigB:
                uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
                return bits_to_f32(uiZ)
            return bits_to_f32(uiA)

        signZ = signF32UI(uiA)
        expZ = expA

        # Active variant: Cenário 2 (Cenário 1 left commented in original)
        sigZ = 0x01000000 ^ sigA ^ sigB

        if (not (sigZ & 1)) and (expZ < 0xFE):
            uiZ = packToF32UI(signZ, expZ, sigZ >> 1)
            return bits_to_f32(uiZ)

        sigZ <<= 6
    else:
        signZ = signF32UI(uiA)
        sigA <<= 6
        sigB <<= 6

        if expDiff < 0:
            if expB == 0xFF:
                if sigB:
                    uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
                    return bits_to_f32(uiZ)
                uiZ = packToF32UI(signZ, 0xFF, 0)
                return bits_to_f32(uiZ)
            expZ = expB
            # Active: Cenário 3
            sigA = 0x20000000 if (sigA ^ expA) else sigA
            sigA = softfloat_shiftRightJam32(sigA, -expDiff)
        else:
            if expA == 0xFF:
                if sigA:
                    uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
                    return bits_to_f32(uiZ)
                return bits_to_f32(uiA)
            expZ = expA
            # Active: Cenário 3
            sigB = 0x20000000 if (sigB ^ expB) else sigB
            sigB = softfloat_shiftRightJam32(sigB, expDiff)

        # Active: Cenário 4
        sigZ = 0x20000000 ^ sigA ^ sigB

        if sigZ < 0x40000000:
            expZ -= 1
            sigZ <<= 1

    return softfloat_roundPackToF32(signZ, expZ, sigZ)


# ---------------------------------------------------------------------------
# softfloat_subMagsF32x
# ---------------------------------------------------------------------------
def softfloat_subMagsF32x(uiA: int, uiB: int) -> float:
    Cin = 0

    expA = expF32UI(uiA)
    sigA = fracF32UI(uiA)
    expB = expF32UI(uiB)
    sigB = fracF32UI(uiB)

    # Cenário 4 (exponent diff bitwise form) left commented in original -> plain subtraction used
    expDiff = expA - expB

    if expDiff == 0:
        if expA == 0xFF:
            if sigA | sigB:
                uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
                return bits_to_f32(uiZ)
            softfloat_raiseFlags(softfloat_flag_invalid)
            return bits_to_f32(DEFAULT_NAN_F32UI)

        # Active: Cenário 1
        sigDiff = ((~sigA & sigB) | (sigB & Cin) | (~sigA & Cin) | (sigA & ~sigB & ~Cin))

        if sigDiff == 0:
            uiZ = packToF32UI(softfloat_roundingMode == softfloat_round_min, 0, 0)
            return bits_to_f32(uiZ)

        if expA:
            expA -= 1
        signZ = signF32UI(uiA)
        if sigDiff < 0:
            signZ = not signZ
            sigDiff = -sigDiff

        shiftDist = countLeadingZeros32(sigDiff) - 8
        expZ = expA - shiftDist
        if expZ < 0:
            shiftDist = expA
            expZ = 0

        uiZ = packToF32UI(signZ, expZ, sigDiff << shiftDist)
        return bits_to_f32(uiZ)

    else:
        signZ = signF32UI(uiA)
        sigA <<= 7
        sigB <<= 7

        if expDiff < 0:
            signZ = not signZ
            if expB == 0xFF:
                if sigB:
                    uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
                    return bits_to_f32(uiZ)
                uiZ = packToF32UI(signZ, 0xFF, 0)
                return bits_to_f32(uiZ)
            expZ = expB - 1
            sigX = sigB | 0x40000000
            # Active: Cenário 2
            sigY = sigA ^ (0x40000000 if expA else sigA)
            expDiff = -expDiff
        else:
            if expA == 0xFF:
                if sigA:
                    uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
                    return bits_to_f32(uiZ)
                return bits_to_f32(uiA)
            expZ = expA - 1
            sigX = sigA | 0x40000000
            # Active: Cenário 2
            sigY = sigB ^ (0x40000000 if expB else sigB)

        return softfloat_normRoundPackToF32(
            signZ, expZ, sigX - softfloat_shiftRightJam32(sigY, expDiff)
        )


# ---------------------------------------------------------------------------
# Top-level entry point (from the earlier f32_subx translation)
# ---------------------------------------------------------------------------
def f32_subx(a: float, b: float) -> float:
    ui_a = f32_to_bits(a)
    ui_b = f32_to_bits(b)

    if signF32UI(ui_a ^ ui_b):
        return softfloat_addMagsF32x(ui_a, ui_b)
    else:
        return softfloat_subMagsF32x(ui_a, ui_b)


def f32_addx(a: float, b: float) -> float:
    ui_a = f32_to_bits(a)
    ui_b = f32_to_bits(b)

    # Note: branches are swapped relative to f32_subx (per the "mudei esta
    # função" comments in the original C).
    if signF32UI(ui_a ^ ui_b):
        return softfloat_subMagsF32x(ui_a, ui_b)
    else:
        return softfloat_addMagsF32x(ui_a, ui_b)


class Exp16Sig32:
    """Mirrors C's `struct exp16_sig32 { int_fast16_t exp; uint_fast32_t sig; }`."""
    __slots__ = ("exp", "sig")

    def __init__(self, exp: int, sig: int):
        self.exp = exp
        self.sig = sig

    def __repr__(self):
        return f"Exp16Sig32(exp={self.exp}, sig={self.sig})"


def softfloat_normSubnormalF32Sig(sig: int) -> Exp16Sig32:
    shiftDist = countLeadingZeros32(sig) - 8
    exp = 1 - shiftDist
    sig = (sig << shiftDist) & 0xFFFFFFFF
    return Exp16Sig32(exp, sig)


def softfloat_shortShiftRightJam64x(a: int, dist: int) -> int:
    """
    a: uint64_t, dist: uint_fast8_t.

    Active variant uses Cenário 6's bitwise substitute for the mask
    `(1<<dist) - 1` (the ORIG line computing that mask directly is
    commented out in the source). teste1 reduces to just `~teste`
    (mod 2**64, since the other OR terms all vanish with the 0/1
    literals), so it's carried through literally below rather than
    "simplified" back to the original mask.
    """
    a &= 0xFFFFFFFFFFFFFFFF
    teste = (1 << dist) & 0xFFFFFFFFFFFFFFFF

    # Cenário 6: teste1 = ((~teste & 1) | (1 & 0) | (~teste & 0) | (teste & ~1 & ~0))
    # With Python's arbitrary-precision ints, ~teste is negative (infinite
    # leading 1s), so mask everything to 64 bits to match C's uint64_t
    # wraparound semantics term-by-term.
    MASK64 = 0xFFFFFFFFFFFFFFFF
    not_teste = (~teste) & MASK64
    not_1 = (~1) & MASK64
    not_0 = (~0) & MASK64
    teste1 = (
        (not_teste & 1)
        | (1 & 0)
        | (not_teste & 0)
        | (teste & not_1 & not_0)
    ) & MASK64

    return (a >> dist) | int((a & teste1) != 0)


def softfloat_roundPackToF32x(sign: bool, exp: int, sig: int) -> float:
    global softfloat_exceptionFlags

    roundingMode = softfloat_roundingMode
    roundNearEven = (roundingMode == softfloat_round_near_even)
    roundIncrement = 0x40

    if (not roundNearEven) and (roundingMode != softfloat_round_near_maxMag):
        roundIncrement = (
            0x7F
            if roundingMode == (softfloat_round_min if sign else softfloat_round_max)
            else 0
        )

    roundBits = sig & 0x7F

    unsigned_exp_ge_0xFD = (exp < 0) or (0xFD <= exp)

    if unsigned_exp_ge_0xFD:
        if exp < 0:
            # Active variant: Cenário 2. Note C operator precedence:
            # `sig ^ roundIncrement < 0x80000000` parses as
            # `sig ^ (roundIncrement < 0x80000000)` since `<` binds tighter
            # than `^` in both C and Python — i.e. sig XORed with a 0/1
            # boolean, NOT (sig ^ roundIncrement) compared to 0x80000000.
            # The commented-out ORIG (`sig + roundIncrement < 0x80000000`)
            # is left inactive, matching the source.
            isTiny = (
                (softfloat_detectTininess == softfloat_tininess_beforeRounding)
                or (exp < -1)
                or bool(sig ^ int(roundIncrement < 0x80000000))
            )
            sig = softfloat_shiftRightJam32(sig, -exp)
            exp = 0
            roundBits = sig & 0x7F
            if isTiny and roundBits:
                softfloat_raiseFlags(softfloat_flag_underflow)
        elif (0xFD < exp) or (0x80000000 <= sig + roundIncrement):
            softfloat_raiseFlags(softfloat_flag_overflow | softfloat_flag_inexact)
            uiZ = (packToF32UI(sign, 0xFF, 0) - (0 if roundIncrement else 1)) & 0xFFFFFFFF
            return bits_to_f32(uiZ)

    # Active variant: Cenário 1 (ORIG `(sig + roundIncrement) >> 7` is
    # commented out in the source).
    sig = (sig ^ roundIncrement) >> 7

    if roundBits:
        softfloat_exceptionFlags |= softfloat_flag_inexact
        if roundingMode == softfloat_round_odd:
            sig |= 1
            uiZ = packToF32UI(sign, exp, sig)
            return bits_to_f32(uiZ)

    if (roundBits == 0x40) and roundNearEven:
        sig = 0

    if not sig:
        exp = 0

    uiZ = packToF32UI(sign, exp, sig)
    return bits_to_f32(uiZ)


def f32_mulx(a: float, b: float) -> float:
    uiA = f32_to_bits(a)
    signA = signF32UI(uiA)
    expA = expF32UI(uiA)
    sigA = fracF32UI(uiA)

    uiB = f32_to_bits(b)
    signB = signF32UI(uiB)
    expB = expF32UI(uiB)
    sigB = fracF32UI(uiB)

    signZ = signA ^ signB

    if expA == 0xFF:
        if sigA or ((expB == 0xFF) and sigB):
            uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
            return bits_to_f32(uiZ)
        magBits = expB | sigB
        if not magBits:
            softfloat_raiseFlags(softfloat_flag_invalid)
            return bits_to_f32(DEFAULT_NAN_F32UI)
        else:
            return bits_to_f32(packToF32UI(signZ, 0xFF, 0))

    if expB == 0xFF:
        if sigB:
            uiZ = softfloat_propagateNaNF32UI(uiA, uiB)
            return bits_to_f32(uiZ)
        magBits = expA | sigA
        if not magBits:
            softfloat_raiseFlags(softfloat_flag_invalid)
            return bits_to_f32(DEFAULT_NAN_F32UI)
        else:
            return bits_to_f32(packToF32UI(signZ, 0xFF, 0))

    if not expA:
        if not sigA:
            return bits_to_f32(packToF32UI(signZ, 0, 0))
        normExpSig = softfloat_normSubnormalF32Sig(sigA)
        expA = normExpSig.exp
        sigA = normExpSig.sig

    if not expB:
        if not sigB:
            return bits_to_f32(packToF32UI(signZ, 0, 0))
        normExpSig = softfloat_normSubnormalF32Sig(sigB)
        expB = normExpSig.exp
        sigB = normExpSig.sig

    # Active variant ("APPROX", not the commented-out ORIG `expA + expB - 0x7F`
    # nor the commented-out Cenário 5 bitwise form): note C operator
    # precedence makes this `expA ^ (expB - 0x7F)`, which Python's own
    # precedence (arithmetic binds tighter than bitwise xor) replicates
    # identically, so no extra parens are needed for equivalence — they're
    # added below purely for readability.
    expZ = expA ^ (expB - 0x7F)

    sigA = (sigA | 0x00800000) << 7
    sigB = (sigB | 0x00800000) << 8

    # Active variant: ORIG 64x64-bit product path (the MULX/Cenário 4 inline-
    # asm alternative is commented out in the source and not translatable to
    # portable Python anyway).
    sigZ = softfloat_shortShiftRightJam64x(sigA * sigB, 32)

    if sigZ < 0x40000000:
        expZ -= 1
        sigZ <<= 1

    # Uses the modified roundPackToF32 variant per the "mudei a função" /
    # "C1 e C2" comment, not the plain softfloat_roundPackToF32.
    return softfloat_roundPackToF32x(signZ, expZ, sigZ)
    ui_a = f32_to_bits(a)
    ui_b = f32_to_bits(b)

    # Note: branches are swapped relative to f32_subx (per the "mudei esta
    # função" comments in the original C).
    if signF32UI(ui_a ^ ui_b):
        return softfloat_subMagsF32x(ui_a, ui_b)
    else:
        return softfloat_addMagsF32x(ui_a, ui_b)