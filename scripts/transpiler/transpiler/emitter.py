"""
Turns the IR (schema.py) into the final C source string, matching the
common_api / approx.h boilerplate style shown in the target examples.
"""

from __future__ import annotations
import ast

from .schema import (
    MainFunctionIR, HelperFunctionIR, OpCallIR, CounterIncrIR,
    HistoryAppendIR, PlainAssignIR, MetadataEntryIR, UnsupportedPattern,
)
from .rules import APPROX_OP_RULES, all_includes_for
from .expr_emitter import ExprEmitter

INDENT = "    "


def emit_c_source(ir: MainFunctionIR, helpers: dict[str, HelperFunctionIR],
                   bits: dict[str, bool] | None = None, iterations: int = 1000) -> str:
    """
    bits: op_name -> True (use approx variant, e.g. fmulx) | False (exact, fmul).
    Missing keys default to False, matching bits.get(op_name, False) in the
    Python source. This mirrors running the Python function with a specific
    `bits` dict, baking that choice into the generated C at transpile time.

    iterations: baked in as the literal value of the `iterations`/`n`
    parameter in the generated C (C has no runtime argument for it, so
    this must be fixed at transpile time, matching the value you'd pass
    as the first positional argument when calling the Python function).
    """
    bits = bits or {}
    used_approx: set[str] = set()
    used_exact: set[str] = set()
    global _declared_vars
    _declared_vars = set()

    def make_emitter(**kwargs) -> ExprEmitter:
        kwargs.setdefault("const_dict_names", ir.const_dict_names)
        return ExprEmitter(used_approx, used_exact, **kwargs)

    # Pre-scan op-call statements so #includes are known before we start
    # writing lines (approx ops are always used via OpCallIR, tracked here).
    for stmt in ir.body_stmts:
        if isinstance(stmt, OpCallIR):
            used_approx.add(stmt.func)

    lines: list[str] = []
    lines.append("#include <stdio.h>")
    lines.append("#include <stdlib.h>")
    lines.append("#include <math.h>")
    lines.append('#include "approx.h" // standard lib for the approx and exact functions')
    lines.append("#define COMMON_API_IMPLEMENTATION")
    lines.append('#include "common.h" // standard boilerplate too')
    lines.append("")

    # -- helper function C translations (emitted as standalone functions) --
    used_helpers = {name for _, name, _ in ir.helper_calls}
    for hname in used_helpers:
        h = helpers[hname]
        lines.extend(_emit_helper_function(h, make_emitter))
        lines.append("")

    lines.append("int main(int argc, char *argv[]) {")
    lines.append(f"{INDENT}if (argc < 2) {{")
    lines.append(f"{INDENT * 2}return 1;")
    lines.append(f"{INDENT}}}")
    lines.append(f'{INDENT}char *caminho_saida = argv[argc - 1]; // boilerplate for json writing')
    lines.append(f"{INDENT}common_api_init(); // boilerplate to API json writing")
    lines.append("")

    lines.append(f"{INDENT}int {ir.n_param} = {iterations}; // matches iterations from python")

    for pname, default in ir.extra_params:
        emitter = make_emitter()
        if default is None:
            raise UnsupportedPattern(
                f"extra parameter '{pname}' has no default value -- "
                f"the transpiler needs a concrete value to bake in"
            )
        val = emitter.emit(default)
        lines.append(f"{INDENT}float {pname} = {val};")

    if ir.constants:
        const_decls = ", ".join(f"{k} = {_fmt_const(v)}" for k, v in ir.constants.items())
        lines.append(f"{INDENT}float {const_decls}; // weights/biases translated from python constants")
    lines.append("")

    # -- helper call sites -> malloc'd arrays -----------------------------
    for result_var, hname, call_args in ir.helper_calls:
        h = helpers[hname]
        lines.extend(_emit_helper_call_site(result_var, h, call_args, make_emitter))
        lines.append("")

    # -- pre-loop statements ------------------------------------------------
    if ir.pre_loop_stmts:
        emitter = make_emitter()
        for stmt in ir.pre_loop_stmts:
            if isinstance(stmt, HistoryAppendIR):
                val = emitter.emit(stmt.value_expr)
                lines.append(f"{INDENT}common_api_history_push_number((double){val});")
            elif isinstance(stmt, PlainAssignIR):
                declare = _mark_declared(stmt.target_var)
                lines.append(f"{INDENT}{_emit_plain_assign(stmt, emitter, declare=declare)}")
            else:
                raise UnsupportedPattern(f"unhandled pre-loop statement type: {type(stmt).__name__}")
        lines.append("")

    # -- main loop ------------------------------------------------------------
    body_emitter = make_emitter()

    if ir.loop_kind == "range":
        # for <loop_var> in range(start, stop, step) -> a plain C for loop;
        # the loop variable is used directly in the body (not as an array
        # index), so it's declared as `int` and body expressions cast it
        # via float(...) themselves where needed (existing EXACT_CALL_RULES
        # handling for float()/int() already covers that).
        range_emitter = make_emitter()
        start_c = range_emitter.emit(ir.loop_range_start) if ir.loop_range_start is not None else "0"
        stop_c = range_emitter.emit(ir.loop_range_stop)
        step_c = range_emitter.emit(ir.loop_range_step) if ir.loop_range_step is not None else None

        loop_var = ir.loop_var
        if step_c is None:
            lines.append(
                f"{INDENT}for (int {loop_var} = {start_c}; {loop_var} < {stop_c}; {loop_var}++) {{"
            )
        else:
            # step may be negative (range(a, b, -1)); emitting a generic
            # `+=` covers the common ascending case correctly, but a
            # negative literal step would need `>` instead of `<` for the
            # loop condition to ever be false. Since we can't always tell
            # the sign of an arbitrary expression at transpile time, only
            # a literal step is supported for now -- anything else is
            # rejected rather than silently emitting an infinite loop.
            if isinstance(ir.loop_range_step, ast.Constant) and isinstance(ir.loop_range_step.value, (int, float)):
                step_val = ir.loop_range_step.value
                cmp = "<" if step_val > 0 else ">"
                lines.append(
                    f"{INDENT}for (int {loop_var} = {start_c}; {loop_var} {cmp} {stop_c}; "
                    f"{loop_var} += {step_c}) {{"
                )
            else:
                raise UnsupportedPattern(
                    "range() with a non-constant step isn't supported -- "
                    "the sign of the step can't be determined at transpile time"
                )
    else:
        loop_source = ir.helper_calls[0][0] if ir.helper_calls else ir.loop_source_var
        lines.append(f"{INDENT}for (int i = 0; i < {ir.n_param}; i++) {{")

        if len(ir.loop_unpack) == 1 and ir.loop_var != "__tuple__":
            var = ir.loop_unpack[0]
            lines.append(f"{INDENT * 2}float {var} = {loop_source}[i];")
        else:
            for idx, name in enumerate(ir.loop_unpack):
                lines.append(f"{INDENT * 2}float {name} = {loop_source}_{idx}[i];")

    for stmt in ir.body_stmts:
        lines.extend(_emit_loop_stmt(stmt, body_emitter, ir, bits))

    lines.append(f"{INDENT}}}")
    lines.append("")

    # -- post-loop statements -----------------------------------------------
    helper_result_vars = {rv for rv, _, _ in ir.helper_calls}
    if ir.post_loop_stmts:
        emitter = make_emitter(len_rewrite_vars=helper_result_vars)
        for stmt in ir.post_loop_stmts:
            lines.extend(_emit_post_loop_stmt(stmt, emitter, bits))

    # -- final value + metadata + output -------------------------------------
    final_emitter = make_emitter(len_rewrite_vars=helper_result_vars)

    # If final_value_expr is just a bare Name that a post-loop (or in-loop)
    # statement already assigned -- e.g. `final_value = s_div(...)` was
    # already emitted as a post-loop OpCallIR producing a C variable named
    # `final_value` -- don't re-declare it. Only emit a fresh `float
    # final_value = ...;` when the return expression is something new
    # (e.g. `final_value=accum` referencing the loop accumulator directly,
    # or `final_value=ema`).
    if isinstance(ir.final_value_expr, ast.Name) and ir.final_value_expr.id in _declared_vars:
        final_val_name = ir.final_value_expr.id
        if final_val_name == "final_value":
            pass  # already declared as `final_value` by a post-loop statement -- reuse it directly
        else:
            lines.append(f"{INDENT}float final_value = {final_val_name};")
    else:
        final_val_c = final_emitter.emit(ir.final_value_expr)
        lines.append(f"{INDENT}float final_value = {final_val_c};")

    lines.append(f"{INDENT}common_api_set_final_value((double)final_value); // sets final value in history")

    if ir.metadata:
        lines.append("")
        for entry in ir.metadata:
            lines.extend(_emit_metadata_entry(entry, make_emitter, helpers, ir.history_var))

    lines.append("")
    lines.append(f"{INDENT}common_api_output(caminho_saida); // writes")
    lines.append(f"{INDENT}common_api_free(); // clears")

    for result_var, hname, _ in ir.helper_calls:
        h = helpers[hname]
        if h.element_kind == "scalar":
            lines.append(f"{INDENT}free({result_var});")
        else:
            for i in range(h.tuple_arity):
                lines.append(f"{INDENT}free({result_var}_{i});")

    lines.append(f"{INDENT}return 0;")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------- pieces --

def _emit_helper_function(h: HelperFunctionIR, make_emitter) -> list[str]:
    """
    Emits a C function that returns a malloc'd array for a @helper-decorated
    Python function. Only single-scalar-output comprehensions over range(n)
    are currently supported (the shapes seen in practice); tuple-element
    comprehensions are emitted as N parallel arrays via out-params.
    """
    comp = h.body_expr  # ast.ListComp
    generators = comp.generators
    if len(generators) != 1:
        raise UnsupportedPattern(f"@helper '{h.name}': only single-generator comprehensions are supported")
    gen = generators[0]
    if not (isinstance(gen.iter, ast.Call) and isinstance(gen.iter.func, ast.Name) and gen.iter.func.id == "range"):
        raise UnsupportedPattern(f"@helper '{h.name}': comprehension must iterate over range(...)")
    if not isinstance(gen.target, ast.Name):
        raise UnsupportedPattern(f"@helper '{h.name}': range loop variable must be a simple name")
    loop_var = gen.target.id

    n_param = h.params[0] if h.params else "n"
    extra_params = h.params[1:]

    lines: list[str] = []
    if h.element_kind == "scalar":
        lines.append(f"float *{h.name}(int {n_param}{'' if not extra_params else ', ' + ', '.join(f'float {p}' for p in extra_params)}) {{")
        lines.append(f"{INDENT}float *out = (float *)malloc(sizeof(float) * {n_param});")
        lines.append(f"{INDENT}for (int {loop_var} = 0; {loop_var} < {n_param}; {loop_var}++) {{")
        emitter = make_emitter()
        val = emitter.emit(comp.elt)
        lines.append(f"{INDENT * 2}out[{loop_var}] = {val};")
        lines.append(f"{INDENT}}}")
        lines.append(f"{INDENT}return out;")
        lines.append("}")
    else:
        # tuple element: emit N parallel out-arrays via pointer-to-pointer params
        elts = comp.elt.elts
        out_names = [f"out{i}" for i in range(len(elts))]
        params_decl = ", ".join([f"int {n_param}"] + [f"float {p}" for p in extra_params] + [f"float **{o}" for o in out_names])
        lines.append(f"void {h.name}({params_decl}) {{")
        for o in out_names:
            lines.append(f"{INDENT}*{o} = (float *)malloc(sizeof(float) * {n_param});")
        lines.append(f"{INDENT}for (int {loop_var} = 0; {loop_var} < {n_param}; {loop_var}++) {{")
        emitter = make_emitter()
        for i, elt in enumerate(elts):
            val = emitter.emit(elt)
            lines.append(f"{INDENT * 2}(*{out_names[i]})[{loop_var}] = {val};")
        lines.append(f"{INDENT}}}")
        lines.append("}")
    return lines


def _emit_helper_call_site(result_var: str, h: HelperFunctionIR, call_args: list, make_emitter) -> list[str]:
    lines = []
    emitter = make_emitter(name_rewrites={"iterations": "iterations", "n": "iterations"})

    # C has no default arguments, so any parameter the Python call site
    # omits (relying on the helper's own default, e.g. `seed=0`) must be
    # filled in explicitly here using that same default expression.
    extra_params = h.params[1:]  # first param is always n/iterations
    n_supplied = len(call_args) - 1  # call_args[0] is iterations/n
    full_args = list(call_args)
    for pname in extra_params[max(n_supplied, 0):]:
        if pname not in h.param_defaults:
            raise UnsupportedPattern(
                f"call to helper '{h.name}' omits required parameter '{pname}' with no default"
            )
        full_args.append(h.param_defaults[pname])

    c_args = [emitter.emit(a) if not (isinstance(a, ast.Name) and a.id in ("iterations", "n")) else "iterations"
              for a in full_args]

    if h.element_kind == "scalar":
        args_str = ", ".join(c_args) if c_args else "iterations"
        lines.append(f"{INDENT}float *{result_var} = {h.name}({args_str});")
    else:
        for i in range(h.tuple_arity):
            lines.append(f"{INDENT}float *{result_var}_{i};")
        args_str = ", ".join(c_args) if c_args else "iterations"
        ptr_args = ", ".join(f"&{result_var}_{i}" for i in range(h.tuple_arity))
        lines.append(f"{INDENT}{h.name}({args_str}, {ptr_args});")
    return lines


def _emit_loop_stmt(stmt, emitter: ExprEmitter, ir: MainFunctionIR, bits: dict) -> list[str]:
    if isinstance(stmt, CounterIncrIR):
        return [f'{INDENT * 2}common_api_history_increment("{stmt.op_name}"); // history.append detected']

    if isinstance(stmt, OpCallIR):
        rule = APPROX_OP_RULES[stmt.func]
        emitter.used_approx_ops.add(stmt.func)
        a = emitter.emit(stmt.args[0])
        b = emitter.emit(stmt.args[1])
        use_approx = bits.get(stmt.op_name, False)
        c_fn = rule.approx_fn if use_approx else rule.exact_fn
        prefix = "float " if _mark_declared(stmt.target_var) else ""
        return [f"{INDENT * 2}{prefix}{stmt.target_var} = {c_fn}({a}, {b});"]

    if isinstance(stmt, HistoryAppendIR):
        val = emitter.emit(stmt.value_expr)
        return [f"{INDENT * 2}common_api_history_push_number((double){val}); // another history for iteration granularity inspection"]

    if isinstance(stmt, PlainAssignIR):
        declare = _mark_declared(stmt.target_var)
        return [f"{INDENT * 2}{_emit_plain_assign(stmt, emitter, declare=declare)}"]

    raise UnsupportedPattern(f"unhandled loop statement type: {type(stmt).__name__}")


_declared_vars: set = set()


def _mark_declared(var_name: str) -> bool:
    if var_name in _declared_vars:
        return False
    _declared_vars.add(var_name)
    return True


def _emit_post_loop_stmt(stmt, emitter: ExprEmitter, bits: dict) -> list[str]:
    if isinstance(stmt, CounterIncrIR):
        return [f'{INDENT}common_api_history_increment("{stmt.op_name}");']

    if isinstance(stmt, OpCallIR):
        rule = APPROX_OP_RULES[stmt.func]
        emitter.used_approx_ops.add(stmt.func)
        a = emitter.emit(stmt.args[0])
        b = emitter.emit(stmt.args[1])
        use_approx = bits.get(stmt.op_name, False)
        c_fn = rule.approx_fn if use_approx else rule.exact_fn
        prefix = "float " if _mark_declared(stmt.target_var) else ""
        return [f"{INDENT}{prefix}{stmt.target_var} = {c_fn}({a}, {b});"]

    if isinstance(stmt, PlainAssignIR):
        declare = _mark_declared(stmt.target_var)
        return [f"{INDENT}{_emit_plain_assign(stmt, emitter, declare=declare)}"]

    raise UnsupportedPattern(f"unhandled post-loop statement type: {type(stmt).__name__}")


def _emit_plain_assign(stmt: PlainAssignIR, emitter: ExprEmitter, declare: bool) -> str:
    val = emitter.emit(stmt.value_expr)
    prefix = "float " if declare else ""
    return f"{prefix}{stmt.target_var} = {val};"


def _emit_metadata_entry(entry: MetadataEntryIR, make_emitter, helpers: dict, history_var: str) -> list[str]:
    key = entry.key
    value = entry.value_expr
    emitter = make_emitter()

    if isinstance(value, ast.Constant):
        if isinstance(value.value, bool):
            return [f'{INDENT}common_api_metadata_set_bool("{key}", {1 if value.value else 0});']
        if isinstance(value.value, (int, float)):
            return [f'{INDENT}common_api_metadata_set_number("{key}", {_fmt_const(float(value.value))});']
        if isinstance(value.value, str):
            return [f'{INDENT}common_api_metadata_set_string("{key}", "{value.value}");']

    if isinstance(value, ast.ListComp):
        # e.g. [(i, v) for i, v in enumerate(history)]  -> array-of-pairs metadata
        return _emit_metadata_array_of_pairs(key, value, make_emitter, helpers, history_var)

    raise UnsupportedPattern(
        f"metadata key '{key}': unsupported value shape '{type(value).__name__}' -- "
        f"supported: string/number/bool constants, or [(i, v) for ...] list comprehensions"
    )


def _emit_metadata_array_of_pairs(key: str, comp: ast.ListComp, make_emitter,
                                   helpers: dict, history_var: str) -> list[str]:
    # Recognizes: [(i, v) for i, v in enumerate(<source>)]
    # <source> can be:
    #   - the loop's own history variable (e.g. `history`)      -> use the
    #     runtime history buffer directly, no new array needed
    #   - a fresh call to a @helper function (e.g.
    #     `_synthetic_series(iterations)`) -> materialize it as its own
    #     local malloc'd array first, then reference that
    gen = comp.generators[0]
    if not (
        isinstance(gen.iter, ast.Call) and len(gen.iter.args) == 1
        and isinstance(gen.iter.func, ast.Name) and gen.iter.func.id == "enumerate"
    ):
        raise UnsupportedPattern(f"metadata key '{key}': only enumerate(...) sources are supported")

    source = gen.iter.args[0]
    lines: list[str] = []

    if isinstance(source, ast.Name) and source.id == history_var:
        return [
            f'{INDENT}common_api_metadata_set_array_from_history("{key}"); '
            f'// array-of-(index,value) pairs from the runtime history buffer'
        ]

    if isinstance(source, ast.Call) and isinstance(source.func, ast.Name) and source.func.id in helpers:
        h = helpers[source.func.id]
        if h.element_kind != "scalar":
            raise UnsupportedPattern(
                f"metadata key '{key}': enumerate() over a tuple-element @helper isn't supported"
            )
        local_var = f"_meta_{key}_arr"
        lines.extend(_emit_helper_call_site(local_var, h, source.args, make_emitter))
        lines.append(
            f'{INDENT}common_api_metadata_set_array("{key}", {local_var}, iterations); '
            f'// array-of-(index,value) pairs from {source.func.id}(...)'
        )
        lines.append(f"{INDENT}free({local_var});")
        return lines

    raise UnsupportedPattern(
        f"metadata key '{key}': enumerate() source must be the history variable "
        f"or a direct call to a @helper function"
    )


def _fmt_const(v: float) -> str:
    return f"{v}f"


# (includes are hardcoded in the emit_c_source() header to match the
# fixed common_api/approx.h boilerplate; all_includes_for() is retained
# in rules.py for callers that want to inspect per-op dependencies.)