import pandas as pd
import glob

listing_files = sorted(glob.glob("CRMLSListing*.csv"))

print("Listing files found:")

listing_dfs = []

for file in listing_files:
    df = pd.read_csv(file, low_memory=False)
    print(f"{file}: {len(df):,} rows")
    listing_dfs.append(df)

# Combine all monthly listing files into one dataset
listings = pd.concat(listing_dfs, ignore_index=True)

print(f"\nTotal listing rows after concatenation: {len(listings):,}")

# Check row count before filtering
print(f"Rows before Residential filter: {len(listings):,}")

# Keep only Residential properties
listings_residential = listings[
    listings["PropertyType"] == "Residential"
].copy()

# Check row count after filtering
print(f"Rows after Residential filter: {len(listings_residential):,}")
# Save filtered combined listing dataset
listings_residential.to_csv(
    "CRMLS_Combined_Listings_Residential.csv",
    index=False
)

print("Saved CRMLS_Combined_Listings_Residential.csv")

# -------------------------
# SOLD DATA
# -------------------------

sold_files = sorted(glob.glob("CRMLSSold*.csv"))

print("\nSold files found:")

sold_dfs = []

for file in sold_files:
    df = pd.read_csv(file, low_memory=False)
    print(f"{file}: {len(df):,} rows")
    sold_dfs.append(df)

# Combine all monthly sold files into one dataset
sold = pd.concat(sold_dfs, ignore_index=True)

print(f"\nTotal sold rows after concatenation: {len(sold):,}")

# Check row count before filtering
print(f"Rows before Residential filter: {len(sold):,}")

# Keep only Residential properties
sold_residential = sold[
    sold["PropertyType"] == "Residential"
].copy()

# Check row count after filtering
print(f"Rows after Residential filter: {len(sold_residential):,}")

# Save filtered combined sold dataset
sold_residential.to_csv(
    "CRMLS_Combined_Sold_Residential.csv",
    index=False
)

print("Saved CRMLS_Combined_Sold_Residential.csv")
