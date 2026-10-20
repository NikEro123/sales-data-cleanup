
import random
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

SEED = 7
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)

# (product, category, sku, min_price, max_price, popularity weight)
CATALOG = [
    ('Dell XPS 13 Laptop', 'Laptops', 'LAP-DX13', 999, 1399, 4),
    ('MacBook Air M3 13"', 'Laptops', 'LAP-MBA3', 1099, 1299, 5),
    ('Lenovo ThinkPad E14', 'Laptops', 'LAP-TPE14', 749, 949, 4),
    ('HP Pavilion 15', 'Laptops', 'LAP-HPP15', 599, 799, 5),
    ('ASUS ROG Strix G16', 'Laptops', 'LAP-ROG16', 1399, 1799, 2),
    ('Dell 27" 4K Monitor', 'Monitors', 'MON-D274K', 329, 449, 5),
    ('LG UltraGear 27" 165Hz', 'Monitors', 'MON-LG27', 249, 329, 6),
    ('Samsung 32" Curved Monitor', 'Monitors', 'MON-SM32', 279, 379, 4),
    ('Logitech MX Master 3S', 'Accessories', 'ACC-MXM3', 89, 99, 12),
    ('Logitech MX Keys', 'Accessories', 'ACC-MXK', 99, 119, 9),
    ('Razer DeathAdder V3', 'Accessories', 'ACC-RDA3', 59, 89, 8),
    ('Anker USB-C Hub 7-in-1', 'Accessories', 'ACC-ANK7', 34, 49, 14),
    ('Keychron K2 Keyboard', 'Accessories', 'ACC-KK2', 79, 99, 7),
    ('Sony WH-1000XM5', 'Audio', 'AUD-SXM5', 329, 399, 6),
    ('AirPods Pro 2', 'Audio', 'AUD-APP2', 199, 249, 10),
    ('JBL Flip 6 Speaker', 'Audio', 'AUD-JBF6', 99, 129, 8),
    ('Logitech C920 Webcam', 'Accessories', 'ACC-C920', 59, 79, 9),
    ('Samsung T7 SSD 1TB', 'Storage', 'STO-T71T', 89, 119, 10),
    ('WD 4TB External HDD', 'Storage', 'STO-WD4T', 99, 129, 6),
    ('iPad 10th Gen 64GB', 'Tablets', 'TAB-IPD10', 329, 449, 5),
    ('Samsung Galaxy Tab S9', 'Tablets', 'TAB-GTS9', 699, 849, 3),
    ('TP-Link Deco Mesh WiFi', 'Networking', 'NET-DECO', 149, 249, 5),
]
PRODUCT_WEIGHTS = [p[5] for p in CATALOG]

STATES = {  # city -> state, weighted toward big cities
    "New York": "NY", "Los Angeles": "CA", "Chicago": "IL", "Houston": "TX",
    "Phoenix": "AZ", "Philadelphia": "PA", "San Antonio": "TX", "San Diego": "CA",
    "Dallas": "TX", "Austin": "TX", "Seattle": "WA", "Denver": "CO", "Boston": "MA",
    "Miami": "FL", "Atlanta": "GA", "Portland": "OR", "Nashville": "TN", "Columbus": "OH",
}
CITY_WEIGHTS = [14, 11, 9, 7, 5, 5, 4, 5, 6, 5, 6, 4, 5, 5, 5, 3, 3, 3]
REPS = ["Mike Turner", "Jessica Lee", "Carlos Ramirez", "Emily Chen", "David Brooks"]
PAYMENTS = ["Credit Card", "Credit Card", "Credit Card", "PayPal", "Debit Card", "Apple Pay", "Invoice"]


def make_customers(n=900):
    customers = []
    for i in range(n):
        is_business = random.random() < 0.06  # 6% are companies buying in bulk
        city = random.choices(list(STATES), weights=CITY_WEIGHTS)[0]
        if is_business:
            name = fake.company()
            email = f"purchasing@{fake.domain_name()}"
        else:
            first, last = fake.first_name(), fake.last_name()
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{random.choice(['', str(random.randint(1, 99))])}@" \
                    f"{random.choice(['gmail.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com'])}"
   
   
        weight = min(np.random.pareto(2.2) + 0.3, 4.0)
        if is_business:
            weight = min(weight * 3, 10.0)
        customers.append(dict(id=f"C{1000 + i}", name=name, email=email, city=city,
                              state=STATES[city], business=is_business, weight=weight))
    return customers


def random_order_date():
    """2024 with holiday peak, Black Friday spike, quieter weekends."""
    while True:
        d = date(2024, 1, 1) + timedelta(days=random.randint(0, 365))
        w = 1.0
        if d.month in (11, 12):
            w = 1.8
        if date(2024, 11, 29) <= d <= date(2024, 12, 2):  # Black Friday -> Cyber Monday
            w = 4.0
        if d.month in (1, 2):
            w = 0.7
        if d.weekday() >= 5:
            w *= 0.75
        if random.random() < w / 4.0:
            return d


def build_clean(n_orders):
    customers = make_customers()
    cust_weights = [c["weight"] for c in customers]
    rows = []
    for i in range(n_orders):
        c = random.choices(customers, weights=cust_weights)[0]
        name, cat, sku, lo, hi, _ = random.choices(CATALOG, weights=PRODUCT_WEIGHTS)[0]
        unit = round(random.uniform(lo, hi) / 5) * 5 - 0.01  # prices like 1,099.99
        if c["business"]:
            qty = random.choice([2, 3, 5, 5, 10, 10, 12, 20, 25])
        else:
            qty = random.choices([1, 2, 3], weights=[80, 15, 5])[0]
            if cat == "Accessories":
                qty = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
        d = random_order_date()
        discount = 0.0
        if c["business"] and qty >= 10:
            discount = 0.10
        elif date(2024, 11, 29) <= d <= date(2024, 12, 2):
            discount = random.choice([0.15, 0.20, 0.25])
        elif random.random() < 0.12:
            discount = random.choice([0.05, 0.10])
        total = round(qty * unit * (1 - discount), 2)
        status = random.choices(["Completed", "Refunded", "Pending", "Cancelled"],
                                weights=[90, 4, 3, 3])[0]
        rows.append({
            "Order ID": f"SO-{24000 + i}",
            "Order Date": d,
            "Channel": "Online" if random.random() < 0.65 else "In-Store",
            "Customer ID": c["id"],
            "Customer Name": c["name"],
            "Email": c["email"],
            "City": c["city"],
            "State": c["state"],
            "Product": name,
            "Category": cat,
            "SKU": sku,
            "Qty": qty,
            "Unit Price": unit,
            "Discount": discount,
            "Total": total,
            "Payment Method": "Invoice" if c["business"] else random.choice(PAYMENTS[:-1]),
            "Status": status,
            "Sales Rep": random.choice(REPS),
        })
    df = pd.DataFrame(rows).sort_values("Order Date").reset_index(drop=True)
    df["Order ID"] = [f"SO-{24000 + i}" for i in range(len(df))]  # IDs in date order
    return df


def add_mess(df):
    """Realistic mess: mostly from the old in-store POS system and manual edits."""
    df = df.astype(object)
    n = len(df)
    store = df["Channel"] == "In-Store"


    df.loc[store, "Order Date"] = df.loc[store, "Order Date"].map(lambda d: d.strftime("%m/%d/%Y"))
    df.loc[~store, "Order Date"] = df.loc[~store, "Order Date"].map(lambda d: d.strftime("%Y-%m-%d"))

  
    for col in ["Unit Price", "Total"]:
        df.loc[store, col] = df.loc[store, col].map(lambda v: f"${v:,.2f}")

 
    df.loc[store, "Discount"] = df.loc[store, "Discount"].map(lambda v: f"{int(v * 100)}%" if v else "0%")

    def pick(frac, mask=None):
        pool = df.index[mask] if mask is not None else df.index
        return np.random.choice(pool, size=int(len(pool) * frac), replace=False)

  
    idx = pick(0.10, store)
    df.loc[idx, "Customer Name"] = df.loc[idx, "Customer Name"].map(
        lambda s: random.choice([s.upper(), s.lower(), f" {s}", f"{s}  ", s.replace(" ", "  ", 1)]))

  
    variants = {"New York": ["NYC", "new york", "New York "], "Los Angeles": ["LA", "los angeles"],
                "Chicago": ["chicago"], "Houston": ["HOUSTON"]}
    for i in pick(0.04):
        if df.at[i, "City"] in variants:
            df.at[i, "City"] = random.choice(variants[df.at[i, "City"]])

    df.loc[pick(0.06, store), "Email"] = np.nan         
    df.loc[pick(0.015), "Sales Rep"] = np.nan
    df.loc[pick(0.008), "Qty"] = np.nan
    for i in pick(0.006):
        df.at[i, "Total"] = random.choice(["", "#VALUE!", "N/A"])  
    df.loc[pick(0.004), "Unit Price"] = np.nan

    
    week = df[(df["Order ID"] >= "SO-27000") & (df["Order ID"] < "SO-27250")].copy()
    week.loc[week.sample(frac=0.3, random_state=SEED).index, "Customer Name"] = \
        week["Customer Name"].astype(str).str.upper()
    df = pd.concat([df, week])

  
    blanks = pd.DataFrame([{c: np.nan for c in df.columns}] * max(3, n // 400))
    df = pd.concat([df, blanks])
    df = df.sample(frac=1, random_state=SEED)  # export isn't in order
    df = df.sort_values("Order ID", na_position="last", key=lambda s: s.fillna("SO-99999"))


    total_row = {c: np.nan for c in df.columns}
    total_row["Order ID"] = "TOTAL"
    total_row["Total"] = "see sum"
    df = pd.concat([df, pd.DataFrame([total_row])])
    return df.reset_index(drop=True)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    clean = build_clean(n)
    messy = add_mess(clean)
    out = "sales_export_2024.xlsx"
    messy.to_excel(out, index=False, sheet_name="Export")
    print(f"Created {out}: {len(messy):,} rows, {messy.shape[1]} columns")
