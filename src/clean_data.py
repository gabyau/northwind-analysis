from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "northwind.xlsx"
CLEAN_DIR = ROOT / "data" / "clean"

# Workbook tab name -> output file name.
TABLES = {
    "Categories": "categories",
    "Customers": "customers",
    "Employees": "employees",
    "Orders": "orders",
    "Orders Details": "order_details",
    "Product": "products",
    "Shippers": "shippers",
    "Suppliers": "suppliers",
}

# Columns added to the Product tab for a class exercise; not Northwind data.
PRODUCT_EXTRA_COLS = ["Cheap", "Cheap.1", "NewPrice", "NewPrice.1", "IsCheap"]


def load_raw(path):
    sheets = pd.read_excel(path, sheet_name=None)
    tables = {}
    for tab, name in TABLES.items():
        df = sheets[tab]
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
        tables[name] = df
    return tables


def clean_tables(tables):
    t = {name: df.copy() for name, df in tables.items()}

    t["categories"] = t["categories"].drop(columns=["Picture"])
    t["employees"] = t["employees"].drop(columns=["Photo"])
    t["employees"]["ReportsTo"] = t["employees"]["ReportsTo"].astype("Int64")
    for col in ["BirthDate", "HireDate"]:
        t["employees"][col] = pd.to_datetime(t["employees"][col])

    orders = t["orders"]
    for col in ["OrderDate", "RequiredDate", "ShippedDate"]:
        orders[col] = pd.to_datetime(orders[col])

    details = t["order_details"]
    # Discounts are stored as float32 noise (e.g. 0.150000006).
    details["Discount"] = details["Discount"].round(2)

    products = t["products"].drop(columns=PRODUCT_EXTRA_COLS)
    products = products.rename(columns={"Price": "ListPrice"})
    products["Discontinued"] = products["Discontinued"].astype(bool)
    t["products"] = products.sort_values("ProductID").reset_index(drop=True)

    return t


def check_integrity(t):
    def assert_fk(child, col, parent, key):
        missing = set(t[child][col].dropna()) - set(t[parent][key])
        assert not missing, f"{child}.{col} not in {parent}: {missing}"

    for name, key in [
        ("categories", "CategoryID"), ("customers", "CustomerID"),
        ("employees", "EmployeeID"), ("orders", "OrderID"),
        ("products", "ProductID"), ("shippers", "ShipperID"),
        ("suppliers", "SupplierID"),
    ]:
        assert t[name][key].is_unique, f"duplicate {key} in {name}"
    assert not t["order_details"].duplicated(["OrderID", "ProductID"]).any()

    assert_fk("order_details", "OrderID", "orders", "OrderID")
    assert_fk("order_details", "ProductID", "products", "ProductID")
    assert_fk("orders", "CustomerID", "customers", "CustomerID")
    assert_fk("orders", "EmployeeID", "employees", "EmployeeID")
    assert_fk("orders", "ShipVia", "shippers", "ShipperID")
    assert_fk("products", "SupplierID", "suppliers", "SupplierID")
    assert_fk("products", "CategoryID", "categories", "CategoryID")
    assert_fk("employees", "ReportsTo", "employees", "EmployeeID")

    d = t["order_details"]
    assert (d["Quantity"] > 0).all() and (d["UnitPrice"] > 0).all()
    assert d["Discount"].between(0, 1).all()


def build_order_lines(t):
    employees = t["employees"].assign(
        EmployeeName=lambda e: e["FirstName"] + " " + e["LastName"]
    )
    lines = (
        t["order_details"]
        .merge(t["orders"], on="OrderID", how="left")
        .merge(
            t["customers"][["CustomerID", "CompanyName", "Country"]]
            .rename(columns={"CompanyName": "CustomerName",
                             "Country": "CustomerCountry"}),
            on="CustomerID", how="left",
        )
        .merge(
            employees[["EmployeeID", "EmployeeName", "Country"]]
            .rename(columns={"Country": "EmployeeCountry"}),
            on="EmployeeID", how="left",
        )
        .merge(
            t["products"][["ProductID", "ProductName", "CategoryID",
                           "SupplierID", "ListPrice", "Discontinued"]],
            on="ProductID", how="left",
        )
        .merge(t["categories"][["CategoryID", "CategoryName"]],
               on="CategoryID", how="left")
        .merge(
            t["suppliers"][["SupplierID", "CompanyName", "Country"]]
            .rename(columns={"CompanyName": "SupplierName",
                             "Country": "SupplierCountry"}),
            on="SupplierID", how="left",
        )
        .merge(
            t["shippers"][["ShipperID", "CompanyName"]]
            .rename(columns={"ShipperID": "ShipVia",
                             "CompanyName": "ShipperName"}),
            on="ShipVia", how="left",
        )
    )
    assert len(lines) == len(t["order_details"]), "join changed row count"

    lines["GrossRevenue"] = lines["UnitPrice"] * lines["Quantity"]
    lines["NetRevenue"] = lines["GrossRevenue"] * (1 - lines["Discount"])
    lines["DiscountAmount"] = lines["GrossRevenue"] - lines["NetRevenue"]
    lines["OrderMonth"] = lines["OrderDate"].dt.to_period("M").astype(str)
    lines["DaysToShip"] = (lines["ShippedDate"] - lines["OrderDate"]).dt.days
    lines["ShippedLate"] = lines["ShippedDate"] > lines["RequiredDate"]
    return lines


def main():
    tables = clean_tables(load_raw(RAW_PATH))
    check_integrity(tables)
    lines = build_order_lines(tables)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(CLEAN_DIR / f"{name}.csv", index=False)
    lines.to_csv(CLEAN_DIR / "order_lines.csv", index=False)

    print("Integrity checks passed.")
    for name, df in {**tables, "order_lines": lines}.items():
        print(f"  {name:<14}{len(df):>6} rows")
    print(f"Net revenue: ${lines['NetRevenue'].sum():,.2f}")
    print(f"Order dates: {lines['OrderDate'].min():%Y-%m-%d} to "
          f"{lines['OrderDate'].max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
