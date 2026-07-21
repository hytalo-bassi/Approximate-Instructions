"""
Analyze the numerical behavior of the SGD linear regression algorithm.

If no command-line arguments are provided, an interactive wizard is launched.

Examples:
    python analyze.py
    python analyze.py sensitivity sgd
    python analyze.py pareto sgd --iterations 200
    python analyze.py pareto sgd --strategy nsga2-corr
    python analyze.py pareto sgd --strategy random --n-samples 50
    python analyze.py pareto sgd --strategy sweep
"""

from __future__ import annotations

import argparse
import sys
from importlib import import_module

import questionary

from analyzing.scoring import (
    discover,
    register_strategy,
    single_op_sensitivity,
)
from analyzing.strategies import (
    nsga2_strategy,
    nsga2_corr_strategy,
    random_strategy,
    sweep_strategy,
)
from analyzing.utils import print_report, print_table

ALGORITHMS = {
    "SGD Linear Regression": {
        "module": "algorithms.sgd",
        "function": "sgd_linear_regression",
    },
    "Neural Network Inference": {
        "module": "algorithms.nn_inference",
        "function": "nn_inference",
    },
    "Exponential Moving Average": {
        "module": "algorithms.ema",
        "function": "exponential_moving_average",
    },
    "Chudnovsky π Terms": {
        "module": "algorithms.chudnovsky_pi_terms",
        "function": "chudnovsky_pi_terms",
    },
    "Calculate π (libnz)": {
        "module": "algorithms.calculate_pi_libnz",
        "function": "calculate_pi",
    },
}

CLI_ALGORITHMS = {
    "sgd": "SGD Linear Regression",
    "nn": "Neural Network Inference",
    "ema": "Exponential Moving Average",
    "chudnovsky": "Chudnovsky π Terms",
    "libnz": "Calculate π (libnz)",
}

# Every strategy registered here becomes selectable via --strategy on the CLI.
STRATEGY_CHOICES = ["sweep", "random", "nsga2", "nsga2-corr"]

register_strategy("sweep")(sweep_strategy)
register_strategy("random")(random_strategy)
register_strategy("nsga2")(nsga2_strategy)
register_strategy("nsga2-corr")(nsga2_corr_strategy)


def load_algorithm(name: str):
    """name is a key into ALGORITHMS, e.g. 'SGD Linear Regression'."""
    info = ALGORITHMS[name]
    fn = getattr(import_module(info["module"]), info["function"])
    return fn, info


def print_candidate_code(results, info, iterations, prefix="nsga2"):
    # "-" isn't valid in a Python identifier (e.g. nsga2-corr), so sanitize it
    # for use as a variable-name prefix in the printed code.
    var_prefix = prefix.replace("-", "_")

    print("\n=== Python Code ===\n")

    print(
        f"from {info['module']} import {info['function']}\n"
    )

    print(
        f"res_exact = {info['function']}({iterations}, {{}})"
    )

    for i, result in enumerate(results, start=1):
        enabled = {
            name: True
            for name, enabled in result["bits"].items()
            if enabled
        }

        print(
            f"res_{var_prefix}_{i} = "
            f"{info['function']}({iterations}, {enabled})"
        )


def run_sensitivity(fn, iterations: int):
    results = single_op_sensitivity(fn, iterations)

    print_table(results, title=f"Sensitivity — {fn.__name__}")
    print_report(results, title=f"Sensitivity (full detail) — {fn.__name__}")


def run_pareto(fn, info, iterations: int, strategy: str, strategy_kwargs: dict, show_code: bool = False):
    results = discover(
        fn,
        iterations,
        strategy=strategy,
        **strategy_kwargs,
    )

    print_table(results, title=f"{strategy} — {fn.__name__}")
    print_report(results, title=f"{strategy} (full detail) — {fn.__name__}")
    if show_code:
        print_candidate_code(results, info, iterations, prefix=strategy)


def interactive_mode():
    print("\nApproximate Computing Analyzer")
    print("Press Ctrl+C at any time to exit.\n")

    while True:
        algorithm_name = questionary.select(
            "Choose an algorithm:",
            choices=list(ALGORITHMS.keys()),
        ).unsafe_ask()

        fn, info = load_algorithm(algorithm_name)

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
            strategy = questionary.select(
                "Choose a strategy:",
                choices=STRATEGY_CHOICES,
                default="nsga2",
            ).unsafe_ask()

            show_code = questionary.confirm(
                "Show Python code?",
                default=False,
            ).unsafe_ask()

            if strategy in ("nsga2", "nsga2-corr"):
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
                strategy_kwargs = {"pop_size": pop_size, "generations": generations}
            elif strategy == "random":
                n_samples = int(
                    questionary.text(
                        "Number of samples:",
                        default="20",
                        validate=lambda x: x.isdigit() and int(x) > 0,
                    ).unsafe_ask()
                )
                strategy_kwargs = {"n_samples": n_samples}
            else:  # sweep
                strategy_kwargs = {}

            run_pareto(
                fn,
                info,
                iterations,
                strategy=strategy,
                strategy_kwargs=strategy_kwargs,
                show_code=show_code,
            )
        print()


def cli_mode():
    parser = argparse.ArgumentParser(
        description="Analyze approximate-computing candidates for an algorithm."
    )

    parser.add_argument(
        "analysis",
        choices=["sensitivity", "pareto"],
        help="Analysis to perform.",
    )

    parser.add_argument(
        "algorithm",
        choices=list(CLI_ALGORITHMS.keys()),
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
        "--strategy",
        choices=STRATEGY_CHOICES,
        default="nsga2",
        help="Candidate-discovery strategy to use (pareto analysis only). Default: nsga2.",
    )

    parser.add_argument(
        "--pop-size",
        type=int,
        default=24,
        help="Population size. Used by nsga2 / nsga2-corr only.",
    )

    parser.add_argument(
        "--generations",
        type=int,
        default=20,
        help="Number of generations. Used by nsga2 / nsga2-corr only.",
    )

    parser.add_argument(
        "--n-samples",
        type=int,
        default=20,
        help="Number of samples to draw. Used by random only.",
    )

    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Print Python code to reproduce each candidate (pareto only).",
    )

    args = parser.parse_args()

    fn, info = load_algorithm(CLI_ALGORITHMS[args.algorithm])

    if args.analysis == "sensitivity":
        run_sensitivity(fn, args.iterations)
    else:
        # Only pass the kwargs each strategy actually understands — the
        # rest are silently accepted-and-ignored via **kwargs in each
        # strategy function, but keeping this explicit avoids confusion
        # about which flags do anything for a given --strategy.
        if args.strategy in ("nsga2", "nsga2-corr"):
            strategy_kwargs = {"pop_size": args.pop_size, "generations": args.generations}
        elif args.strategy == "random":
            strategy_kwargs = {"n_samples": args.n_samples}
        else:  # sweep
            strategy_kwargs = {}

        run_pareto(
            fn,
            info,
            args.iterations,
            strategy=args.strategy,
            strategy_kwargs=strategy_kwargs,
            show_code=args.show_code,
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