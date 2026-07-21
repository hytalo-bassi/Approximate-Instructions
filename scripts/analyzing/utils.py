from __future__ import annotations

import math

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def format_bits(bits: dict[str, bool]) -> str:
    active = [op for op, enabled in bits.items() if enabled]
    return ", ".join(active) if active else "[green]none[/green]"


def print_report(results, title: str = "Results") -> None:
    console.rule(f"[bold cyan]{title}")

    for i, r in enumerate(results, 1):
        body = Text()

        body.append("Approximate operations: ", style="bold")
        body.append(f"{format_bits(r['bits'])}\n")

        body.append("Exact value:            ", style="bold")
        body.append(f"{r['exact_value']:.10g}\n")

        body.append("Approximate value:      ", style="bold")
        body.append(f"{r['approx_value']:.10g}\n")

        body.append("Absolute error:         ", style="bold red")
        body.append(f"{r['global_error']:.6g}\n")

        if not math.isnan(r["relative_error"]):
            body.append("Relative error:         ", style="bold yellow")
            body.append(f"{r['relative_error']:.4%}\n")

        body.append("Historical mean error:  ", style="bold")
        body.append(f"{r['historical_mean_error']:.6g}\n")

        body.append("Maximum error:          ", style="bold")
        body.append(f"{r['maximum_error']:.6g}")

        if "score" in r:
            body.append("\nScore:                  ", style="bold magenta")
            body.append(f"{r['score']:.6f}")

        console.print(
            Panel(
                body,
                title=f"Candidate {i}",
                border_style="cyan",
            )
        )


def print_table(results, error_key: str = "global_error", title: str = "Results") -> None:
    rows = sorted(results, key=lambda r: r[error_key])

    table = Table(title=title, header_style="bold cyan")

    table.add_column("Approximate Operations", style="green")
    table.add_column("Exact", justify="right")
    table.add_column("Approx.", justify="right")
    table.add_column("Abs. Error", justify="right", style="red")
    table.add_column("Rel. Error", justify="right", style="yellow")
    table.add_column("Mean Error", justify="right")
    table.add_column("Max Error", justify="right")

    if any("score" in r for r in rows):
        table.add_column("Score", justify="right", style="magenta")

    for r in rows:
        row = [
            format_bits(r["bits"]),
            f"{r['exact_value']:.6g}",
            f"{r['approx_value']:.6g}",
            f"{r['global_error']:.4g}",
            "—" if math.isnan(r["relative_error"]) else f"{r['relative_error']:.2%}",
            f"{r['historical_mean_error']:.4g}",
            f"{r['maximum_error']:.4g}",
        ]

        if "score" in r:
            row.append(f"{r['score']:.4f}")

        table.add_row(*row)

    console.print(table)