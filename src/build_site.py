"""Build the webpage (docs/index.html) from the three analyses."""

import json
from html import escape

from plotly.offline import get_plotlyjs_version

import q1_rep_discounts
import q2_discount_effect
import q3_late_shipments
from common import RESULT_DIR, ROOT, load_lines

SITE_DIR = ROOT / "docs"
# Set to the public GitHub repository URL once it exists.
REPO_URL = "https://github.com/gabyau/northwind-analysis"
DATA_URL = ("https://docs.google.com/spreadsheets/d/"
            "1mD4Hn4NZdJlXMC4EJcSp27vg-_jbxUYJ95vQvMbSpVM/edit?usp=sharing")
CHART_CONFIG = {"displayModeBar": False, "responsive": True}


def load_results():
    """Load the key numbers each analysis saved.

    Args:
        None.

    Returns:
        dict[str, dict]: Results keyed ``"q1"``, ``"q2"``, ``"q3"``.
    """
    return {q: json.loads((RESULT_DIR / f"{q}.json").read_text())
            for q in ["q1", "q2", "q3"]}


def chart(fig):
    """Render a chart as an HTML fragment that fills its container.

    Args:
        fig (plotly.graph_objects.Figure): Chart; its layout is changed
            in place to autosize.

    Returns:
        str: HTML ``<div>`` for the chart; plotly.js is loaded
        separately by the page.
    """
    fig.update_layout(width=None, autosize=True)
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config=CHART_CONFIG, default_width="100%")


def money(v):
    """Format an amount as whole dollars.

    Args:
        v (float): Amount in dollars.

    Returns:
        str: E.g. ``"$5,680"``.
    """
    return f"${v:,.0f}"


def signed_money(v):
    """Format an amount as whole dollars with a + or − sign.

    Args:
        v (float): Amount in dollars; zero gets "+".

    Returns:
        str: E.g. ``"+$5,680"`` or ``"−$751"`` (Unicode minus).
    """
    return f"{'+' if v >= 0 else '−'}${abs(v):,.0f}"


def pct(v, digits=0):
    """Format a fraction as a percentage.

    Args:
        v (float): Fraction, e.g. 0.176.
        digits (int): Decimal places to show.

    Returns:
        str: E.g. ``"18%"``.
    """
    return f"{100 * v:.{digits}f}%"


def overview():
    """Summarize the dataset for the page header.

    Args:
        None.

    Returns:
        dict: ``orders`` and ``customers`` (counts), ``net`` (sales
        after discounts, $), and ``start`` / ``end`` (first and last
        order dates, as pandas Timestamps).
    """
    lines = load_lines()
    return {
        "orders": lines["OrderID"].nunique(),
        "customers": lines["CustomerID"].nunique(),
        "net": lines["NetRevenue"].sum(),
        "start": lines["OrderDate"].min(),
        "end": lines["OrderDate"].max(),
    }


def section(num, title, why, approach, chart_html, finding, implication):
    """Lay out one question as an HTML section.

    Args:
        num (int): Question number; also sets the anchor ``#q<num>``.
        title (str): The question.
        why (str): HTML for "Why it matters".
        approach (str): HTML for "Approach".
        chart_html (str): HTML for the chart, from ``chart``.
        finding (str): HTML for "Main finding".
        implication (str): HTML for "Business implication".

    Returns:
        str: HTML ``<section>``.
    """
    return f"""
<section class="question" id="q{num}">
  <p class="eyebrow">Question {num}</p>
  <h2>{title}</h2>
  <div class="grid">
    <div><h3>Why it matters</h3>{why}</div>
    <div><h3>Approach</h3>{approach}</div>
  </div>
  <figure class="chart">{chart_html}</figure>
  <div class="grid">
    <div class="finding"><h3>Main finding</h3>{finding}</div>
    <div class="implication"><h3>Business implication</h3>{implication}</div>
  </div>
</section>"""


def q1_section(r, fig):
    """Write the Q1 section with numbers from its results.

    Args:
        r (dict): Q1 results from ``load_results``.
        fig (plotly.graph_objects.Figure): Q1 chart.

    Returns:
        str: HTML ``<section>`` for Q1.
    """
    extra = r["extra_discount_by_rep"]
    why = f"""<p>Northwind gave away {money(r['total_discount'])} in
    discounts, {pct(r['overall_discount_rate'], 1)} of sales before
    discount. Reps don't own territories: a typical customer is served by
    {r['median_reps_per_customer']:.0f} different reps, so the same customer
    can get a different price depending on who takes the order. If one rep
    discounts more than everyone else, that is a coaching or approval issue,
    not a market one.</p>"""
    approach = f"""<p>For the {r['customers_compared']} customers served by
    at least two reps who ever received a discount, each rep's discount rate
    with that customer is compared with the customer's overall rate. The gap
    is turned into dollars using the rep's sales to that customer, then
    added up per rep. Comparing reps on the <em>same customers</em> means a
    rep isn't penalized for simply having bigger or more price-sensitive
    accounts.</p>"""
    finding = f"""<p><strong>{escape(r['top_rep'])} gave
    {money(r['top_rep_extra_discount'])} more discount</strong> than
    the same customers usually get, almost three times the next rep
    ({escape(r['runner_up'])}, {signed_money(r['runner_up_extra_discount'])}).
    He discounted more than usual for {r['top_rep_customers_above']} of his
    {r['top_rep_customers']} customers. {r['reps_above_norm']} of 9 reps
    gave more than the norm; the rest gave less, down to
    {signed_money(min(extra.values()))}.</p>"""
    implication = f"""<p>Excess discounting is concentrated in one rep, not
    spread across the team. A targeted step, such as reviewing
    {escape(r['top_rep'].split()[0])}'s discounts and requiring manager
    approval above a set level, deals with most of it without changing
    policy for everyone. Question 2 shows why it matters: discounts of this
    size don't bring in enough extra sales to pay for themselves.</p>"""
    return section(
        1, "Are some reps giving away more discount than their customers "
        "would otherwise get?", why, approach,
        chart(fig), finding, implication)


def q2_section(r, fig):
    """Write the Q2 section with numbers from its results.

    Args:
        r (dict): Q2 results from ``load_results``.
        fig (plotly.graph_objects.Figure): Q2 chart.

    Returns:
        str: HTML ``<section>`` for Q2.
    """
    t = r["by_depth"]
    five, ten, mid, deep = (t["About 5%"], t["About 10%"], t["15–20%"],
                            t["About 25%"])
    why = f"""<p>{r['orders_discounted']} of {r['orders']} orders
    ({pct(r['orders_discounted'] / r['orders'])}) carried a discount. A
    discount only pays off if customers buy enough extra to make up for the
    lower price: at 10% off they need to buy about 11% more just to bring in
    the same money.</p>"""
    approach = f"""<p>Each customer is compared with themselves. For the
    {r['customers_compared']} customers with both full-price and discounted
    orders, their average units on discounted orders at each discount size
    are set against their usual full-price order. The black mark is the
    units needed to bring in the same money: usual units ÷ (1 − discount).
    Comparing all discounted orders with all full-price orders would
    mislead, because discounts tend to go to customers who already place
    large orders.</p>"""
    finding = f"""<p>Customers buy only slightly more when discounted:
    {pct(five['Lift'])} more units at about 5%, {pct(ten['Lift'])} at about
    10%, {pct(mid['Lift'], 1)} at 15–20%, and {pct(deep['Lift'])} at about
    25%. <strong>A 5% discount roughly breaks even</strong>
    ({five['DiscountedUnits']:.0f} units bought vs.
    {five['BreakEvenUnits']:.0f} needed). <strong>Deeper discounts fall
    short</strong>, and the gap grows with the discount: at 25% off,
    customers would need {deep['BreakEvenUnits']:.0f} units and bought
    {deep['DiscountedUnits']:.0f}.</p>"""
    implication = """<p>Keep routine discounts at about 5% or less, and
    require a reason, such as clearing stock or winning a new account, for
    anything deeper. Because discounts weren't handed out at random, a
    simple test would confirm this before changing policy: offer similar
    customers 5% or 10% at random for a quarter and compare what they
    buy.</p>"""
    return section(
        2, "Do customers buy more when they get a discount?", why, approach,
        chart(fig), finding, implication)


def q3_section(r, fig):
    """Write the Q3 section with numbers from its results.

    Args:
        r (dict): Q3 results from ``load_results``.
        fig (plotly.graph_objects.Figure): Q3 chart.

    Returns:
        str: HTML ``<section>`` for Q3.
    """
    late = r["late_counts_by_deadline"]
    n = r["orders_by_deadline"]
    days = r["median_days_to_ship_by_deadline"]
    why = """<p>Customers give a deadline with each order: 14, 28, or 42
    days. A late shipment puts the customer relationship at risk. Knowing
    <em>which</em> orders run late tells operations where to focus.</p>"""
    approach = f"""<p>For every shipped order ({r['shipped_orders']}), the
    number of days from order to shipment, grouped by the deadline the
    customer gave. The buckets (1–14, 15–28, 29+ days) line up with the
    deadlines, and the black line on each bar marks the deadline: anything
    to its right shipped late. "Late" means shipped after the required
    date; delivery dates aren't recorded.</p>"""
    finding = f"""<p>{r['late_orders']} of {r['shipped_orders']} orders
    ({pct(r['late_rate'], 1)}) shipped late, by a median of
    {r['median_days_late']:.0f} days. <strong>Orders take about a week to
    ship no matter how soon they're due</strong> (median
    {days['14']:g}, {days['28']:g}, and {days['42']:g} days). So the short
    deadline is where it breaks: <strong>{late['14']} of {n['14']}
    14-day orders were late ({pct(late['14'] / n['14'])})</strong>, against
    {late['28']} of {n['28']} for 28 days and {late['42']} of {n['42']}
    for 42 days.</p>"""
    implication = f"""<p>The warehouse doesn't prioritize rush orders.
    Flagging 14-day orders when they come in and moving them up the queue
    would address about a third of all late shipments ({late['14']} of
    {r['late_orders']}). The other {late['28']}, all with 28-day deadlines,
    took 29 days or more: a slow tail worth investigating order by order.</p>"""
    return section(
        3, "Are orders shipping before the customer's deadline?", why,
        approach, chart(fig), finding, implication)


def page(results, ov, figures):
    """Assemble the full webpage.

    Args:
        results (dict[str, dict]): Results from ``load_results``.
        ov (dict): Dataset summary from ``overview``.
        figures (dict[str, plotly.graph_objects.Figure]): Charts keyed
            ``"q1"``, ``"q2"``, ``"q3"``.

    Returns:
        str: Complete HTML document.
    """
    q1, q2, q3 = results["q1"], results["q2"], results["q3"]
    deep = q2["by_depth"]["About 25%"]
    late14 = q3["late_counts_by_deadline"]["14"] / \
        q3["orders_by_deadline"]["14"]
    repo = (f'<a href="{REPO_URL}">GitHub repository</a>' if REPO_URL
            else "GitHub repository (link to be added)")
    period = f"{ov['start']:%B %Y} to {ov['end']:%B %Y}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Northwind Discounts and Deadlines</title>
<meta name="description" content="Analysis of Northwind Traders orders:
rep discounting, whether discounts pay off, and late shipments.">
<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js"
  charset="utf-8"></script>
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e;
  --muted: #898781; --line: #e1e0d9; --accent: #2a78d6; --warm: #eb6834;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink);
  font: 17px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 960px; margin: 0 auto; padding: 0 16px 64px; }}
header {{ padding: 56px 0 24px; }}
h1 {{ font-size: clamp(28px, 5vw, 40px); line-height: 1.15; margin: 0 0 12px; }}
.lede {{ color: var(--ink-2); font-size: 19px; margin: 0; max-width: 68ch; }}
.meta {{ color: var(--muted); font-size: 14px; margin-top: 16px; }}
.takeaways {{ display: grid; gap: 12px; margin: 24px 0 8px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
.takeaway {{ background: var(--surface); border: 1px solid var(--line);
  border-radius: 10px; padding: 16px 18px; }}
.takeaway b {{ display: block; font-size: 24px; line-height: 1.2; }}
.takeaway span {{ color: var(--ink-2); font-size: 15px; }}
.question {{ border-top: 1px solid var(--line); margin-top: 48px;
  padding-top: 32px; }}
.eyebrow {{ color: var(--accent); font-weight: 600; font-size: 14px;
  letter-spacing: .04em; text-transform: uppercase; margin: 0; }}
h2 {{ font-size: clamp(22px, 3.5vw, 28px); line-height: 1.25;
  margin: 6px 0 20px; }}
h3 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .04em;
  color: var(--ink-2); margin: 0 0 6px; }}
p {{ margin: 0 0 12px; }}
.grid {{ display: grid; gap: 24px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
.chart {{ background: var(--surface); border: 1px solid var(--line);
  border-radius: 10px; margin: 24px 0; padding: 8px; overflow-x: auto; }}
.chart > div {{ min-width: 560px; }}
.finding, .implication {{ background: var(--surface);
  border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; }}
.finding {{ border-left: 4px solid var(--accent); }}
.implication {{ border-left: 4px solid var(--warm); }}
.methods {{ color: var(--ink-2); font-size: 15px; }}
.methods li {{ margin-bottom: 6px; }}
a {{ color: var(--accent); }}
footer {{ color: var(--muted); font-size: 14px; margin-top: 48px; }}
</style>
</head>
<body>
<main>
<header>
  <h1>Discounts and deadlines at Northwind Traders</h1>
  <p class="lede">Three questions for a manager about where Northwind is
  giving away money and where it is letting customers down: who discounts
  the most, whether discounts pay for themselves, and which orders ship
  late.</p>
  <p class="meta">{ov['orders']} orders from {ov['customers']} customers,
  {period} · ${ov['net'] / 1e6:.2f}M in sales after discounts</p>
  <div class="takeaways">
    <div class="takeaway"><b>{signed_money(q1['top_rep_extra_discount'])}</b>
      <span>extra discount from one rep, {escape(q1['top_rep'])}, beyond
      what the same customers usually get</span></div>
    <div class="takeaway"><b>{deep['DiscountedUnits']:.0f} vs.
      {deep['BreakEvenUnits']:.0f} units</b>
      <span>bought vs. needed to break even at 25% off; only ~5% discounts
      pay for themselves</span></div>
    <div class="takeaway"><b>{pct(late14)}</b>
      <span>of 14-day orders ship late, because every order takes about a
      week regardless of deadline</span></div>
  </div>
</header>
{q1_section(q1, figures['q1'])}
{q2_section(q2, figures['q2'])}
{q3_section(q3, figures['q3'])}
<section class="question methods" id="methods">
  <p class="eyebrow">Data and methods</p>
  <h2>How this was done</h2>
  <ul>
    <li><strong>Data:</strong> the <a href="{DATA_URL}">Northwind
    database</a> (8 tables: orders, order lines, customers, employees,
    products, categories, suppliers, shippers), {period}. Every key between
    tables was checked; no order line points to a missing order or
    product.</li>
    <li><strong>Revenue</strong> is unit price × quantity × (1 − discount)
    on each order line. There is no cost data, so results are about
    revenue, not profit.</li>
    <li><strong>Comparisons are within customer</strong> wherever possible
    (Questions 1 and 2), so results reflect what reps and discounts do, not
    which customers they happen to involve. Discounts were not assigned at
    random, so these are strong patterns rather than proof of cause.</li>
    <li><strong>Late</strong> means shipped after the required date;
    delivery dates aren't recorded. {q3['unshipped_orders']} orders hadn't
    shipped by the end of the data, and none were yet past their
    deadline.</li>
    <li>All numbers and charts on this page are generated by Python code
    that anyone can rerun from the raw data: {repo}.</li>
  </ul>
</section>
<footer>15.561 · HW3 · Charts are interactive: hover for details.</footer>
</main>
</body>
</html>
"""


def main(figures=None):
    """Build ``docs/index.html`` from the three analyses.

    Args:
        figures (dict[str, plotly.graph_objects.Figure] | None): Charts
            keyed ``"q1"``-``"q3"``; if None, reruns the three analyses
            to make them (which also rewrites their outputs).

    Returns:
        None. Writes ``docs/index.html`` and ``docs/.nojekyll``.
    """
    # run_all passes the charts in; run on its own, rerun the analyses.
    if figures is None:
        figures = {"q1": q1_rep_discounts.main(),
                   "q2": q2_discount_effect.main(),
                   "q3": q3_late_shipments.main()}
    SITE_DIR.mkdir(exist_ok=True)
    html = page(load_results(), overview(), figures)
    out = SITE_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    # Tell GitHub Pages to serve the files as-is, without Jekyll.
    (SITE_DIR / ".nojekyll").touch()
    print(f"Wrote {out.relative_to(ROOT)} ({len(html) / 1024:.0f} KB).")


if __name__ == "__main__":
    main()
