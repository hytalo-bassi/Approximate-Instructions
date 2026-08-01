"""
Schema definitions for the fixed pattern this transpiler understands.

A source file must contain exactly ONE "main" function matching:

    def <name>(iterations, bits, [extra_scalar_kwargs...]):
        ...
        return ExecutionResult(
            final_value=...,
            history=...,
            execution_count=...,
            [metadata={...}]
        )

Anything that doesn't match a known statement/expression shape raises
UnsupportedPattern with a source location, rather than being silently
guessed at. This keeps the tool honest: it only ever emits C for
constructs it actually understands.
"""

from __future__ import annotations
import ast
from dataclasses import dataclass, field


class UnsupportedPattern(Exception):
    """Raised when source code doesn't match a known transpilable shape."""

    def __init__(self, message: str, node: ast.AST | None = None):
        loc = f" (line {node.lineno})" if node is not None and hasattr(node, "lineno") else ""
        super().__init__(f"{message}{loc}")
        self.node = node


@dataclass
class HelperFunctionIR:
    """A @helper-decorated function: produces a malloc'd array."""
    name: str
    params: list[str]              # e.g. ["n"] or ["n", "seed"]
    body_expr: ast.AST             # the single return expression (must be a comprehension)
    element_kind: str = "scalar"   # "scalar" | "tuple"
    tuple_arity: int = 1           # if element_kind == "tuple"
    param_defaults: dict = field(default_factory=dict)  # param name -> default ast.expr, for params with defaults


@dataclass
class OpCallIR:
    """A call like s_mul(a, b, bits.get('op_name', False))."""
    op_name: str                   # the bits-dict key, e.g. "h1_mul_x1"
    func: str                      # exact-mode C function, e.g. "fmul"
    args: list[ast.AST]            # the non-bits arguments (already-emitted-ready expr nodes)
    target_var: str                # the assigned variable name, e.g. "h1_a"


@dataclass
class CounterIncrIR:
    op_name: str


@dataclass
class HistoryAppendIR:
    value_expr: ast.AST


@dataclass
class PlainAssignIR:
    """Fallback: a normal assignment whose RHS is a plain expression
    (e.g. `h1 = math.tanh(h1_sum + b_h1)`), translated via the generic
    expression emitter rather than the op-call rules."""
    target_var: str
    value_expr: ast.AST
    is_augmented: bool = False   # True for `accum = fadd(accum, out, ...)`-style rebinds we keep as float


@dataclass
class MetadataEntryIR:
    key: str
    value_expr: ast.AST


@dataclass
class MainFunctionIR:
    name: str
    n_param: str
    bits_param: str
    extra_params: list[tuple[str, ast.AST | None]]  # (name, default_expr_or_None)
    constants: dict[str, float]        # module-level _W-style dict, flattened
    helper_calls: list[tuple[str, str, list[ast.AST]]]  # (result_var, helper_name, call_args)
    loop_var: str
    loop_kind: str                      # "array" | "range"
    loop_source_var: str                # ("array" kind) the array/list being iterated (usually a helper result)
    loop_unpack: list[str]              # ("array" kind) e.g. ["x1", "x2"] or ["x"] for single var
    loop_range_start: ast.AST | None    # ("range" kind) None means literal 0
    loop_range_stop: ast.AST | None     # ("range" kind) required
    loop_range_step: ast.AST | None     # ("range" kind) None means literal 1
    body_stmts: list                    # sequence of OpCallIR | CounterIncrIR | HistoryAppendIR | PlainAssignIR
    pre_loop_stmts: list                # PlainAssignIR-like, before the loop (e.g. ema = series[0])
    post_loop_stmts: list               # statements after the loop, before return
    final_value_expr: ast.AST
    history_var: str
    execution_count_var: str
    ops_tuple: list[str]                # from `<name>.ops = (...)`
    metadata: list[MetadataEntryIR] = field(default_factory=list)
    const_dict_names: set = field(default_factory=set)  # original dict var names, e.g. {"_W"}