"""
Analyze the numerical behavior of the SGD linear regression algorithm.

If no command-line arguments are provided, an interactive wizard is launched.

Examples:
    python analyze.py
    python analyze.py sensitivity
    python analyze.py pareto --iterations 200
"""

from __future__ import annotations

import argparse
import sys

import questionary

from analyzing.scoring import (
    discover,
    register_strategy,
    single_op_sensitivity,
)
from analyzing.strategies import nsga2_strategy
from analyzing.utils import print_report, print_table
from algorithms.sgd import sgd_linear_regression
from importlib import import_module

ALGORITHMS = {
    "SGD Linear Regression": lambda: getattr(
        import_module("algorithms.sgd"),
        "sgd_linear_regression",
    ),
    "Neural Network Inference": lambda: getattr(
        import_module("algorithms.nn_inference"),
        "nn_inference",
    ),
    "Exponential Moving Average": lambda: getattr(
        import_module("algorithms.ema"),
        "exponential_moving_average",
    ),
    "Chudnovsky π Terms": lambda: getattr(
        import_module("algorithms.chudnovsky_pi_terms"),
        "chudnovsky_pi_terms",
    ),
    "Calculate π (libnz)": lambda: getattr(
        import_module("algorithms.calculate_pi_libnz"),
        "calculate_pi",
    ),
}


@register_strategy("nsga2")
def nsga2_strategy_wrapper(fn, iterations, op_names, **kwargs):
    return nsga2_strategy(fn, iterations, op_names, **kwargs)


def run_sensitivity(fn, iterations: int):
    results = single_op_sensitivity(fn, iterations)

    print_table(results, title=f"Sensitivity — {fn.__name__}")
    print_report(results, title=f"Sensitivity (full detail) — {fn.__name__}")



def run_pareto(fn, iterations: int, pop_size: int, generations: int):
    results = discover(
        fn,
        iterations,
        strategy="nsga2",
        pop_size=pop_size,
        generations=generations,
    )

    print_table(results, title=f"Pareto front — {fn.__name__}")
    print_report(results, title=f"Pareto front (full detail) — {fn.__name__}")


def interactive_mode():
    print("\nApproximate Computing Analyzer")
    print("Press Ctrl+C at any time to exit.\n")

    while True:
        algorithm_name = questionary.select(
            "Choose an algorithm:",
            choices=list(ALGORITHMS.keys()),
        ).unsafe_ask()

        fn = ALGORITHMS[algorithm_name]()

        analysis = questionary.select(
            "Choose an analysis:",
            choices=[
                "Sensitivity",
                "Pareto",
            ],
        ).unsafe_ask()
        iterations = int(
            questionary.text(
                "Iterations:",
                default="100",
                validate=lambda x: x.isdigit() and int(x) > 0,
            ).unsafe_ask()
        )
        if analysis == "Sensitivity":
            run_sensitivity(fn, iterations)
        else:
            pop_size = int(
                questionary.text(
                    "Population size:",
                    default="24",
                    validate=lambda x: x.isdigit() and int(x) > 0,
                ).unsafe_ask()
            )
            generations = int(
                questionary.text(
                    "Generations:",
                    default="20",
                    validate=lambda x: x.isdigit() and int(x) > 0,
                ).unsafe_ask()
            )
            run_pareto(fn, iterations, pop_size, generations)
        print()


def cli_mode():
    parser = argparse.ArgumentParser(
        description="Analyze SGD linear regression."
    )

    parser.add_argument(
        "analysis",
        choices=["sensitivity", "pareto"],
        help="Analysis to perform.",
    )

    parser.add_argument(
        "algorithm",
        choices=[
            "sgd",
            "nn",
            "ema",
            "chudnovsky",
            "libnz",
        ],
        help="Algorithm to analyze.",
    )


    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=100,
        help="Number of executions.",
    )

    parser.add_argument(
        "--pop-size",
        type=int,
        default=24,
        help="Population size (Pareto only).",
    )

    parser.add_argument(
        "--generations",
        type=int,
        default=20,
        help="Number of generations (Pareto only).",
    )

    args = parser.parse_args()
    CLI_ALGORITHMS = {
        "sgd": ALGORITHMS["SGD Linear Regression"],
        "nn": ALGORITHMS["Neural Network Inference"],
        "ema": ALGORITHMS["Exponential Moving Average"],
        "chudnovsky": ALGORITHMS["Chudnovsky π Terms"],
        "libnz": ALGORITHMS["Calculate π (libnz)"],
    }
    fn = CLI_ALGORITHMS[args.algorithm]()

    if args.analysis == "sensitivity":
        run_sensitivity(fn, args.iterations)
    else:
        run_pareto(
            fn,
            args.iterations,
            args.pop_size,
            args.generations,
        )


def main():
    try:
        if len(sys.argv) == 1:
            interactive_mode()
        else:
            cli_mode()
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()
