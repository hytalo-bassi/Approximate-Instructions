"""
The rule tables. This is the "abc -> def" mapping layer.

Two kinds of rules:

1. APPROX_OP_RULES: functions like s_mul/s_add/s_div that take a trailing
   `bits.get("op_name", False)` argument and switch between an exact C
   function and its approximate ('x'-suffixed) counterpart.

2. EXACT_CALL_RULES: plain passthrough translations for calls that have
   no approx/exact distinction (math.tanh -> tanhf, math.sin -> sinf, etc).

Both tables also declare required #include lines, collected automatically
as the source is walked (see emitter.py: `required_includes`).
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ApproxOpRule:
    exact_fn: str          # C function used when approx bit is False
    approx_suffix: str = "x"  # approx_fn = exact_fn + approx_suffix
    includes: tuple[str, ...] = ("\"approx.h\"",)

    @property
    def approx_fn(self) -> str:
        return self.exact_fn + self.approx_suffix


# Python function name (as called in source, e.g. `s_mul`) -> C rule.
# Extend this table as new approximable ops are added to custom_approx_ops.
APPROX_OP_RULES: dict[str, ApproxOpRule] = {
    "s_mul": ApproxOpRule(exact_fn="fmul"),
    "s_add": ApproxOpRule(exact_fn="fadd"),
    "s_sub": ApproxOpRule(exact_fn="fsub"),
    "s_div": ApproxOpRule(exact_fn="fdiv"),
}


@dataclass(frozen=True)
class ExactCallRule:
    c_fn: str
    includes: tuple[str, ...] = ("<math.h>",)


# Plain (non-approximable) call translations. Key is the Python-side
# dotted or bare name as it appears in a Call node (see emitter._call_key).
EXACT_CALL_RULES: dict[str, ExactCallRule] = {
    "math.tanh": ExactCallRule(c_fn="tanhf"),
    "math.sin": ExactCallRule(c_fn="sinf"),
    "math.cos": ExactCallRule(c_fn="cosf"),
    "math.exp": ExactCallRule(c_fn="expf"),
    "math.log": ExactCallRule(c_fn="logf"),
    "math.sqrt": ExactCallRule(c_fn="sqrtf"),
    "math.fabs": ExactCallRule(c_fn="fabsf"),
    "abs": ExactCallRule(c_fn="fabsf"),
    "float": ExactCallRule(c_fn="(float)", includes=()),
    "int": ExactCallRule(c_fn="(int)", includes=()),
    "len": ExactCallRule(c_fn="__LEN__", includes=()),  # special-cased in emitter
}


def is_approx_op(func_name: str) -> bool:
    return func_name in APPROX_OP_RULES


def is_exact_call(func_key: str) -> bool:
    return func_key in EXACT_CALL_RULES


def all_includes_for(used_approx_ops: set[str], used_exact_calls: set[str]) -> list[str]:
    """Collect the deduplicated, ordered list of #include lines needed."""
    includes: list[str] = []
    for op in used_approx_ops:
        for inc in APPROX_OP_RULES[op].includes:
            if inc not in includes:
                includes.append(inc)
    for call in used_exact_calls:
        for inc in EXACT_CALL_RULES[call].includes:
            if inc not in includes:
                includes.append(inc)
    return includes
