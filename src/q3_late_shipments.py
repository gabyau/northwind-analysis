"""Q3: days to ship compared with the customer's deadline."""

import pandas as pd
import plotly.graph_objects as go

from common import (BLUE_RAMP, INK, SURFACE, load_lines,
                    save_results, save_table, style)

# Bucket edges at 14 and 28 days line up with the 14- and 28-day deadlines.
SHIP_BINS = [0, 14, 28, 999]
SHIP_LABELS = ["1–14 days", "15–28 days", "29+ days"]


def build_orders(lines):
    """Build one row per order with its deadline and shipping times.

    Args:
        lines (pandas.DataFrame): Order lines from ``load_lines``.

    Returns:
        pandas.DataFrame: Orders with ``DeadlineDays``, ``DaysToShip``,
        ``DaysOfMargin`` (days shipped before the deadline; negative if
        late), ``Late``, and the order's products joined by "; ".
        Unshipped orders have NaN shipping fields.
    """
    orders = lines.groupby("OrderID").agg(
        CustomerName=("CustomerName", "first"),
        EmployeeName=("EmployeeName", "first"),
        ShipperName=("ShipperName", "first"),
        OrderDate=("OrderDate", "first"),
        RequiredDate=("RequiredDate", "first"),
        ShippedDate=("ShippedDate", "first"),
        Products=("ProductName", lambda s: "; ".join(s)),
        NetValue=("NetRevenue", "sum"),
    ).reset_index()
    orders["DeadlineDays"] = (orders["RequiredDate"]
                              - orders["OrderDate"]).dt.days
    orders["DaysToShip"] = (orders["ShippedDate"]
                            - orders["OrderDate"]).dt.days
    # Positive: shipped before the deadline. Negative: days late.
    orders["DaysOfMargin"] = (orders["RequiredDate"]
                              - orders["ShippedDate"]).dt.days
    orders["Late"] = orders["DaysOfMargin"] < 0
    return orders


def ship_time_table(shipped):
    """Count orders by deadline and shipping-time bucket.

    Args:
        shipped (pandas.DataFrame): Shipped orders, from
            ``build_orders``.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: Order counts, and the
        same as shares of each deadline's orders; rows are deadlines in
        days, columns are ``SHIP_LABELS``.
    """
    s = shipped.assign(ShipTime=pd.cut(shipped["DaysToShip"], SHIP_BINS,
                                       labels=SHIP_LABELS))
    counts = pd.crosstab(s["DeadlineDays"], s["ShipTime"]).reindex(
        columns=SHIP_LABELS, fill_value=0)
    shares = counts.div(counts.sum(axis=1), axis=0)
    return counts, shares


def stacked_figure(shipped, counts, shares):
    """Draw shipping-time shares per deadline, marking each deadline.

    Args:
        shipped (pandas.DataFrame): Shipped orders, from
            ``build_orders``.
        counts (pandas.DataFrame): Order counts, from
            ``ship_time_table``.
        shares (pandas.DataFrame): Order shares, from
            ``ship_time_table``.

    Returns:
        plotly.graph_objects.Figure: 100% stacked bars, one per
        deadline.
    """
    windows = list(counts.index)
    late = shipped.groupby("DeadlineDays")["Late"].agg(["sum", "size"])
    rows = [f"{w}-day deadline<br>{late.loc[w, 'sum']} of "
            f"{late.loc[w, 'size']} late" for w in windows]
    colors = [BLUE_RAMP[i] for i in (1, 4, 6)]
    fig = go.Figure()
    for label, color in zip(SHIP_LABELS, colors):
        share = 100 * shares[label]
        dark = colors.index(color) >= 1
        fig.add_bar(
            y=rows, x=share, orientation="h", name=label,
            marker_color=color, marker_line={"color": SURFACE, "width": 2},
            text=[f"{v:.0f}%" if v >= 6 else "" for v in share],
            textposition="inside", insidetextanchor="middle", textangle=0,
            textfont={"color": "#ffffff" if dark else INK},
            customdata=counts[label].values,
            hovertemplate=(f"<b>%{{y}}</b><br>Shipped in {label}: "
                           "%{customdata} orders (%{x:.0f}%)"
                           "<extra></extra>"),
        )
    # Mark the deadline on each bar: everything to its right shipped late.
    for row, w in zip(rows, windows):
        on_time = 100 * (1 - late.loc[w, "sum"] / late.loc[w, "size"])
        fig.add_scatter(
            x=[on_time], y=[row], mode="markers", showlegend=False,
            marker={"symbol": "line-ns-open", "size": 44, "color": INK,
                    "line": {"width": 3}},
            hovertemplate=(f"Deadline (day {w}): {on_time:.1f}% of "
                           "orders shipped before it<extra></extra>"),
        )
    fig.add_scatter(x=[None], y=[None], mode="markers",
                    name="Deadline (right of it = late)",
                    marker={"symbol": "line-ns-open", "size": 16,
                            "color": INK, "line": {"width": 3}})
    fig.update_layout(barmode="stack")
    fig.update_xaxes(ticksuffix="%", range=[0, 100])
    fig.update_yaxes(autorange="reversed")
    fig = style(
        fig, "How long orders took to ship, by the deadline the customer "
        "gave", "Share of orders", None, height=460,
    )
    # Legend under the chart so its entries can wrap on narrow screens.
    fig.update_layout(margin={"l": 150, "t": 60, "b": 130},
                      legend={"y": -0.22, "yanchor": "top",
                              "traceorder": "normal"})
    return fig


def main():
    """Run Q3: save its tables and key numbers, and return its chart.

    Args:
        None.

    Returns:
        plotly.graph_objects.Figure: The Q3 chart for the webpage.
    """
    orders = build_orders(load_lines())
    shipped = orders.dropna(subset=["ShippedDate"])
    late = shipped[shipped["Late"]].sort_values("DaysOfMargin")
    data_end = orders["OrderDate"].max()
    unshipped = orders[orders["ShippedDate"].isna()].copy()
    unshipped["PastDeadline"] = unshipped["RequiredDate"] < data_end

    cols = ["OrderID", "CustomerName", "EmployeeName", "ShipperName",
            "OrderDate", "RequiredDate", "ShippedDate", "DeadlineDays",
            "DaysToShip", "DaysOfMargin", "NetValue", "Products"]
    save_table(late[cols].round(2), "q3_late_orders")
    save_table(unshipped[cols[:6] + ["DeadlineDays", "PastDeadline",
                                     "NetValue", "Products"]].round(2),
               "q3_unshipped_orders")
    save_table(shipped[cols[:-1]].round(2), "q3_all_shipped_orders")
    counts, shares = ship_time_table(shipped)
    save_table(counts.reset_index(), "q3_ship_time_by_deadline")
    fig = stacked_figure(shipped, counts, shares)

    results = {
        "shipped_orders": int(len(shipped)),
        "late_orders": int(len(late)),
        "late_rate": float(len(late) / len(shipped)),
        "median_days_late": float(-late["DaysOfMargin"].median()),
        "max_days_late": int(-late["DaysOfMargin"].min()),
        "late_by_one_day": int((late["DaysOfMargin"] == -1).sum()),
        "late_counts_by_deadline": shipped.groupby("DeadlineDays")[
            "Late"].sum().astype(int).to_dict(),
        "orders_by_deadline": shipped.groupby("DeadlineDays")[
            "Late"].size().to_dict(),
        "late_value": float(late["NetValue"].sum()),
        "median_margin_on_time": float(
            shipped.loc[~shipped["Late"], "DaysOfMargin"].median()),
        "shipped_on_deadline_day": int((shipped["DaysOfMargin"] == 0)
                                       .sum()),
        "median_days_to_ship_by_deadline": shipped.groupby("DeadlineDays")[
            "DaysToShip"].median().to_dict(),
        "late_rate_by_deadline": shipped.groupby("DeadlineDays")[
            "Late"].mean().to_dict(),
        "unshipped_orders": int(len(unshipped)),
        "unshipped_past_deadline": int(unshipped["PastDeadline"].sum()),
        "data_end_date": str(data_end.date()),
    }
    save_results(results, "q3")
    print(results)
    print(late[["OrderID", "CustomerName", "EmployeeName", "ShipperName",
                "DeadlineDays", "DaysToShip", "DaysOfMargin"]]
          .to_string(index=False))
    return fig


if __name__ == "__main__":
    main()
