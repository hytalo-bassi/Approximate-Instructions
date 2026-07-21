from analyzing.custom_approx_ops import *
from analyzing.scoring import ExecutionResult
import math


def chudnovsky_pi_terms(terms, bits):
    """
    Computes an approximation of Pi using the Chudnovsky algorithm.
    Each additional term adds roughly 14 digits of precision.

    bits: dict keyed by op name (see chudnovsky_pi_terms.ops), e.g.
          {"term_div": True, "term_add": False, "final_mul": False, "final_div": False}
    """
    sigma_sum = 0.0
    history = []
    execution_count = {op: 0 for op in chudnovsky_pi_terms.ops}

    for k in range(terms):
        numerator = ((-1) ** k) * math.factorial(6 * k) * (545140134 * k + 13591409)

        denominator = math.factorial(3 * k) * (math.factorial(k) ** 3) * (640320 ** (3 * k))

        execution_count["term_div"] += 1
        term = s_div(numerator, denominator, bits.get("term_div", False))

        execution_count["term_add"] += 1
        sigma_sum = s_add(sigma_sum, term, bits.get("term_add", False))

        history.append(sigma_sum)

    execution_count["final_mul"] += 1
    constant = s_mul(426880, math.sqrt(10005), bits.get("final_mul", False))

    execution_count["final_div"] += 1
    pi_estimate = s_div(constant, sigma_sum, bits.get("final_div", False))

    return ExecutionResult(
        final_value=pi_estimate,
        history=history,
        execution_count=execution_count,
    )


chudnovsky_pi_terms.ops = ("term_div", "term_add", "final_mul", "final_div")
