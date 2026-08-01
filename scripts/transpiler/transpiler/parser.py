"""
Parses a source .py file into the IR defined in schema.py.

Strategy: walk the module top-down, classify each top-level definition
(module constants dict, @helper functions, the one main function), then
walk the main function's body statement-by-statement, matching each
statement against a known shape. Anything unrecognized raises
UnsupportedPattern with a line number rather than being guessed at.
"""

from __future__ import annotations
import ast

from .schema import (
    UnsupportedPattern, HelperFunctionIR, OpCallIR, CounterIncrIR,
    HistoryAppendIR, PlainAssignIR, MainFunctionIR, MetadataEntryIR,
)
from .rules import is_approx_op


def parse_source(source: str, filename: str = "<source>") -> tuple[MainFunctionIR, dict[str, HelperFunctionIR]]:
    tree = ast.parse(source, filename=filename)

    module_constants: dict[str, dict[str, float]] = {}
    helpers: dict[str, HelperFunctionIR] = {}
    main_fn_node: ast.FunctionDef | None = None
    ops_by_fn: dict[str, list[str]] = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            # module-level constants dict, e.g. _W = {...}
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                dict_name = node.targets[0].id
                if isinstance(node.value, ast.Dict):
                    module_constants[dict_name] = _flatten_const_dict(node.value)

            # <fn>.ops = (...)
            elif (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Attribute)
                and node.targets[0].attr == "ops"
                and isinstance(node.targets[0].value, ast.Name)
            ):
                owner = node.targets[0].value.id
                if isinstance(node.value, (ast.Tuple, ast.List)):
                    ops_by_fn[owner] = [_expect_str_const(e) for e in node.value.elts]

        elif isinstance(node, ast.FunctionDef):
            if _is_helper_decorated(node):
                helpers[node.name] = _parse_helper(node)
            else:
                # candidate for the main function; validated below by signature
                if _looks_like_main(node):
                    if main_fn_node is not None:
                        raise UnsupportedPattern(
                            f"multiple candidate main functions found "
                            f"('{main_fn_node.name}' and '{node.name}') — expected exactly one",
                            node,
                        )
                    main_fn_node = node

    if main_fn_node is None:
        raise UnsupportedPattern("no main function found with signature (iterations, bits, ...)")

    ir = _parse_main_function(main_fn_node, module_constants, helpers, ops_by_fn)
    return ir, helpers


# ---------------------------------------------------------------- helpers --

def _is_helper_decorated(node: ast.FunctionDef) -> bool:
    for dec in node.decorator_list:
        name = _decorator_name(dec)
        if name in ("helper", "transpile.helper"):
            return True
    return False


def _decorator_name(dec: ast.expr) -> str:
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        base = _decorator_name(dec.value)
        return f"{base}.{dec.attr}"
    return ""


def _looks_like_main(node: ast.FunctionDef) -> bool:
    args = node.args
    positional = [a.arg for a in args.args]
    return len(positional) >= 2 and positional[0] in ("iterations", "n") and positional[1] == "bits"


def _flatten_const_dict(d: ast.Dict) -> dict[str, float]:
    out = {}
    for k, v in zip(d.keys, d.values):
        key = _expect_str_const(k)
        out[key] = _expect_num_const(v)
    return out


def _expect_str_const(node: ast.expr) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise UnsupportedPattern("expected a string literal here", node)


def _expect_num_const(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_expect_num_const(node.operand)
    raise UnsupportedPattern("expected a numeric literal here", node)


def _parse_helper(node: ast.FunctionDef) -> HelperFunctionIR:
    params = [a.arg for a in node.args.args]
    defaults = node.args.defaults  # aligned to the END of args.args
    param_defaults: dict[str, ast.expr] = {}
    n_defaults = len(defaults)
    n_params = len(params)
    for i, default in enumerate(defaults):
        param_name = params[n_params - n_defaults + i]
        param_defaults[param_name] = default

    # Expect: return <listcomp>
    if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        raise UnsupportedPattern(
            f"@helper function '{node.name}' must be a single `return <list comprehension>` statement",
            node,
        )
    ret_val = node.body[0].value
    if not isinstance(ret_val, ast.ListComp):
        raise UnsupportedPattern(
            f"@helper function '{node.name}' must return a list comprehension", ret_val
        )

    elt = ret_val.elt
    if isinstance(elt, ast.Tuple):
        return HelperFunctionIR(
            name=node.name, params=params, body_expr=ret_val,
            element_kind="tuple", tuple_arity=len(elt.elts), param_defaults=param_defaults,
        )
    return HelperFunctionIR(name=node.name, params=params, body_expr=ret_val,
                             element_kind="scalar", param_defaults=param_defaults)


def _parse_main_function(
    node: ast.FunctionDef,
    module_constants: dict[str, dict[str, float]],
    helpers: dict[str, HelperFunctionIR],
    ops_by_fn: dict[str, list[str]],
) -> MainFunctionIR:
    args = node.args
    positional = [a.arg for a in args.args]
    n_param, bits_param, *extra_names = positional

    extra_params: list[tuple[str, ast.AST | None]] = []
    n_extra = len(extra_names)
    defaults = args.defaults  # aligned to the END of args.args
    n_defaults = len(defaults)
    for i, name in enumerate(extra_names):
        # index into defaults: defaults apply to the trailing args of args.args
        offset = i - (n_extra - n_defaults)
        default = defaults[offset] if offset >= 0 else None
        extra_params.append((name, default))

    ops_tuple = ops_by_fn.get(node.name, [])

    stmts = list(node.body)
    # Drop leading docstring
    if stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant) \
            and isinstance(stmts[0].value.value, str):
        stmts = stmts[1:]

    pre_loop: list = []
    helper_calls: list[tuple[str, str, list]] = []
    loop_node: ast.For | None = None
    history_var = "history"
    execution_count_var = "execution_count"
    final_value_expr = None
    return_node: ast.Return | None = None
    post_loop: list = []

    seen_loop = False
    for stmt in stmts:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            target = stmt.targets[0].id
            value = stmt.value

            # inputs = _synthetic_inputs(iterations)  -> helper call
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in helpers:
                if seen_loop:
                    raise UnsupportedPattern("helper calls after the main loop aren't supported", stmt)
                helper_calls.append((target, value.func.id, value.args))
                continue

            # execution_count = {op: 0 for op in <fn>.ops}
            if isinstance(value, ast.DictComp):
                execution_count_var = target
                continue

            # history = []  (empty init -- pure bookkeeping, no C output needed
            # since history is tracked entirely via common_api_history_* calls)
            if not seen_loop and isinstance(value, ast.List) and len(value.elts) == 0:
                history_var = target
                continue

            # history = [ema]  (seeded with a real value -- needs an initial
            # common_api_history_push_number emitted before the loop starts)
            if not seen_loop and isinstance(value, ast.List) and len(value.elts) == 1:
                history_var = target
                pre_loop.append(HistoryAppendIR(value_expr=value.elts[0]))
                continue

            # generic scalar assign, before or after the loop
            if not seen_loop:
                pre_loop.append(PlainAssignIR(target_var=target, value_expr=value))
            else:
                post_loop.append(_classify_post_loop_assign(target, value))
            continue

        # execution_count["op"] += 1  appearing after the loop (e.g. final_div)
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Subscript):
            if not seen_loop:
                raise UnsupportedPattern("counter increment found before the main loop", stmt)
            t = stmt.target
            if isinstance(t.value, ast.Name) and t.value.id == execution_count_var:
                post_loop.append(CounterIncrIR(op_name=_subscript_str_key(t.slice)))
                continue
            raise UnsupportedPattern("unsupported augmented assignment after loop", stmt)

        if isinstance(stmt, ast.For):
            if seen_loop:
                raise UnsupportedPattern("only one main loop per function is supported", stmt)
            loop_node = stmt
            seen_loop = True
            continue

        if isinstance(stmt, ast.Return):
            return_node = stmt
            continue

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue  # stray docstring/comment-like expr, ignore

        raise UnsupportedPattern(f"unsupported top-level statement in '{node.name}'", stmt)

    if loop_node is None:
        raise UnsupportedPattern(f"no main `for` loop found in '{node.name}'", node)
    if return_node is None:
        raise UnsupportedPattern(f"no `return ExecutionResult(...)` found in '{node.name}'", node)

    loop_var, loop_unpack = _parse_loop_target(loop_node.target)
    loop_iter_info = _parse_loop_iter(loop_node.iter)

    if loop_iter_info[0] == "range":
        _, range_start, range_stop, range_step = loop_iter_info
        if loop_var == "__tuple__":
            raise UnsupportedPattern(
                "range(...) loops must use a single loop variable, not a tuple unpack", loop_node.target
            )
        loop_kind = "range"
        loop_source_var = ""
        loop_range_start, loop_range_stop, loop_range_step = range_start, range_stop, range_step
    else:
        _, source_var = loop_iter_info
        loop_kind = "array"
        loop_source_var = source_var
        loop_range_start = loop_range_stop = loop_range_step = None

    body_stmts = [_parse_body_stmt(s, execution_count_var, history_var) for s in loop_node.body]

    final_value_expr, hist_var_from_return, exec_var_from_return, metadata = _parse_return(return_node)

    return MainFunctionIR(
        name=node.name,
        n_param=n_param,
        bits_param=bits_param,
        extra_params=extra_params,
        constants=_merge_constants(module_constants),
        const_dict_names=set(module_constants.keys()),
        helper_calls=helper_calls,
        loop_var=loop_var,
        loop_kind=loop_kind,
        loop_source_var=loop_source_var,
        loop_unpack=loop_unpack,
        loop_range_start=loop_range_start,
        loop_range_stop=loop_range_stop,
        loop_range_step=loop_range_step,
        body_stmts=body_stmts,
        pre_loop_stmts=pre_loop,
        post_loop_stmts=post_loop,
        final_value_expr=final_value_expr,
        history_var=hist_var_from_return or history_var,
        execution_count_var=exec_var_from_return or execution_count_var,
        ops_tuple=ops_tuple,
        metadata=metadata,
    )


def _merge_constants(module_constants: dict[str, dict[str, float]]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for d in module_constants.values():
        merged.update(d)
    return merged


def _parse_loop_target(target: ast.expr) -> tuple[str, list[str]]:
    if isinstance(target, ast.Name):
        return target.id, [target.id]
    if isinstance(target, ast.Tuple):
        names = []
        for elt in target.elts:
            if not isinstance(elt, ast.Name):
                raise UnsupportedPattern("loop unpack target must be simple names", target)
            names.append(elt.id)
        return "__tuple__", names
    raise UnsupportedPattern("unsupported for-loop target", target)


def _parse_loop_iter(it: ast.expr):
    """
    Returns a tuple describing the loop source:
        ("array", source_var_name)
        ("range", start_expr_or_None, stop_expr, step_expr_or_None)

    Recognizes:
        for x1, x2 in inputs        -> ("array", "inputs")
        for x in series[1:]         -> ("array", "series")   (slice bound ignored,
                                        matches existing pre-slice behavior)
        for i in range(n)           -> ("range", None, n, None)
        for i in range(a, b)        -> ("range", a, b, None)
        for i in range(a, b, s)     -> ("range", a, b, s)
    """
    if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
        args = it.args
        if len(args) == 1:
            return ("range", None, args[0], None)
        if len(args) == 2:
            return ("range", args[0], args[1], None)
        if len(args) == 3:
            return ("range", args[0], args[1], args[2])
        raise UnsupportedPattern("range() must have 1, 2, or 3 arguments", it)

    if isinstance(it, ast.Name):
        return ("array", it.id)
    if isinstance(it, ast.Subscript) and isinstance(it.value, ast.Name):
        return ("array", it.value.id)  # caller can inspect slice separately if needed
    raise UnsupportedPattern(
        "loop source must be a plain name, a simple slice of a name, or range(...)", it
    )


def _classify_post_loop_assign(target: str, value: ast.expr):
    """Same recognition as an in-loop assignment (approx op-call vs plain),
    used for post-loop statements like `final_value = s_div(accum, n, bits.get(...))`."""
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and is_approx_op(value.func.id):
        if len(value.args) != 3:
            raise UnsupportedPattern(
                f"approx op call '{value.func.id}' must have exactly 3 args (a, b, bits.get(...))", value
            )
        a_arg, b_arg, bits_arg = value.args
        op_name = _extract_bits_get_key(bits_arg)
        return OpCallIR(op_name=op_name, func=value.func.id, args=[a_arg, b_arg], target_var=target)
    return PlainAssignIR(target_var=target, value_expr=value)


def _parse_body_stmt(stmt: ast.stmt, execution_count_var: str, history_var: str):
    # execution_count["op"] += 1
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Subscript):
        target = stmt.target
        if isinstance(target.value, ast.Name) and target.value.id == execution_count_var:
            op_name = _subscript_str_key(target.slice)
            return CounterIncrIR(op_name=op_name)
        raise UnsupportedPattern("unsupported augmented assignment", stmt)

    # history.append(expr)
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "append"
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == history_var
        ):
            if len(call.args) != 1:
                raise UnsupportedPattern("history.append() must take exactly one argument", call)
            return HistoryAppendIR(value_expr=call.args[0])
        raise UnsupportedPattern("unsupported bare call statement", stmt)

    # commented-out lines never appear as AST nodes at all (Python strips
    # comments at parse time), so nothing special is needed for that case.

    # x = s_mul(a, b, bits.get("op", False))  OR  x = <anything else>
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        target_var = stmt.targets[0].id
        value = stmt.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and is_approx_op(value.func.id):
            op_call = value
            if len(op_call.args) != 3:
                raise UnsupportedPattern(
                    f"approx op call '{value.func.id}' must have exactly 3 args (a, b, bits.get(...))",
                    op_call,
                )
            a_arg, b_arg, bits_arg = op_call.args
            op_name = _extract_bits_get_key(bits_arg)
            return OpCallIR(op_name=op_name, func=value.func.id, args=[a_arg, b_arg], target_var=target_var)

        # generic assignment (math.tanh(...), plain arithmetic, etc.)
        return PlainAssignIR(target_var=target_var, value_expr=value)

    raise UnsupportedPattern("unsupported statement inside main loop", stmt)


def _subscript_str_key(slice_node: ast.expr) -> str:
    # Py3.9+: slice is the expr directly (no ast.Index wrapper)
    node = slice_node
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise UnsupportedPattern("expected a string subscript key", slice_node)


def _extract_bits_get_key(node: ast.expr) -> str:
    # bits.get("op_name", False)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and len(node.args) >= 1
    ):
        key_node = node.args[0]
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            return key_node.value
    raise UnsupportedPattern("expected bits.get(\"op_name\", False) as the third argument", node)


def _parse_return(node: ast.Return):
    call = node.value
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "ExecutionResult"):
        raise UnsupportedPattern("return statement must construct ExecutionResult(...)", node)

    final_value_expr = None
    history_var = None
    exec_var = None
    metadata: list[MetadataEntryIR] = []

    for kw in call.keywords:
        if kw.arg == "final_value":
            final_value_expr = kw.value
        elif kw.arg == "history":
            if isinstance(kw.value, ast.Name):
                history_var = kw.value.id
        elif kw.arg == "execution_count":
            if isinstance(kw.value, ast.Name):
                exec_var = kw.value.id
        elif kw.arg == "metadata":
            if not isinstance(kw.value, ast.Dict):
                raise UnsupportedPattern("metadata= must be a dict literal", kw.value)
            for k, v in zip(kw.value.keys, kw.value.values):
                key = _expect_str_const(k)
                metadata.append(MetadataEntryIR(key=key, value_expr=v))
        else:
            raise UnsupportedPattern(f"unsupported ExecutionResult keyword '{kw.arg}'", kw.value)

    if final_value_expr is None:
        raise UnsupportedPattern("ExecutionResult(...) missing final_value=", node)

    return final_value_expr, history_var, exec_var, metadata