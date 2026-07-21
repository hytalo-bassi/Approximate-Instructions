from analyzing.custom_approx_ops import *
from analyzing.scoring import ExecutionResult


def calculate_pi(iterations, bits):
    """
    bits: dict keyed by op name, e.g. {"div": False, "add_pi": True, "add_denom": False}
    Missing keys default to False (exact) via bits.get(...).
    """
    pi_estimate = 0.0
    denominator = 1.0
    sign = 1.0

    history = []
    execution_count = {op: 0 for op in calculate_pi.ops}

    for _ in range(iterations):

        execution_count["div"] += 1
        term = s_div(4.0, denominator, bits.get("div", False))

        execution_count["add_pi"] += 1
        pi_estimate = s_add(pi_estimate, sign * term, bits.get("add_pi", False))

        execution_count["add_denom"] += 1
        denominator = s_add(denominator, 2.0, bits.get("add_denom", False))

        sign *= -1
        history.append(pi_estimate)

    return ExecutionResult(
        final_value=pi_estimate,
        history=history,
        execution_count=execution_count,
    )

calculate_pi.ops = ("div", "add_pi", "add_denom")
