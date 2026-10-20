# Sales Data Cleanup

A Python script that takes a messy sales export from Excel and turns it into a clean,
organized report sorted by money.

**The data is generated, not real sales data.** I built a generator that copies a common
real-world problem: one year of orders from an electronics store, exported from two
different systems (online store + in-store till) and dumped into one Excel file.

## The problem

The raw file has 6,266 rows and looks like a typical merged export:

- Two date formats: `2024-01-05` (online) and `01/05/2024` (in-store)
- Prices stored as text: `"$1,234.56"` next to plain numbers like `1234.56`
- Discounts as `0.1` in one system and `"10%"` in the other
- Customer names in ALL CAPS, lowercase, or with double spaces
- Short city names: `NYC`, `LA`
- A week of orders exported twice (duplicates)
- Missing quantities, prices and broken totals (`#VALUE!`, `N/A`)
- Blank rows and a leftover `TOTAL` row at the bottom

## What the script does

1. Turns junk values (`N/A`, `#VALUE!`, `-`, empty text) into real missing values
2. Removes blank rows, the `TOTAL` row and duplicate orders (same Order ID)
3. Converts both date formats into one real date type
4. Converts text prices and percentage discounts into numbers
5. **Rebuilds missing numbers instead of deleting the row:**
   `Total = Qty x Unit Price x (1 - Discount)`, and the same formula backwards for a
   missing Qty or Unit Price
6. Fixes customer names and city names
7. Labels missing emails / sales reps as "Not provided" / "Unassigned" instead of guessing
8. Logs every fix with a row count, so you can see exactly what changed
9. Groups the clean data by money and saves a formatted Excel report

## Result

```
Rows in: 6,266  ->  clean orders: 6,000

Removed duplicate orders (same Order ID)            250
Text prices like '$1,234.56' converted to numbers  2100
Customer names fixed (caps / extra spaces)          245
City names standardized (NYC, LA, caps)             112
Missing/broken Total recalculated from Qty x Price   36
Missing Qty recalculated from Total / Price          48
Missing Unit Price recalculated from Total / Qty     24
```

The output workbook has 6 sheets:

| Sheet | What's in it |
|---|---|
| Orders by Total | Every clean order, biggest money first |
| Top Customers | Revenue per customer, ranked, with share and cumulative % |
| Monthly Revenue | Orders and revenue per month |
| By Product | Units and revenue per product |
| Summary | Total revenue, average and median order, best month |
| Data Quality | Every fix and how many rows it touched |

A few things the report shows: the top 20% of customers bring in about 78% of revenue,
and November-December is the strongest part of the year.

## Run it

```bash
pip install pandas numpy openpyxl faker
python generating_realistic_sales.py          # creates sales_export_2024.xlsx
python clean_and_sort.py sales_export_2024.xlsx
```

The clean report is saved as `sales_export_2024_clean.xlsx`.
