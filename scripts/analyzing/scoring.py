from dataclasses import dataclass
from typing import Any
from statistics import mean
import itertools
import random


@dataclass
class ExecutionResult:
    final_value: float
    history: list
    execution_count: dict
    metadata: dict[str, Any] | None = None


def evaluate_candidate(fn, iterations, bits):
    op_names = fn.ops
    exact = fn(iterations, {op: False for op in op_names})
    approx = fn(iterations, bits)
 
    global_error = abs(exact.final_value - approx.final_value)
    relative_error = (
        global_error / abs(exact.final_value) if exact.final_value != 0 else float("nan")
    )
 
    errors = [abs(e - a) for e, a in zip(exact.history, approx.history)]
    historical_mean_error = mean(errors)
    maximum_error = max(errors)
 
    return {
        "bits": bits,
        "exact_value": exact.final_value,
        "approx_value": approx.final_value,
        "global_error": global_error,
        "relative_error": relative_error,
        "historical_mean_error": historical_mean_error,
        "maximum_error": maximum_error,
        "execution_count": approx.execution_count,
    }


def single_op_sensitivity(fn, iterations):
    """
    Isolate each op by name: flip ONE op on at a time from the all-exact baseline.
    Tells you which single op contributes the most error on its own.
    Not a "discovery" strategy (it doesn't search for a candidate) — kept as a
    standalone diagnostic, same as before.
    """
    op_names = fn.ops
    results = []
    for op in op_names:
        bits = {name: False for name in op_names}
        bits[op] = True
        result = evaluate_candidate(fn, iterations, bits)
        result["op_name"] = op
        results.append(result)
    return sorted(results, key=lambda r: r["global_error"])


# -------------------------------
# Scoring (unchanged, used by sweep/random; NSGA-II uses objectives_fn instead)
# -------------------------------

def score_candidate(result, error_weight=1.0, approx_weight=1.0, error_key="global_error"):
    """
    Lower score = better tradeoff.
    - error_weight: penalty per unit of error
    - approx_weight: reward per approx op used
    Swap error_key to "historical_mean_error" or "maximum_error" to change what "error" means.
    """
    approx_count = sum(result["bits"].values())
    return error_weight * result[error_key] - approx_weight * approx_count


def rank_candidates(results, error_weight=1.0, approx_weight=1.0, error_key="global_error"):
    """Sort candidates best-first by score_candidate."""
    scored = [
        {**r, "score": score_candidate(r, error_weight, approx_weight, error_key)}
        for r in results
    ]
    return sorted(scored, key=lambda r: r["score"])


# -------------------------------
# Strategy registry
# -------------------------------
# Every strategy has the signature:
#   strategy(fn, iterations, op_names, **kwargs) -> list[dict]  (results from evaluate_candidate)
#
# To add a custom discovery algorithm, just write a function with that
# signature and decorate it — nothing else in this file needs to change:
#
#   @register_strategy("hillclimb")
#   def hillclimb(fn, iterations, op_names, **kwargs):
#       ...
#       return [evaluate_candidate(fn, iterations, bits), ...]

STRATEGIES = {}


def register_strategy(name):
    def decorator(func):
        STRATEGIES[name] = func
        return func
    return decorator


def discover(fn, iterations, strategy="sweep", op_names=None, **kwargs):
    """Single entry point: discover(fn, iterations, strategy="nsga2", pop_size=30, generations=25)"""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{strategy}'. Available: {list(STRATEGIES)}")
    op_names = op_names or fn.ops
    return STRATEGIES[strategy](fn, iterations, op_names, **kwargs)
