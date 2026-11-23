# Northwind Business Analysis (15.561 HW3)

Analysis of the Northwind sample database, a fictional specialty-foods
wholesaler, with orders from July 1996 to May 1998.

- **Webpage:** _link to be added_
- **Data source:** [Northwind Database (Google Sheet)](https://docs.google.com/spreadsheets/d/1mD4Hn4NZdJlXMC4EJcSp27vg-_jbxUYJ95vQvMbSpVM/edit?usp=sharing)

## Reproduce the results

Requires Python 3.10 or newer. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/run_all.py
```

`run_all.py` runs every step in order. Each step can also be run on its own:

| Step | Script | Writes |
|---|---|---|
| 1 | `src/download_data.py` | `data/raw/northwind.xlsx` (skipped if present) |
| 2 | `src/clean_data.py` | `data/clean/*.csv`, after integrity checks |
| 3 | `src/q1_rep_discounts.py` | `output/tables/q1_*`, `output/results/q1.json` |
| 4 | `src/q2_discount_effect.py` | `output/tables/q2_*`, `output/results/q2.json` |
| 5 | `src/q3_late_shipments.py` | `output/tables/q3_*`, `output/results/q3.json` |
| 6 | `src/build_site.py` | `docs/index.html`: the webpage with all three charts |

Each analysis script saves its supporting tables (CSV) and the key numbers
quoted on the webpage (`output/results/`), and returns its chart.
`build_site.py` puts the three charts and those numbers into one page, so
everything on the webpage comes from the analysis code. Run on its own,
`build_site.py` reruns the three analyses first. Open `docs/index.html` in a
browser to view the page locally.

A snapshot of the workbook is committed at `data/raw/northwind.xlsx`, so the
results reproduce even if the Google Sheet changes. To fetch a fresh copy, run
`python src/download_data.py --force`.

`clean_data.py` should print `Integrity checks passed.` and a net revenue of
**$1,265,793.04** across 2,155 order lines.

## Repository layout

| Path | Contents |
|---|---|
| `src/download_data.py` | Downloads the Google Sheet as `data/raw/northwind.xlsx` |
| `src/clean_data.py` | Cleans each tab, checks keys, builds `order_lines.csv` |
| `src/common.py` | Shared loaders, chart style, and output helpers |
| `src/q1_rep_discounts.py` | Q1: extra discount $ each rep gave vs. the customer's norm |
| `src/q2_discount_effect.py` | Q2: same customers' units per order, by discount size |
| `src/q3_late_shipments.py` | Q3: days to ship vs. the customer's deadline |
| `src/build_site.py` | Builds the webpage from the three charts and key numbers |
| `src/run_all.py` | Runs every step above in order |
| `data/raw/` | Untouched workbook snapshot |
| `data/clean/` | One CSV per tab, plus `order_lines.csv` |
| `output/` | Supporting tables and the key numbers on the webpage |
| `docs/` | The webpage (served by GitHub Pages) |

## Methods

- **Q1, each rep vs. the customer's average.** For every customer served by
  at least two reps who ever received a discount, each rep's discount rate
  with that customer (`DiscountAmount / GrossRevenue` over their orders) is
  compared with the customer's overall rate. The rep's extra discount with
  that customer is `(rep's rate − customer's rate) × rep's pre-discount
  sales to that customer`, in dollars; the chart sums it per rep. Positive
  means the rep gave more than the same customers usually get, negative
  less. Customers who never got a discount are excluded, since every rep's
  gap with them is zero.
- **Q2, units per order with and without a discount.** An order is
  "discounted" if any of its lines has a discount; size is measured in
  units (sum of `Quantity`), which the discount itself doesn't change.
  Each customer is compared with themselves, which removes the effect of
  which customers tend to get discounts: for every customer with both kinds
  of orders (54), their average units on discounted orders at each discount
  size vs. their average full-price order. Discount size is the order's
  effective discount (discount $ / pre-discount $): about 5% (up to 7.5%),
  about 10% (7.5–12.5%), 15–20% (12.5–20%), about 25% (over 20%). The
  break-even mark is the units needed to bring in the same money as the
  usual order: usual units ÷ (1 − average discount in that group).
- **Q3, days to ship vs. the customer's deadline.** For every shipped order,
  days from order to shipment, grouped by the deadline the customer gave
  (`RequiredDate − OrderDate`: 14, 28, or 42 days), bucketed as 1–14,
  15–28, and 29+ days so bucket edges line up with the 14- and 28-day
  deadlines. An order is late if it shipped after `RequiredDate`; delivery
  dates are not recorded. Unshipped orders are checked against the last
  order date in the data (1998-05-06).

## Data model

`Orders Details` (one row per product on an order) links to `Orders` by
`OrderID` and to `Product` by `ProductID`. `Orders` links to `Customers`,
`Employees`, and `Shippers` (`ShipVia` = `ShipperID`). `Product` links to
`Suppliers` and `Categories`. `Employees.ReportsTo` points to another employee.

`data/clean/order_lines.csv` joins all of these into one row per order line,
with these derived columns:

| Column | Definition |
|---|---|
| `GrossRevenue` | `UnitPrice × Quantity` |
| `NetRevenue` | `GrossRevenue × (1 − Discount)` |
| `DiscountAmount` | `GrossRevenue − NetRevenue` |
| `OrderMonth` | Order date as `YYYY-MM` |
| `DaysToShip` | `ShippedDate − OrderDate` in days; blank if not shipped |
| `ShippedLate` | `ShippedDate` after `RequiredDate` |

## Cleaning decisions

- **Product:** dropped `Cheap`, `IsCheap`, and both `NewPrice` columns. They
  are not part of Northwind (`NewPrice` is always `Price × 1.07`, and `Cheap`
  contains a stray `"B"`). Renamed `Price` to `ListPrice`.
- **Discount:** rounded to 2 decimals (stored as values like `0.150000006`).
- **Revenue uses `UnitPrice` from the order, not `ListPrice`.** About 30% of
  lines were sold at an older price than today's catalog price.
- Dropped the empty `Picture` (Categories) and `Photo` (Employees) columns.

## Caveats

- **May 1998 is a partial month** (orders through May 6). Leave it out of
  monthly trend comparisons.
- **21 orders have no `ShippedDate`.** They are still open.
- **`Freight` is per order.** It repeats on each line in `order_lines.csv`, so
  take it from `orders.csv` instead of summing it there.
- `FISSA` and `PARIS` are customers with no orders.
- About 0.5% of orders ship to a different country than the customer's
  address.
