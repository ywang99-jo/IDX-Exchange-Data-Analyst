# Filtering documented from the Week 1 aggregation script:
# Unfiltered sold records: 681,599
# Residential sold records retained: 458,336
# Filter: sold["PropertyType"] == "Residential"
#
# Other property types found:
# ResidentialLease 155,507; Land 22,601; ManufacturedInPark 18,604;
# ResidentialIncome 18,212; CommercialSale 4,267;
# CommercialLease 3,599; BusinessOpportunity 473.
#
# Missing-value decision:
# Flag columns over 90% missing for review. Do not automatically drop them
# from the filtered CSV. Review their purpose before cleaning.
#
# Outliers to investigate:
# ClosePrice reaches 989,500,000; LivingArea reaches 17,021,321;
# DaysOnMarket includes 63 negative values.
# Preserve original values until checked against source records.
import pandas as pd

sold = pd.read_csv(
    "CRMLS_Combined_Sold_Residential.csv",
    low_memory=False
)

print(f"Rows: {len(sold):,}")
print(f"Columns: {len(sold.columns)}")

print("\nKey fields:")
print(sold[["ClosePrice", "LivingArea", "DaysOnMarket"]].dtypes)

missing_report = pd.DataFrame({
    "missing_count": sold.isna().sum(),
    "missing_percent": sold.isna().mean() * 100
}).sort_values("missing_percent", ascending=False)

missing_report["over_90_percent_missing"] = (
    missing_report["missing_percent"] > 90
)

missing_report.to_csv("sold_missing_value_report.csv")

print("\nColumns over 90% missing:")
print(
    missing_report[missing_report["over_90_percent_missing"]]
    .round(1)
    .to_string()
)
print("\nSaved sold_missing_value_report.csv")

fields = ["ClosePrice", "LivingArea", "DaysOnMarket"]

numeric_summary = (
    sold[fields]
    .describe(percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
    .T
)

numeric_summary.to_csv("sold_numeric_summary.csv")

print("\nNumeric distribution summary:")
print(numeric_summary.round(2).to_string())
print("\nSaved sold_numeric_summary.csv")

print("\nPotential data-quality issues:")
print("ClosePrice missing:", sold["ClosePrice"].isna().sum())
print("ClosePrice zero or negative:", (sold["ClosePrice"] <= 0).sum())
print("LivingArea missing:", sold["LivingArea"].isna().sum())
print("LivingArea zero or negative:", (sold["LivingArea"] <= 0).sum())
print("DaysOnMarket negative:", (sold["DaysOnMarket"] < 0).sum())

print("\nFive highest ClosePrice records (selected fields):")
print(
    sold[["ClosePrice", "ListPrice", "LivingArea", "DaysOnMarket"]]
    .nlargest(5, "ClosePrice")
    .to_string(index=False)
)

valid_list_price = sold["ListPrice"] > 0
price_ratio = sold.loc[valid_list_price, "ClosePrice"] / sold.loc[
    valid_list_price, "ListPrice"
]

print("\nClosePrice compared with ListPrice:")
print("At least 10 times ListPrice:", (price_ratio >= 10).sum())
print("At most 10% of ListPrice:", (price_ratio <= 0.1).sum())

print("\nHighest ClosePrice/ListPrice ratios:")
print(
    price_ratio.nlargest(5).round(2).to_string()
)

from pathlib import Path
import matplotlib.pyplot as plt

chart_folder = Path("sold_eda_charts")
chart_folder.mkdir(exist_ok=True)

chart_fields = [
    "ClosePrice", "ListPrice", "OriginalListPrice",
    "LivingArea", "LotSizeAcres", "BedroomsTotal",
    "BathroomsTotalInteger", "DaysOnMarket", "YearBuilt"
]

for field in chart_fields:
    if field not in sold.columns:
        print(f"Skipping {field}: column not found")
        continue

    values = pd.to_numeric(sold[field], errors="coerce").dropna()
    if values.empty:
        print(f"Skipping {field}: no numeric values")
        continue

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(values, bins=50)
    axes[0].set_title(f"{field}: histogram")
    axes[1].boxplot(values)
    axes[1].set_title(f"{field}: boxplot")
    fig.tight_layout()

    fig.savefig(chart_folder / f"{field}.png", dpi=150)
    plt.close(fig)

print(f"\nCharts saved in: {chart_folder}")
print("Charts saved at:", chart_folder.resolve())
