from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


class Fig:
    _DEFAULT_COLORS = (
        "tab:blue",
        "tab:orange",
        "tab:green",
        "tab:red",
        "tab:purple",
        "tab:brown",
        "tab:pink",
        "tab:gray",
    )

    def __init__(self):
        self._fig, self._ax = plt.subplots(figsize=(8, 5))
        self._ax.set_xlabel("x")
        self._ax.set_ylabel("y")
        self._color_index = 0
        self._filename = "figure"

    @classmethod
    def new(cls) -> "Fig":
        return cls()

    def _next_color(self):
        color = self._DEFAULT_COLORS[
            self._color_index % len(self._DEFAULT_COLORS)
        ]
        self._color_index += 1
        return color

    def title(self, text: str):
        self._ax.set_title(text)
        if self._filename == "figure":
            self._filename = text
        return self

    def xlabel(self, text: str):
        self._ax.set_xlabel(text)
        return self

    def ylabel(self, text: str):
        self._ax.set_ylabel(text)
        return self

    def grid(self, enabled: bool = True, alpha: float = 0.3):
        self._ax.grid(enabled, alpha=alpha)
        return self

    def legend(self):
        self._ax.legend()
        return self

    def filename(self, filename: str):
        self._filename = filename
        return self

    def scatter(
        self,
        points,
        *,
        label: str | None = None,
        color: str | None = None,
        size: float = 30,
        **kwargs,
    ):
        xs = [x for x, _ in points]
        ys = [y for _, y in points]

        self._ax.scatter(
            xs,
            ys,
            label=label,
            color=color or self._next_color(),
            s=size,
            **kwargs,
        )
        return self

    def line(
        self,
        points,
        *,
        label: str | None = None,
        color: str | None = None,
        linewidth: float = 2,
        **kwargs,
    ):
        xs = [x for x, _ in points]
        ys = [y for _, y in points]

        self._ax.plot(
            xs,
            ys,
            label=label,
            color=color or self._next_color(),
            linewidth=linewidth,
            **kwargs,
        )
        return self

    def regression(
        self,
        a: float,
        b: float,
        xmin: float,
        xmax: float,
        *,
        label: str | None = None,
        color: str | None = None,
        **kwargs,
    ):
        self._ax.plot(
            [xmin, xmax],
            [a * xmin + b, a * xmax + b],
            label=label or f"y = {a:.4g}x + {b:.4g}",
            color=color or self._next_color(),
            **kwargs,
        )
        return self

    def finish(self):
        self._fig.tight_layout()

        output = Path(f"{self._filename}.png")
        self._fig.savefig(output, dpi=300)

        plt.close(self._fig)

        return output

def auto(
    result,
    title: str = "Result",
    xlabel: str = "x",
    ylabel: str = "y",
    filename: str | None = None,
):
    """
    Generates a figure from an ExecutionResult.

    Required metadata for graph_type == "line":
        metadata = {
            "graph_type": "line",
            "data_points": [(x1, y1), (x2, y2), ...],
            "a": <slope>,
            "b": <intercept>,
        }

    Parameters
    ----------
    result : ExecutionResult
    title : str
    xlabel : str
    ylabel : str
    filename : str | None
        Output filename without extension (defaults to title).

    Returns
    -------
    pathlib.Path
        Path to the generated PNG.
    """
    metadata = result.metadata or {}

    graph_type = metadata.get("graph_type")
    fig = Fig.new()
    
    fig.title(title).xlabel(xlabel).ylabel(ylabel)

    if graph_type == "line":
        try:
            points = metadata["data_points"]
            a = metadata["a"]
            b = metadata["b"]
            fig \
                .scatter(points, label="Data") \
                .regression(a, b, xmin=1, xmax=5)
        except KeyError as exc:
            raise ValueError(
                "Line graph metadata must contain "
                "'data_points', 'a', and 'b'."
            ) from exc

    elif graph_type == "scatter":
        try:
            expected = metadata["data_points"]
            actual = metadata["points"]
            fig \
                .scatter(expected, label="Exact") \
                .scatter(actual, label="Approximate")   
        except KeyError as exc:
            raise ValueError(
                "Scatter graph metadata must contain "
                "'data_points' and 'points'."
            ) from exc

    else:
        raise ValueError(
            f"Unsupported graph_type {graph_type!r}. "
            "Supported types are 'line' and 'scatter'."
        )

    if (filename is not None):
        fig.filename(filename)
    else:
        fig.filename(title)
    
    fig \
        .grid() \
        .legend() \
        .finish()

    return output