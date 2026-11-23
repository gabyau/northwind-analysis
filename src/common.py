"""Shared paths, chart colors and style, and output helpers."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT / "data" / "clean"
TABLE_DIR = ROOT / "output" / "tables"
RESULT_DIR = ROOT / "output" / "results"

DATE_COLS = ["OrderDate", "RequiredDate", "ShippedDate"]

# Categorical slots in fixed order (validated palette, light mode).
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"

# Single-hue blue ramp, light to dark, for magnitude.
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf",
             "#184f95", "#0d366b"]


def load_lines():
    """Load the joined order-lines table with dates parsed.

    Args:
        None.

    Returns:
        pandas.DataFrame: One row per order line from
        ``data/clean/order_lines.csv``; ``DATE_COLS`` as datetimes.
    """
    return pd.read_csv(CLEAN_DIR / "order_lines.csv", parse_dates=DATE_COLS)


def style(fig, title, x_title, y_title, height=420):
    """Apply the shared chart style to a Plotly figure.

    Args:
        fig (plotly.graph_objects.Figure): Chart to style; changed in
            place.
        title (str): Chart title, shown top left.
        x_title (str | None): X-axis title; None for no title.
        y_title (str | None): Y-axis title; None for no title.
        height (int): Figure height in pixels.

    Returns:
        plotly.graph_objects.Figure: The same ``fig``, styled.
    """
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left",
               "y": 1, "yref": "container", "yanchor": "top",
               "pad": {"t": 12}, "font": {"size": 16, "color": INK}},
        font={"family": "system-ui, -apple-system, Segoe UI, sans-serif",
              "size": 13, "color": INK_2},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        height=height,
        margin={"l": 70, "r": 30, "t": 100, "b": 60},
        # Legend sits on its own row under the title, left-aligned.
        legend={"orientation": "h", "y": 1.01, "yanchor": "bottom",
                "x": 0, "xanchor": "left", "title": None},
        hoverlabel={"bgcolor": "white", "font_size": 13},
    )
    # Zero lines off: charts draw their own reference lines where needed.
    axis = {"gridcolor": GRID, "linecolor": AXIS, "zeroline": False,
            "tickfont": {"color": MUTED}, "title_font": {"color": INK_2}}
    fig.update_xaxes(title_text=x_title, **axis)
    fig.update_yaxes(title_text=y_title, **axis)
    return fig


def save_table(df, name):
    """Save a table as CSV in ``output/tables``.

    Args:
        df (pandas.DataFrame): Table to save; the index is not written.
        name (str): File name without extension.

    Returns:
        None. Writes ``output/tables/<name>.csv``, overwriting it.
    """
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLE_DIR / f"{name}.csv", index=False)


def save_results(results, name):
    """Save key numbers as JSON in ``output/results``.

    Args:
        results (dict): Numbers quoted on the webpage; values that JSON
            can't encode (e.g. numpy numbers) are written as floats.
        name (str): File name without extension, e.g. ``"q1"``.

    Returns:
        pathlib.Path: Path of the written JSON file.
    """
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULT_DIR / f"{name}.json"
    path.write_text(json.dumps(results, indent=2, default=float))
    return path
