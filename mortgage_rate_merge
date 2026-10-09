import pandas as pd

url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"

mortgage = pd.read_csv(url, parse_dates=["observation_date"])
mortgage.columns = ["date", "rate_30yr_fixed"]

mortgage["rate_30yr_fixed"] = pd.to_numeric(
    mortgage["rate_30yr_fixed"], errors="coerce"
)

mortgage["year_month"] = mortgage["date"].dt.to_period("M")

mortgage_monthly = (
    mortgage.groupby("year_month", as_index=False)["rate_30yr_fixed"]
    .mean()
)

print("Monthly mortgage rates:")
print(mortgage_monthly.tail(6).to_string(index=False))
print(f"Months with rates: {len(mortgage_monthly):,}")

sold = pd.read_csv("CRMLS_Combined_Sold_Residential.csv", low_memory=False)
listings = pd.read_csv(
    "CRMLS_Combined_Listings_Residential.csv", low_memory=False
)

sold["year_month"] = (
    pd.to_datetime(sold["CloseDate"], errors="coerce")
    .dt.to_period("M")
)

listings["year_month"] = (
    pd.to_datetime(listings["ListingContractDate"], errors="coerce")
    .dt.to_period("M")
)

sold_with_rates = sold.merge(
    mortgage_monthly, on="year_month", how="left", validate="many_to_one"
)
listings_with_rates = listings.merge(
    mortgage_monthly, on="year_month", how="left", validate="many_to_one"
)

sold_unmatched = sold_with_rates["rate_30yr_fixed"].isna()
listings_unmatched = listings_with_rates["rate_30yr_fixed"].isna()

print("\nSold rows without a mortgage rate:", sold_unmatched.sum())
print("Listing rows without a mortgage rate:", listings_unmatched.sum())

print("\nUnmatched sold months:")
print(sold_with_rates.loc[sold_unmatched, "year_month"].value_counts(dropna=False).head(10))

print("\nUnmatched listing months:")
print(listings_with_rates.loc[listings_unmatched, "year_month"].value_counts(dropna=False).head(10))

if sold_unmatched.any() or listings_unmatched.any():
    print("\nReview unmatched dates before saving the enriched CSVs.")
else:
    sold_with_rates.to_csv("CRMLS_Sold_Residential_With_Rates.csv", index=False)
    listings_with_rates.to_csv(
        "CRMLS_Listings_Residential_With_Rates.csv", index=False
    )
    print("\nBoth enriched CSVs saved successfully.")
