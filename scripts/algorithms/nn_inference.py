from analyzing.custom_approx_ops import *
from analyzing.scoring import ExecutionResult
import math

_W = {
    "w_h1_x1": 0.8, "w_h1_x2": -0.5, "b_h1": 0.10,
    "w_h2_x1": -0.3, "w_h2_x2": 0.9, "b_h2": -0.20,
    "w_out_h1": 1.2, "w_out_h2": -0.7, "b_out": 0.05,
}


def _synthetic_inputs(n):
    return [(math.sin(i * 0.31), math.cos(i * 0.17)) for i in range(n)]
 
 
def nn_inference(iterations, bits):
    """
    bits: dict keyed by op name (see nn_inference.ops below), e.g.
          {"h1_mul_x1": True, "out_add": True, ...}. Missing keys default
          to False (exact) via bits.get(...).
    """
    inputs = _synthetic_inputs(iterations)
 
    accum = 0.0
    history = []
    execution_count = {op: 0 for op in nn_inference.ops}
 
    for x1, x2 in inputs:
        execution_count["h1_mul_x1"] += 1
        h1_a = s_mul(_W["w_h1_x1"], x1, bits.get("h1_mul_x1", False))
        execution_count["h1_mul_x2"] += 1
        h1_b = s_mul(_W["w_h1_x2"], x2, bits.get("h1_mul_x2", False))
        execution_count["h1_add"] += 1
        h1_sum = s_add(h1_a, h1_b, bits.get("h1_add", False))
        h1 = math.tanh(h1_sum + _W["b_h1"])  # bias + activation stay exact (no s_* for tanh)
 
        execution_count["h2_mul_x1"] += 1
        h2_a = s_mul(_W["w_h2_x1"], x1, bits.get("h2_mul_x1", False))
        execution_count["h2_mul_x2"] += 1
        h2_b = s_mul(_W["w_h2_x2"], x2, bits.get("h2_mul_x2", False))
        execution_count["h2_add"] += 1
        h2_sum = s_add(h2_a, h2_b, bits.get("h2_add", False))
        h2 = math.tanh(h2_sum + _W["b_h2"])
 
        execution_count["out_mul_h1"] += 1
        out_a = s_mul(_W["w_out_h1"], h1, bits.get("out_mul_h1", False))
        execution_count["out_mul_h2"] += 1
        out_b = s_mul(_W["w_out_h2"], h2, bits.get("out_mul_h2", False))
        execution_count["out_add"] += 1
        out_sum = s_add(out_a, out_b, bits.get("out_add", False))
        out = out_sum + _W["b_out"]
 
        execution_count["accum_add"] += 1
        accum = s_add(accum, out, bits.get("accum_add", False))
 
        history.append(out)
 
    execution_count["final_div"] += 1
    final_value = s_div(accum, float(len(inputs)), bits.get("final_div", False))
 
    return ExecutionResult(
        final_value=final_value,
        history=history,
        execution_count=execution_count,
    )

nn_inference.ops = (
    "h1_mul_x1", "h1_mul_x2", "h1_add",
    "h2_mul_x1", "h2_mul_x2", "h2_add",
    "out_mul_h1", "out_mul_h2", "out_add",
    "accum_add", "final_div",
)