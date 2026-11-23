"""Q2: units per order with and without a discount, same customers."""

import pandas as pd
import plotly.graph_objects as go

from common import (BLUE, INK, ORANGE, SURFACE, load_lines,
                    save_results, save_table, style)

# Effective discount on the whole order (discount $ / pre-discount $).
DEPTH_BINS = [0, 0.075, 0.125, 0.20, 1]
DEPTH_LABELS = ["About 5%", "About 10%", "15–20%", "About 25%"]


def order_units(lines):
    """Summarize each order's units and effective discount.

    Args:
        lines (pandas.DataFrame): Order lines from ``load_lines``.

    Returns:
        pandas.DataFrame: One row per order with ``Units``,
        ``Discounted`` (any line discounted), ``DiscountRate``
        (discount $ / pre-discount $), and ``Depth`` (discount-size
        group; NaN for full-price orders).
    """
    orders = lines.groupby(["OrderID", "CustomerID", "CustomerName"]).agg(
        Units=("Quantity", "sum"),
        GrossValue=("GrossRevenue", "sum"),
        DiscountAmount=("DiscountAmount", "sum"),
    ).reset_index()
    # An order counts as discounted if any of its lines had a discount.
    orders["Discounted"] = orders["DiscountAmount"] > 0
    orders["DiscountRate"] = orders["DiscountAmount"] / orders["GrossValue"]
    orders["Depth"] = pd.cut(orders["DiscountRate"], DEPTH_BINS,
                             labels=DEPTH_LABELS)
    return orders


def same_customer_by_depth(orders):
    """Compare customers' discounted and full-price orders.

    Only customers with both kinds of order are kept, so each is
    compared with themselves.

    Args:
        orders (pandas.DataFrame): Orders from ``order_units``.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]:
        - Per customer and discount size: average units on discounted
          orders, usual full-price units, and ``BuysMore``.
        - Per discount size: averages across those customers, ``Lift``
          (fractional change in units), and ``BreakEvenUnits`` (units
          needed to bring in the usual money at that discount).
    """
    # Each discounted order's customer is compared with their own average
    # full-price order, so only customers with both kinds are kept.
    full_price = orders[~orders["Discounted"]].groupby("CustomerID")[
        "Units"].mean()
    d = orders[orders["Discounted"]].copy()
    d["FullPriceUnits"] = d["CustomerID"].map(full_price)
    d = d.dropna(subset=["FullPriceUnits"])

    per_customer = d.groupby(["Depth", "CustomerID", "CustomerName"],
                             observed=True).agg(
        DiscountedUnits=("Units", "mean"),
        FullPriceUnits=("FullPriceUnits", "first"),
        DiscountRate=("DiscountRate", "mean"),
        DiscountedOrders=("OrderID", "size"),
    ).reset_index()
    per_customer["BuysMore"] = (per_customer["DiscountedUnits"]
                                > per_customer["FullPriceUnits"])

    tiers = per_customer.groupby("Depth", observed=True).agg(
        Customers=("CustomerID", "size"),
        FullPriceUnits=("FullPriceUnits", "mean"),
        DiscountedUnits=("DiscountedUnits", "mean"),
        AvgDiscount=("DiscountRate", "mean"),
        CustomersBuyingMore=("BuysMore", "sum"),
    ).reset_index()
    tiers["Lift"] = tiers["DiscountedUnits"] / tiers["FullPriceUnits"] - 1
    # Units needed at this discount to bring in the same money as usual.
    tiers["BreakEvenUnits"] = (tiers["FullPriceUnits"]
                               / (1 - tiers["AvgDiscount"]))
    return per_customer, tiers


def bar_figure(tiers):
    """Draw usual vs. discounted units by discount size.

    Args:
        tiers (pandas.DataFrame): Per-discount-size table from
            ``same_customer_by_depth``.

    Returns:
        plotly.graph_objects.Figure: Grouped bars with a break-even mark
        over each discounted bar.
    """
    x = [f"{t}<br>({n} customers)" for t, n in
         zip(tiers["Depth"], tiers["Customers"])]
    fig = go.Figure()
    for group, (col, name, color) in enumerate([
        ("FullPriceUnits", "Their usual full-price order", BLUE),
        ("DiscountedUnits", "Their discounted orders", ORANGE),
    ]):
        fig.add_bar(
            x=x, y=tiers[col], name=name, marker_color=color,
            offsetgroup=str(group),
            marker_line={"color": SURFACE, "width": 2},
            # Labels inside the bars, clear of the break-even marks above.
            text=[f"{v:.0f}" for v in tiers[col]], textposition="inside",
            insidetextanchor="end", textangle=0,
            textfont={"color": "#ffffff", "size": 13},
            customdata=tiers[["CustomersBuyingMore", "Customers"]].values,
            hovertemplate=(f"<b>%{{x}}</b><br>{name}: %{{y:.1f}} units"
                           "<br>%{customdata[0]} of %{customdata[1]} "
                           "customers bought more when discounted"
                           "<extra></extra>"),
        )
    # Break-even marker sits over the discounted (right-hand) bar.
    fig.add_scatter(
        x=x, y=tiers["BreakEvenUnits"], mode="markers",
        name="Units needed to make up for the discount",
        marker={"symbol": "line-ew-open", "size": 30, "color": INK,
                "line": {"width": 3}},
        offsetgroup="1",
        customdata=(100 * tiers["AvgDiscount"]).values,
        hovertemplate=("Break-even: %{y:.0f} units<br>(usual order ÷ "
                       "(1 − %{customdata:.0f}% discount))<extra></extra>"),
    )
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08,
                      scattermode="group")
    top = max(tiers["BreakEvenUnits"].max(), tiers["DiscountedUnits"].max())
    fig.update_yaxes(range=[0, top * 1.15])
    fig.update_xaxes(showgrid=False)
    return style(
        fig, "Same customers, with and without a discount",
        "Size of the discount", "Average units per order", height=480,
    )


def main():
    """Run Q2: save its tables and key numbers, and return its chart.

    Args:
        None.

    Returns:
        plotly.graph_objects.Figure: The Q2 chart for the webpage.
    """
    orders = order_units(load_lines())
    per_customer, tiers = same_customer_by_depth(orders)

    save_table(per_customer.round(3), "q2_customer_units_by_discount")
    save_table(tiers.round(4), "q2_units_by_discount")
    fig = bar_figure(tiers)

    results = {
        "orders": int(len(orders)),
        "orders_discounted": int(orders["Discounted"].sum()),
        "customers_compared": int(per_customer["CustomerID"].nunique()),
        "discount_given_total": float(orders["DiscountAmount"].sum()),
        "by_depth": tiers.set_index("Depth")[
            ["Customers", "FullPriceUnits", "DiscountedUnits", "Lift",
             "BreakEvenUnits", "AvgDiscount", "CustomersBuyingMore"]
        ].to_dict(orient="index"),
    }
    save_results(results, "q2")
    print(tiers.round(3).to_string(index=False))
    return fig


if __name__ == "__main__":
    main()
