from analyzing.custom_approx_ops import *
from analyzing.scoring import ExecutionResult
import math

def _synthetic_series(n, seed=0):
    return [math.sin(i * 0.1) * 10 + (i % 7) for i in range(n)]


def exponential_moving_average(iterations, bits, alpha=0.2):
    """
    bits: dict keyed by op name (see .ops below), e.g.
          {"scale_new": True, "scale_old": False, "combine": False, "residual": False}
    """
    series = _synthetic_series(iterations)

    ema = series[0]
    history = [ema]
    execution_count = {op: 0 for op in exponential_moving_average.ops}

    for x in series[1:]:
        execution_count["scale_new"] += 1
        weighted_new = s_mul(alpha, x, bits.get("scale_new", False))

        execution_count["scale_old"] += 1
        weighted_old = s_mul(1 - alpha, ema, bits.get("scale_old", False))

        execution_count["combine"] += 1
        ema = s_add(weighted_new, weighted_old, bits.get("combine", False))

        # execution_count["residual"] += 1
        # _residual = s_sub(x, ema, bits.get("residual", False))  # not tracked because it's unused in output

        history.append(ema)

    return ExecutionResult(
        final_value=ema,
        history=history,
        execution_count=execution_count,
        metadata={
            "graph_type": "scatter",
            "data_points": [(i, v) for i, v in enumerate(_synthetic_series(iterations))],
            "points": [(i, v) for i, v in enumerate(history)]
        }
    )


exponential_moving_average.ops = ("scale_new", "scale_old", "combine", "residual")
