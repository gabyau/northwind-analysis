"""Q1: discount each rep gave beyond the same customers' usual."""

import numpy as np
import plotly.graph_objects as go

from common import (BLUE, INK_2, MUTED, ORANGE, SURFACE, load_lines,
                    save_results, save_table, style)

MIN_REPS = 2


def customer_rep_gaps(lines):
    """Compare each rep's discount with each customer's usual discount.

    Keeps only customers served by at least ``MIN_REPS`` reps who
    received some discount.

    Args:
        lines (pandas.DataFrame): Order lines from ``load_lines``.

    Returns:
        pandas.DataFrame: One row per customer and rep, with the rep's
        ``DiscountRate``, the customer's ``CustomerAvgRate``, and
        ``ExtraDiscount``: the gap in dollars on the rep's pre-discount
        sales to that customer (positive = more than usual).
    """
    cr = lines.groupby(["CustomerID", "CustomerName", "EmployeeName"]).agg(
        Orders=("OrderID", "nunique"),
        GrossRevenue=("GrossRevenue", "sum"),
        DiscountAmount=("DiscountAmount", "sum"),
    ).reset_index()
    cr["DiscountRate"] = cr["DiscountAmount"] / cr["GrossRevenue"]

    cust = lines.groupby("CustomerID")[["DiscountAmount",
                                        "GrossRevenue"]].sum()
    cr["CustomerAvgRate"] = cr["CustomerID"].map(
        cust["DiscountAmount"] / cust["GrossRevenue"])
    cr["RepsForCustomer"] = cr.groupby("CustomerID")["EmployeeName"] \
        .transform("size")
    # Need another rep to compare against, and a customer who ever got a
    # discount (otherwise every rep's gap is trivially zero).
    keep = (cr["RepsForCustomer"] >= MIN_REPS) & (cr["CustomerAvgRate"] > 0)
    cr = cr[keep].copy()
    # Dollars of discount beyond (or short of) what this customer usually
    # gets, on the business this rep wrote for them.
    cr["ExtraDiscount"] = (cr["DiscountRate"] - cr["CustomerAvgRate"]) \
        * cr["GrossRevenue"]
    return cr


def rep_summary(cr):
    """Total each rep's extra discount across their customers.

    Args:
        cr (pandas.DataFrame): Customer-rep rows from
            ``customer_rep_gaps``.

    Returns:
        pandas.DataFrame: One row per rep, sorted by ``ExtraDiscount``
        ascending, with customer counts, ``CustomersAbove`` (customers
        given more than usual), and the rep's overall ``DiscountRate``.
    """
    reps = cr.groupby("EmployeeName").agg(
        Customers=("CustomerID", "nunique"),
        ExtraDiscount=("ExtraDiscount", "sum"),
        DiscountGiven=("DiscountAmount", "sum"),
        GrossRevenue=("GrossRevenue", "sum"),
        CustomersAbove=("ExtraDiscount", lambda s: int((s > 0).sum())),
    ).reset_index()
    reps["DiscountRate"] = reps["DiscountGiven"] / reps["GrossRevenue"]
    # Ascending, so the largest extra discount is drawn at the top.
    return reps.sort_values("ExtraDiscount").reset_index(drop=True)


def bar_figure(reps):
    """Draw each rep's extra discount as a horizontal bar chart.

    Args:
        reps (pandas.DataFrame): Rep summary from ``rep_summary``.

    Returns:
        plotly.graph_objects.Figure: Bars in dollars; orange above the
        customers' norm, blue below.
    """
    extra = reps["ExtraDiscount"]
    fig = go.Figure()
    fig.add_bar(
        y=reps["EmployeeName"], x=extra, orientation="h",
        marker_color=[ORANGE if v > 0 else BLUE for v in extra],
        marker_line={"color": SURFACE, "width": 2},
        text=[f"{'+' if v > 0 else '−'}${abs(v):,.0f}" for v in extra],
        textposition="outside", textfont={"color": INK_2, "size": 13},
        cliponaxis=False,
        customdata=np.stack([reps["CustomersAbove"], reps["Customers"],
                             100 * reps["DiscountRate"]], axis=1),
        hovertemplate=(
            "<b>%{y}</b><br>%{text} vs. what the same customers usually "
            "get<br>Gave more than usual to %{customdata[0]} of "
            "%{customdata[1]} customers<br>Overall discount rate: "
            "%{customdata[2]:.1f}%<extra></extra>"
        ),
        showlegend=False,
    )
    fig.add_vline(x=0, line_color=MUTED, line_width=1)
    span = extra.abs().max() * 1.35
    fig.update_xaxes(range=[-span, span], tickformat="$,.0f")
    fig.update_yaxes(showgrid=False)
    fig = style(
        fig, "Discount each rep gave beyond what the same customers "
        "usually get", "Extra discount (+) or less discount (−), in dollars",
        None, height=440,
    )
    fig.update_layout(margin={"l": 140, "t": 60})
    return fig


def main():
    """Run Q1: save its tables and key numbers, and return its chart.

    Args:
        None.

    Returns:
        plotly.graph_objects.Figure: The Q1 chart for the webpage.
    """
    lines = load_lines()
    cr = customer_rep_gaps(lines)
    reps = rep_summary(cr)
    reps_per_customer = lines.groupby("CustomerID")["EmployeeID"].nunique()

    save_table(cr.round(4), "q1_customer_rep_discounts")
    save_table(reps.round(4), "q1_rep_extra_discount")
    fig = bar_figure(reps)

    top, runner_up = reps.iloc[-1], reps.iloc[-2]
    results = {
        "median_reps_per_customer": float(reps_per_customer.median()),
        "total_discount": float(lines["DiscountAmount"].sum()),
        "overall_discount_rate": float(lines["DiscountAmount"].sum()
                                       / lines["GrossRevenue"].sum()),
        "customers_compared": int(cr["CustomerID"].nunique()),
        "top_rep": top["EmployeeName"],
        "top_rep_extra_discount": float(top["ExtraDiscount"]),
        "top_rep_customers_above": int(top["CustomersAbove"]),
        "top_rep_customers": int(top["Customers"]),
        "runner_up": runner_up["EmployeeName"],
        "runner_up_extra_discount": float(runner_up["ExtraDiscount"]),
        "reps_above_norm": int((reps["ExtraDiscount"] > 0).sum()),
        "extra_discount_by_rep": dict(zip(reps["EmployeeName"],
                                          reps["ExtraDiscount"])),
    }
    save_results(results, "q1")
    print(reps.round(1).to_string(index=False))
    return fig


if __name__ == "__main__":
    main()
