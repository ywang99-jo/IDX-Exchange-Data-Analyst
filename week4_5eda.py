from pathlib import Path
import pandas as pd

# Load the combined residential datasets from Week 1.
# Paths are relative to this script's folder.
folder = Path("/Users/apple/Desktop/IDX Exchange/csv")

sold = pd.read_csv(
    folder / "CRMLS_Combined_Sold_Residential.csv",
    low_memory=False
)

listings = pd.read_csv(
    folder / "CRMLS_Combined_Listings_Residential.csv",
    low_memory=False
)

# Inspect the available fields before choosing cleaning rules.
for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    print(f"\n--- {name} ---")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print("\nColumn names:")
    print(df.columns.tolist())

# Check columns with a ".1" suffix before deciding whether to remove them.
for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    print(f"\n--- {name}: DUPLICATE COLUMN CHECK ---")

    duplicate_columns = [
        col for col in df.columns if col.endswith(".1")
    ]

    if not duplicate_columns:
        print("No columns ending in .1")

    for duplicate in duplicate_columns:
        original = duplicate[:-2]

        if original in df.columns:
            # Treat two missing values as matching.
            matches = (
                df[original].eq(df[duplicate])
                | (df[original].isna() & df[duplicate].isna())
            )

            print(
                f"{original} vs {duplicate}: "
                f"{(~matches).sum():,} differing rows"
            )

# Remove only verified exact duplicate columns.
# They contain no additional information.
drop_columns = []

for duplicate in listings.columns:
    if duplicate.endswith(".1"):
        original = duplicate[:-2]

        if original in listings.columns:
            matches = (
                listings[original].eq(listings[duplicate])
                | (
                    listings[original].isna()
                    & listings[duplicate].isna()
                )
            )

            if matches.all():
                drop_columns.append(duplicate)

before_columns = len(listings.columns)
listings = listings.drop(columns=drop_columns)

print("\nRemoved exact duplicate columns:", drop_columns)
print(f"Listing columns: {before_columns} → {len(listings.columns)}")
print(f"Listing rows unchanged: {len(listings):,}")

# Inspect the two pairs that differ before deciding how to handle them.
for original in ["BuyerOfficeName", "UnparsedAddress"]:
    duplicate = original + ".1"

    matches = (
        listings[original].eq(listings[duplicate])
        | (
            listings[original].isna()
            & listings[duplicate].isna()
        )
    )

    print(f"\nDiffering values: {original}")
    print(
        listings.loc[
            ~matches,
            ["ListingKey", original, duplicate]
        ].to_string(index=False)
    )
# Preserve the office-name conflict for review.
# Keep the original "Compass" rather than replacing it with "Co".
listings["buyer_office_conflict_flag"] = (
    listings["BuyerOfficeName"].notna()
    & listings["BuyerOfficeName.1"].notna()
    & listings["BuyerOfficeName"].ne(listings["BuyerOfficeName.1"])
)

# Original address is populated where its duplicate is missing.
# Remove the two extra columns after documenting the differences.
listings = listings.drop(
    columns=["BuyerOfficeName.1", "UnparsedAddress.1"]
)

print("\nOffice-name conflicts:",
      listings["buyer_office_conflict_flag"].sum())
print("Listing columns after cleanup:", len(listings.columns))

# Convert required date fields.
# Unreadable dates become NaT (missing dates) and are counted.
date_columns = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate"
]

for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    print(f"\n--- {name}: DATE CONVERSION ---")

    for col in date_columns:
        raw = df[col].astype("string").str.strip()
        populated = raw.notna() & raw.ne("")

        converted = pd.to_datetime(
            raw, format="mixed", errors="coerce"
        )

        failed = populated & converted.isna()
        df[col + "_parse_error_flag"] = failed
        df[col] = converted

        print(
            f"{col}: {df[col].dtype}, "
            f"missing = {df[col].isna().sum():,}, "
            f"parse errors = {failed.sum():,}"
        )

# Flag date-order violations without deleting records.
# Same-day events are allowed.
# Missing dates cannot be assessed and remain unflagged;
# a separate flag identifies incomplete timelines.
for name, df in [("SOLD", sold), ("LISTINGS", listings)]:

    df["listing_after_close_flag"] = (
        df["ListingContractDate"] > df["CloseDate"]
    )

    df["purchase_after_close_flag"] = (
        df["PurchaseContractDate"] > df["CloseDate"]
    )

    # Negative listing-to-purchase timeline:
    # purchase occurred before the listing date.
    df["negative_timeline_flag"] = (
        df["PurchaseContractDate"] < df["ListingContractDate"]
    )

    df["incomplete_timeline_flag"] = df[
        ["ListingContractDate", "PurchaseContractDate", "CloseDate"]
    ].isna().any(axis=1)

    flag_columns = [
        "listing_after_close_flag",
        "purchase_after_close_flag",
        "negative_timeline_flag",
        "incomplete_timeline_flag"
    ]

    print(f"\n--- {name}: DATE CONSISTENCY ---")

    for col in flag_columns:
        print(f"{col}: {df[col].sum():,}")

    # Count each record once, even if it violates multiple rules.
    violation_columns = flag_columns[:3]
    print(
        "Rows with any date-order violation:",
        f"{df[violation_columns].any(axis=1).sum():,}"
    )

# Convert numeric fields; preserve missing values rather than fill with zero.
numeric_columns = [
    "OriginalListPrice",
    "ListPrice",
    "ClosePrice",
    "LivingArea",
    "DaysOnMarket",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "Latitude",
    "Longitude"
]

for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    print(f"\n--- {name}: NUMERIC CONVERSION ---")

    for col in numeric_columns:
        raw = df[col].astype("string").str.strip()
        populated = raw.notna() & raw.ne("")

        # Remove formatting characters from numeric text.
        cleaned = raw.str.replace(",", "", regex=False)
        cleaned = cleaned.str.replace("$", "", regex=False)

        converted = pd.to_numeric(cleaned, errors="coerce")
        failed = populated & converted.isna()

        df[col + "_numeric_parse_error_flag"] = failed
        df[col] = converted

        print(
            f"{col}: {df[col].dtype}, "
            f"missing = {df[col].isna().sum():,}, "
            f"parse errors = {failed.sum():,}"
        )

    # Flag invalid values without removing records.
    # Missing values are reported above, separately from invalid values.
    rules = {
        "invalid_close_price_flag": df["ClosePrice"] <= 0,
        "invalid_list_price_flag": df["ListPrice"] <= 0,
        "invalid_living_area_flag": df["LivingArea"] <= 0,
        "negative_dom_flag": df["DaysOnMarket"] < 0,
        "negative_bedrooms_flag": df["BedroomsTotal"] < 0,
        "negative_bathrooms_flag": df["BathroomsTotalInteger"] < 0
    }

    print(f"\n--- {name}: INVALID NUMERIC VALUES ---")

    for flag, condition in rules.items():
        df[flag] = condition.fillna(False).astype(bool)
        print(f"{flag}: {df[flag].sum():,}")

    df["any_invalid_numeric_flag"] = df[
        list(rules)
    ].any(axis=1)

    print(
        "Rows with any invalid numeric value:",
        f"{df['any_invalid_numeric_flag'].sum():,}"
    )

# Geographic checks: retain records and flag coordinate problems.
for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    lat = df["Latitude"]
    lon = df["Longitude"]

    df["missing_coordinates_flag"] = lat.isna() | lon.isna()

    df["zero_coordinates_flag"] = (
        (lat == 0) | (lon == 0)
    ).fillna(False).astype(bool)

    df["positive_longitude_flag"] = (
        lon > 0
    ).fillna(False).astype(bool)

    # Coordinates outside possible global ranges.
    df["implausible_coordinates_flag"] = (
        (lat.notna() & ~lat.between(-90, 90))
        | (lon.notna() & ~lon.between(-180, 180))
    ).fillna(False).astype(bool)

    # Approximate California bounding box.
    # Outside this box requires review; inside does not prove CA location.
    complete = lat.notna() & lon.notna()
    inside_box = (
        lat.between(32.5, 42.1)
        & lon.between(-124.5, -114.0)
    )

    df["outside_ca_bbox_flag"] = (
        complete & ~inside_box
    ).fillna(False).astype(bool)

    geo_flags = [
        "missing_coordinates_flag",
        "zero_coordinates_flag",
        "positive_longitude_flag",
        "implausible_coordinates_flag",
        "outside_ca_bbox_flag"
    ]

    df["any_coordinate_issue_flag"] = df[
        geo_flags
    ].any(axis=1)

    print(f"\n--- {name}: GEOGRAPHIC CHECKS ---")

    for col in geo_flags:
        print(f"{col}: {df[col].sum():,}")

    print(
        "Rows with any coordinate issue:",
        f"{df['any_coordinate_issue_flag'].sum():,}"
    )

    # Inspect a sample of populated coordinates needing review.
    review = (
        df["zero_coordinates_flag"]
        | df["positive_longitude_flag"]
        | df["implausible_coordinates_flag"]
        | df["outside_ca_bbox_flag"]
    )

    print("\nSample coordinates needing review:")
    print(
        df.loc[
            review,
            ["ListingKey", "StateOrProvince", "Latitude", "Longitude"]
        ].head(10).to_string(index=False)
    )

# Standardize text formatting and missing values.
# Drop completely empty columns because they provide no information.
# Retain partially populated columns for possible future analysis.
for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    print(f"\n--- {name}: MISSING-VALUE HANDLING ---")

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for col in text_columns:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace("", pd.NA)

    empty_columns = [
        col for col in df.columns
        if df[col].isna().all()
    ]

    df.drop(columns=empty_columns, inplace=True)

    print("Removed completely empty columns:", empty_columns)
    print(f"Rows retained: {len(df):,}")
    print(f"Columns remaining: {len(df.columns):,}")

    print("\nRemaining columns with the most missing values:")
    missing = df.isna().sum().sort_values(ascending=False)
    print(missing[missing > 0].head(15).to_string())

# Capture actual input counts for the final report.
input_counts = {
    "SOLD": (len(sold), len(sold.columns)),
    "LISTINGS": (len(listings), len(listings.columns))
}
# Export prepared datasets with flags retained.
# Invalid values are flagged, not corrected or deleted.
# Analysts should exclude relevant flagged rows for each analysis.
output_folder = folder / "week4_5_outputs"
output_folder.mkdir(exist_ok=True)

summary = [
    "WEEKS 4–5: DATA CLEANING SUMMARY",
    "",
    "Cleaning decisions:",
    "- Removed verified duplicate listing columns.",
    "- Kept original office/address values for the differing record.",
    "- Flagged the office-name conflict for review.",
    "- Converted required dates and main numeric fields.",
    "- Trimmed text and converted blank text to missing values.",
    "- Removed completely empty columns.",
    "- Preserved missing values; no zero or mean imputation.",
    "- Retained rows and flagged numeric/date/coordinate issues.",
    "- California bounding box is a screening rule, not an exact boundary.",
    "- Positive longitude requires review for California analysis.",
    "- Extreme positive prices/areas still require outlier review.",
    "- CSV stores dates as text; parse date fields when reloading.",
    ""
]

for name, df in [("SOLD", sold), ("LISTINGS", listings)]:
    before_rows, before_columns = input_counts[name]

    output_path = output_folder / (
        f"CRMLS_{name.title()}_Residential_Cleaned.csv"
    )

    print(f"\nSaving {name}...")

    df.to_csv(output_path, index=False)

    flag_columns = [
        col for col in df.columns if col.endswith("_flag")
    ]

    summary.extend([
        f"--- {name} ---",
        f"Rows before: {before_rows:,}",
        f"Rows after: {len(df):,}",
        f"Rows removed: {before_rows - len(df):,}",
        f"Columns before: {before_columns:,}",
        f"Columns after (including flags): {len(df.columns):,}",
        "",
        "Date and numeric data types:"
    ])

    for col in date_columns + numeric_columns:
        if col in df.columns:
            summary.append(f"{col}: {df[col].dtype}")

    summary.append("\nQuality flag counts:")
    for col in flag_columns:
        summary.append(f"{col}: {int(df[col].sum()):,}")

    summary.append("\nMissing values in retained columns:")
    missing = df.isna().sum()
    for col, count in missing[missing > 0].items():
        summary.append(f"{col}: {count:,}")

    summary.append("")

    print(f"Saved: {output_path}")
    print(f"Rows: {before_rows:,} → {len(df):,}")

summary_path = output_folder / "week4_5_cleaning_summary.txt"
summary_path.write_text("\n".join(summary), encoding="utf-8")

print(f"\nSaved summary: {summary_path}")
print("Export complete.")
