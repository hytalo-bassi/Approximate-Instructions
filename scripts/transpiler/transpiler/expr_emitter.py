"""
Translates a (restricted) subset of Python expression AST nodes into C
expression strings. This is intentionally generic-but-narrow: arithmetic,
comparisons, literals, names, attribute access on known modules (math.*),
and known function calls. Anything outside that raises UnsupportedPattern.

This is shared by: loop-body plain assignments, metadata values, and
@helper function bodies -- one emitter, several call sites, per the
"one mechanism, not two" design decision.
"""

from __future__ import annotations
import ast

from .schema import UnsupportedPattern
from .rules import APPROX_OP_RULES, EXACT_CALL_RULES, is_approx_op, is_exact_call

_BINOP = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
    ast.Mod: "%",
}
_CMPOP = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
    ast.Eq: "==", ast.NotEq: "!=",
}


class ExprEmitter:
    """
    used_approx_ops / used_exact_calls are out-params (sets) the caller
    passes in so #include collection can happen across an entire function,
    not just one expression.
    """

    def __init__(self, used_approx_ops: set[str], used_exact_calls: set[str],
                 float_suffix: str = "f", name_rewrites: dict[str, str] | None = None,
                 len_rewrite_vars: set[str] | None = None,
                 const_dict_names: set[str] | None = None):
        self.used_approx_ops = used_approx_ops
        self.used_exact_calls = used_exact_calls
        self.float_suffix = float_suffix
        # optional rename table, e.g. loop var "x" -> "x" (identity) or
        # helper-array element access patterns
        self.name_rewrites = name_rewrites or {}
        # names of helper-call result vars: len(<name>) -> "iterations",
        # since every helper array is precomputed with length == iterations.
        self.len_rewrite_vars = len_rewrite_vars or set()
        # names of module-level constant dicts (e.g. "_W") that were
        # flattened into individual C float declarations -- so
        # `_W["w_h1_x1"]` emits as the bare identifier `w_h1_x1`, not a
        # literal C array subscript (which would be invalid/wrong).
        self.const_dict_names = const_dict_names or set()

    def emit(self, node: ast.expr) -> str:
        method = getattr(self, f"_emit_{type(node).__name__}", None)
        if method is None:
            raise UnsupportedPattern(f"unsupported expression node: {type(node).__name__}", node)
        return method(node)

    # -- literals / names -----------------------------------------------

    def _emit_Constant(self, node: ast.Constant) -> str:
        v = node.value
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, (int, float)):
            return _fmt_num(v, self.float_suffix)
        if isinstance(v, str):
            return f"\"{v}\""
        raise UnsupportedPattern(f"unsupported constant type: {type(v).__name__}", node)

    def _emit_Name(self, node: ast.Name) -> str:
        return self.name_rewrites.get(node.id, node.id)

    # -- operators --------------------------------------------------------

    def _emit_BinOp(self, node: ast.BinOp) -> str:
        op_type = type(node.op)
        if op_type not in _BINOP:
            raise UnsupportedPattern(f"unsupported binary operator: {op_type.__name__}", node)
        left = self.emit(node.left)
        right = self.emit(node.right)
        return f"({left} {_BINOP[op_type]} {right})"

    def _emit_UnaryOp(self, node: ast.UnaryOp) -> str:
        if isinstance(node.op, ast.USub):
            return f"(-{self.emit(node.operand)})"
        if isinstance(node.op, ast.UAdd):
            return self.emit(node.operand)
        raise UnsupportedPattern("unsupported unary operator", node)

    def _emit_Compare(self, node: ast.Compare) -> str:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise UnsupportedPattern("only single comparisons are supported (a < b)", node)
        op_type = type(node.ops[0])
        if op_type not in _CMPOP:
            raise UnsupportedPattern(f"unsupported comparison operator: {op_type.__name__}", node)
        left = self.emit(node.left)
        right = self.emit(node.comparators[0])
        return f"({left} {_CMPOP[op_type]} {right})"

    # -- calls --------------------------------------------------------------

    def _emit_Call(self, node: ast.Call) -> str:
        key = _call_key(node.func)

        if key and is_approx_op(key):
            # Should normally be handled at the statement level (OpCallIR),
            # but support it inline too (e.g. nested in an expression).
            if len(node.args) != 3:
                raise UnsupportedPattern(f"approx op '{key}' requires exactly 3 args", node)
            self.used_approx_ops.add(key)
            rule = APPROX_OP_RULES[key]
            a = self.emit(node.args[0])
            b = self.emit(node.args[1])
            # We don't know the bit value statically in a nested-expression
            # context; require it be lifted to a statement instead.
            raise UnsupportedPattern(
                f"approx op '{key}' must appear as a direct assignment statement, "
                f"not nested inside another expression",
                node,
            )

        if key and is_exact_call(key):
            rule = EXACT_CALL_RULES[key]
            self.used_exact_calls.add(key)
            if rule.c_fn == "__LEN__":
                if len(node.args) != 1:
                    raise UnsupportedPattern("len() takes exactly one argument", node)
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id in self.len_rewrite_vars:
                    return "iterations"
                raise UnsupportedPattern(
                    f"len() on '{ast.dump(arg)}' isn't supported -- only len() on a "
                    f"helper-array result (implicitly == iterations) is recognized", node
                )
            args = [self.emit(a) for a in node.args]
            if rule.c_fn in ("(float)", "(int)"):
                return f"{rule.c_fn}{args[0]}" if len(args) == 1 else _err_cast(node)
            return f"{rule.c_fn}({', '.join(args)})"

        raise UnsupportedPattern(
            f"unrecognized function call '{key or '<complex>'}' -- "
            f"add it to APPROX_OP_RULES or EXACT_CALL_RULES in rules.py",
            node,
        )

    def _emit_Attribute(self, node: ast.Attribute) -> str:
        # Only reachable for things like `math.pi`-style constants, which
        # we don't yet special-case; treat as unsupported explicitly.
        raise UnsupportedPattern(
            f"unsupported attribute access '{_call_key(node)}' -- "
            f"add a rule if this should translate to something", node
        )

    def _emit_Subscript(self, node: ast.Subscript) -> str:
        # _W["w_h1_x1"]  where _W is a known flattened constants dict ->
        # bare C identifier `w_h1_x1` (declared as a float earlier), not
        # a runtime array/dict lookup.
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in self.const_dict_names
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            return node.slice.value

        base = self.emit(node.value)
        idx = self.emit(node.slice)
        return f"{base}[{idx}]"

    def _emit_Tuple(self, node: ast.Tuple) -> str:
        raise UnsupportedPattern(
            "bare tuple expressions aren't directly translatable to C -- "
            "this must be handled by a caller that knows the target shape "
            "(e.g. metadata array-of-pairs, or helper element unpacking)",
            node,
        )


def _fmt_num(v: float | int, suffix: str) -> str:
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    s = repr(float(v))
    return f"{s}{suffix}"


def _call_key(func_node: ast.expr) -> str | None:
    """Turn `math.tanh` (Attribute) or `s_mul` (Name) into a lookup key."""
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute) and isinstance(func_node.value, ast.Name):
        return f"{func_node.value.id}.{func_node.attr}"
    return None


def _err_cast(node):
    raise UnsupportedPattern("cast functions take exactly one argument", node)
