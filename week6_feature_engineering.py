from pathlib import Path
import pandas as pd

# Locate the cleaned sold data relative to this script
BASE_DIR = Path(__file__).resolve().parent
input_file = BASE_DIR / "CRMLS_Sold_Residential_Cleaned.csv"
# Load the data
sold = pd.read_csv(input_file, low_memory=False)

# Check the dataset before creating metrics
print(f"Sold rows loaded: {len(sold):,}")
print("\nAvailable columns:")
print(sold.columns.tolist())

# Check the fields needed for Week 6
required_columns = [
    "ClosePrice",
    "OriginalListPrice",
    "ListPrice",
    "LivingArea",
    "LivingAreaUnits",
    "DaysOnMarket",
    "CloseDate",
    "ListingContractDate",
    "PurchaseContractDate",
    "PropertyType",
    "PropertySubType",
    "CountyOrParish",
    "Latitude",
    "Longitude",
]

print("\nWEEK 6 FIELD CHECK")

for column in required_columns:
    if column in sold.columns:
        print(f"{column}: FOUND — {sold[column].notna().sum():,} nonmissing")
    else:
        print(f"{column}: NOT FOUND")


# -------------------------
# WEEK 6: ENGINEER METRICS
# -------------------------

# Ensure prices, area, and days on market are numeric
for column in [
    "ClosePrice",
    "OriginalListPrice",
    "LivingArea",
    "DaysOnMarket",
]:
    sold[column] = pd.to_numeric(sold[column], errors="coerce")

# Convert date columns into dates
for column in [
    "CloseDate",
    "ListingContractDate",
    "PurchaseContractDate",
]:
    sold[column] = pd.to_datetime(sold[column], errors="coerce")

# Only use positive prices and areas in price calculations
close_price = sold["ClosePrice"].where(sold["ClosePrice"] > 0)
original_price = sold["OriginalListPrice"].where(
    sold["OriginalListPrice"] > 0
)
living_area = sold["LivingArea"].where(sold["LivingArea"] > 0)

# The handbook gives these two metrics the same formula
sold["PriceRatio"] = close_price / original_price
sold["CloseToOriginalListRatio"] = sold["PriceRatio"]

# Assumption: LivingArea is measured in square feet,
# following the handbook; no units column is available.
sold["PricePerSqFt"] = close_price / living_area

# Keep the original DaysOnMarket field unchanged.
# Use a separate valid version for summaries.
sold["DaysOnMarketValid"] = sold["DaysOnMarket"].where(
    sold["DaysOnMarket"] >= 0
)

# Time-series fields from the closing date
sold["Year"] = sold["CloseDate"].dt.year.astype("Int64")
sold["Month"] = sold["CloseDate"].dt.month.astype("Int64")
sold["YrMo"] = sold["CloseDate"].dt.strftime("%Y-%m")

# Calculate the two stages of the sales timeline
listing_to_contract = (
    sold["PurchaseContractDate"] - sold["ListingContractDate"]
).dt.days

contract_to_close = (
    sold["CloseDate"] - sold["PurchaseContractDate"]
).dt.days

# Negative durations are invalid; leave them blank
sold["ListingToContractDays"] = listing_to_contract.where(
    listing_to_contract >= 0
)
sold["ContractToCloseDays"] = contract_to_close.where(
    contract_to_close >= 0
)

# Preview the new metrics
metric_columns = [
    "ClosePrice",
    "OriginalListPrice",
    "LivingArea",
    "PriceRatio",
    "CloseToOriginalListRatio",
    "PricePerSqFt",
    "DaysOnMarket",
    "Year",
    "Month",
    "YrMo",
    "ListingToContractDays",
    "ContractToCloseDays",
]

print("\nWEEK 6 METRIC SAMPLE")
print(sold[metric_columns].head(10).round(3).to_string(index=False))

# -------------------------
# COUNTY SUMMARY
# -------------------------

# Use positive closing prices for summary statistics
sold["ClosePriceValid"] = close_price

county_summary = (
    sold.groupby("CountyOrParish", dropna=False)
    .agg(
        SalesCount=("ClosePrice", "size"),
        ValidPriceCount=("ClosePriceValid", "count"),
        MedianClosePrice=("ClosePriceValid", "median"),
        MedianPriceRatio=("PriceRatio", "median"),
        MedianPricePerSqFt=("PricePerSqFt", "median"),
        MedianDaysOnMarket=("DaysOnMarketValid", "median"),
        MedianListingToContractDays=("ListingToContractDays", "median"),
        MedianContractToCloseDays=("ContractToCloseDays", "median"),
    )
    .reset_index()
    .sort_values("SalesCount", ascending=False)
)

# Save Week 6 outputs in a separate folder beside week4_5_outputs
output_dir = BASE_DIR.parent / "week6_outputs"
output_dir.mkdir(parents=True, exist_ok=True)

county_summary.to_csv(
    output_dir / "week6_county_summary.csv",
    index=False
)

sold[metric_columns].head(20).to_csv(
    output_dir / "week6_metric_sample.csv",
    index=False
)

print("\nCOUNTY SUMMARY — TOP 10 BY SALES COUNT")
print(county_summary.head(10).round(3).to_string(index=False))

print(f"\nSaved summary and sample to: {output_dir}")

# -------------------------
# LOAD SCHOOL DISTRICTS
# -------------------------
import geopandas as gpd

district_zip = BASE_DIR / "DistrictAreas2425.zip"

districts = gpd.read_file(f"zip://{district_zip}")

print("\nSCHOOL DISTRICT DATA")
print(f"District records: {len(districts):,}")
print(f"Coordinate system: {districts.crs}")

print("\nDistrict column names:")
print(districts.columns.tolist())

print("\nSample district information:")
print(districts.drop(columns="geometry").head(5).to_string(index=False))

# -------------------------
# MATCH PROPERTIES TO SCHOOL DISTRICTS
# -------------------------

latitude = pd.to_numeric(sold["Latitude"], errors="coerce")
longitude = pd.to_numeric(sold["Longitude"], errors="coerce")

# Only create points for valid, nonzero coordinates
valid_coords = (
    latitude.between(-90, 90)
    & longitude.between(-180, 180)
    & latitude.ne(0)
    & longitude.ne(0)
)

# Longitude is x; latitude is y
property_points = gpd.GeoDataFrame(
    index=sold.index[valid_coords],
    geometry=gpd.points_from_xy(
        longitude[valid_coords],
        latitude[valid_coords],
    ),
    crs="EPSG:4326",
)

# Convert points to the boundary file's coordinate system
property_points = property_points.to_crs(districts.crs)

# Find the districts containing each property point
matches = gpd.sjoin(
    property_points,
    districts[["CDSCode", "DistrictNa", "DistrictTy", "geometry"]],
    how="left",
    predicate="within",
)

# Keep district names and types together when multiple districts match
matched = matches.dropna(subset=["DistrictNa"]).copy()
matched["DistrictLabel"] = (
    matched["DistrictNa"].astype(str)
    + " ("
    + matched["DistrictTy"].fillna("Unknown").astype(str)
    + ")"
)

district_names = matched.groupby(level=0)["DistrictLabel"].agg(
    lambda values: " | ".join(sorted(set(values)))
)

district_counts = matched.groupby(level=0)["CDSCode"].nunique()

# Map results back without duplicating property rows
sold["SchoolDistricts"] = sold.index.to_series().map(district_names)
sold["SchoolDistrictCount"] = (
    sold.index.to_series()
    .map(district_counts)
    .fillna(0)
    .astype(int)
)

sold["SchoolDistrictMatchStatus"] = "Missing or invalid coordinates"
sold.loc[valid_coords, "SchoolDistrictMatchStatus"] = "No district match"
sold.loc[
    sold["SchoolDistrictCount"] > 0,
    "SchoolDistrictMatchStatus",
] = "Matched"

print("\nSCHOOL DISTRICT MATCH RESULTS")
print(sold["SchoolDistrictMatchStatus"].value_counts())

print("\nMATCHED PROPERTY SAMPLE")
print(
    sold.loc[
        sold["SchoolDistrictCount"] > 0,
        ["Latitude", "Longitude", "SchoolDistricts"],
    ]
    .head(10)
    .to_string(index=False)
)

# Save the full dataset with metrics and school districts
sold.to_csv(
    output_dir / "CRMLS_Sold_Residential_Week6.csv",
    index=False,
)

# Save a small school-district sample
sold[
    [
        "Latitude",
        "Longitude",
        "SchoolDistricts",
        "SchoolDistrictCount",
        "SchoolDistrictMatchStatus",
    ]
].head(100).to_csv(
    output_dir / "week6_school_district_sample.csv",
    index=False,
)

print(f"\nFinal row count: {len(sold):,}")
print(f"Saved Week 6 dataset to: {output_dir}")
