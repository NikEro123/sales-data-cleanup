
# Clean and sort orders from a messy export, then save to a formatted Excel file.

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

JUNK = {"", "-", "n/a", "na", "#n/a", "#value!", "null", "none", "nan", "?", "see sum"}
CITY_FIX = {"nyc": "New York", "la": "Los Angeles"}

log = []  # data-quality report, filled as we go


def note(msg, count):
    if count:
        log.append({"fix": msg, "rows": int(count)})




# ---------- parsing helpers ----------

def to_money(v):
    """'$1,234.56' / '1234.56' / junk -> float or NaN"""
    if pd.isna(v):
        return np.nan
    s = str(v).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def to_discount(v):
    """'10%' -> 0.10, '0.1' -> 0.10, missing -> 0"""
    if pd.isna(v):
        return 0.0
    s = str(v).strip()
    return float(s.rstrip("%")) / 100 if s.endswith("%") else float(s)


def fix_name(s):
    """Fix ALL CAPS / all lower names, keep 'McDonald' or 'Smith-Jones' as typed."""
    if pd.isna(s):
        return s
    s = " ".join(str(s).split())  # strip + collapse double spaces
    return s.title() if (s.isupper() or s.islower()) else s




# ---------- cleaning ----------

def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Junk text -> real NaN
    df = df.apply(lambda c: c.where(~c.astype(str).str.strip().str.lower().isin(JUNK), np.nan))

  
    before = len(df)
    df = df.dropna(how="all")
    note("Removed empty rows", before - len(df))
    is_total = df["order_id"].astype(str).str.upper().str.startswith("TOTAL")
    note("Removed manual TOTAL row", is_total.sum())
    df = df[~is_total]

   
    dupes = df["order_id"].duplicated()
    note("Removed duplicate orders (same Order ID)", dupes.sum())
    df = df[~dupes].copy()

    
    df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", errors="coerce")
    note("Dates converted to one format (2 formats found)", len(df))

    # Money and discount
    unit_raw, total_raw = df["unit_price"].astype(str), df["total"].astype(str)
    note("Text prices like '$1,234.56' converted to numbers", total_raw.str.contains(r"\$").sum())
    df["unit_price"] = df["unit_price"].map(to_money)
    df["total"] = df["total"].map(to_money)
    df["discount"] = df["discount"].map(to_discount)
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")





    # Rebuild missing numbers from the other columns: total = qty * price * (1 - discount)
    factor = 1 - df["discount"]
    m = df["total"].isna() & df["qty"].notna() & df["unit_price"].notna()
    df.loc[m, "total"] = (df.loc[m, "qty"] * df.loc[m, "unit_price"] * factor[m]).round(2)
    note("Missing/broken Total recalculated from Qty x Price", m.sum())


    m = df["qty"].isna() & df["total"].notna() & df["unit_price"].notna()
    df.loc[m, "qty"] = (df.loc[m, "total"] / (df.loc[m, "unit_price"] * factor[m])).round()
    note("Missing Qty recalculated from Total / Price", m.sum())


    m = df["unit_price"].isna() & df["total"].notna() & df["qty"].notna()
    df.loc[m, "unit_price"] = (df.loc[m, "total"] / (df.loc[m, "qty"] * factor[m])).round(2)
    note("Missing Unit Price recalculated from Total / Qty", m.sum())


    # Anything still unrecoverable is dropped (can't organize it by money)
    lost = df["total"].isna()
    note("Dropped: amount could not be recovered", lost.sum())
    df = df[~lost].copy()
    df["qty"] = df["qty"].astype(int)

    
    changed = df["customer_name"] != df["customer_name"].map(fix_name)
    note("Customer names fixed (caps / extra spaces)", changed.sum())
    df["customer_name"] = df["customer_name"].map(fix_name)

    city_clean = df["city"].str.strip()
    city_clean = city_clean.map(lambda c: CITY_FIX.get(c.lower(), c.title() if c.isupper() or c.islower() else c))
    note("City names standardized (NYC, LA, caps)", (city_clean != df["city"]).sum())
    df["city"] = city_clean

    note("Missing email marked 'Not provided'", df["email"].isna().sum())
    df["email"] = df["email"].fillna("Not provided")
    note("Missing sales rep marked 'Unassigned'", df["sales_rep"].isna().sum())
    df["sales_rep"] = df["sales_rep"].fillna("Unassigned")

    return df.sort_values("order_date").reset_index(drop=True)




# ---------- organizing by money ----------

def organize(df: pd.DataFrame) -> dict:
    sold = df[df["status"] == "Completed"]  # refunds/cancellations aren't revenue

    by_total = df.sort_values("total", ascending=False).reset_index(drop=True)
    by_total["size"] = np.select(
        [by_total["total"] >= 5000, by_total["total"] >= 1000, by_total["total"] >= 250],
        ["Large", "Medium", "Small"], default="Micro")

    customers = (sold.groupby(["customer_id", "customer_name", "city"])
                 .agg(orders=("order_id", "count"), revenue=("total", "sum"),
                      avg_order=("total", "mean"))
                 .sort_values("revenue", ascending=False).reset_index())
    customers["share_of_revenue_%"] = (customers["revenue"] / customers["revenue"].sum() * 100).round(2)
    customers["cumulative_%"] = customers["share_of_revenue_%"].cumsum().round(2)
    customers[["revenue", "avg_order"]] = customers[["revenue", "avg_order"]].round(2)

    monthly = (sold.groupby(sold["order_date"].dt.to_period("M"))
               .agg(orders=("order_id", "count"), revenue=("total", "sum")).reset_index())
    monthly["order_date"] = monthly["order_date"].astype(str)
    monthly = monthly.rename(columns={"order_date": "month"})
    monthly["revenue"] = monthly["revenue"].round(2)

    products = (sold.groupby(["product", "category"])
                .agg(units=("qty", "sum"), revenue=("total", "sum"))
                .sort_values("revenue", ascending=False).reset_index())
    products["revenue"] = products["revenue"].round(2)

    rev = sold["total"].to_numpy()
    top20_n = math.ceil(len(customers) * 0.20)
    top20_share = customers["share_of_revenue_%"].head(top20_n).sum()
    summary = pd.DataFrame({"metric": [
        "Completed orders", "Total revenue ($)", "Average order ($)", "Median order ($)",
        "Largest order ($)", "Refunded / cancelled orders", "Unique customers",
        "Revenue from top 20% of customers (%)", "Best month",
    ], "value": [
        len(sold), round(rev.sum(), 2), round(rev.mean(), 2), round(float(np.median(rev)), 2),
        round(rev.max(), 2), int((df["status"].isin(["Refunded", "Cancelled"])).sum()),
        customers["customer_id"].nunique(), round(top20_share, 1),
        monthly.loc[monthly["revenue"].idxmax(), "month"],
    ]})

    return {"Orders by Total": by_total, "Top Customers": customers, "Monthly Revenue": monthly,
            "By Product": products, "Summary": summary, "Data Quality": pd.DataFrame(log)}




# ---------- formatted Excel ----------

def save(sheets: dict, out: Path):
    from openpyxl.styles import Font, PatternFill
    with pd.ExcelWriter(out, engine="openpyxl", datetime_format="YYYY-MM-DD") as w:
        for name, data in sheets.items():
            data.to_excel(w, sheet_name=name, index=False)
            ws = w.sheets[name]
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            for col in ws.columns:
                header = str(col[0].value)
                width = max(len(str(c.value or "")) for c in col[:300]) + 2
                ws.column_dimensions[col[0].column_letter].width = min(max(width, 10), 45)
                if header in ("total", "unit_price", "revenue", "avg_order"):
                    for c in col[1:]:
                        c.number_format = '"$"#,##0.00'
                elif header == "discount":
                    for c in col[1:]:
                        c.number_format = "0%"
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions




def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python clean_and_sort.py <file.xlsx or .csv>")
    path = Path(sys.argv[1])
    raw = (pd.read_excel(path, dtype=str) if path.suffix.lower() in (".xlsx", ".xls")
           else pd.read_csv(path, dtype=str))

    df = clean(raw)
    sheets = organize(df)
    out = path.with_name(path.stem + "_clean.xlsx")
    save(sheets, out)

    print(f"Rows in: {len(raw):,}  ->  clean orders: {len(df):,}\n")
    print(sheets["Data Quality"].to_string(index=False), "\n")
    print(sheets["Summary"].to_string(index=False))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
