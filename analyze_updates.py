import pandas as pd

# Read the data
df_20240101_20250228 = pd.read_csv("studies_20240101_20250228.csv")
df_20240101_20250430 = pd.read_csv("studies_20240101_20250430.csv")

# Merge the datasets
df_merged = pd.merge(
    df_20240101_20250228[["nct_id", "first_post_date", "last_update_date"]],
    df_20240101_20250430[["nct_id", "first_post_date", "last_update_date"]],
    how="outer",
    on=["nct_id"],
    suffixes=("20250228", "20250430")
)

# Calculate total rows
total_rows = len(df_merged)
print(f"1. Total rows: {total_rows}")

# Calculate rows where last_update_date20250228 is NaN but last_update_date20250430 is not
new_in_430 = df_merged[
    df_merged["last_update_date20250228"].isna() & 
    df_merged["last_update_date20250430"].notna()
].shape[0]
print(f"2. New in 4/30 dataset: {new_in_430}")

# Calculate rows where last_update_date20250430 is NaN but last_update_date20250228 is not
removed_in_430 = df_merged[
    df_merged["last_update_date20250228"].notna() & 
    df_merged["last_update_date20250430"].isna()
].shape[0]
print(f"3. Removed in 4/30 dataset: {removed_in_430}")

# Calculate rows where both dates exist but are different
updated = df_merged[
    df_merged["last_update_date20250228"].notna() & 
    df_merged["last_update_date20250430"].notna() &
    (df_merged["last_update_date20250228"] != df_merged["last_update_date20250430"])
].shape[0]
print(f"4. Updated between datasets: {updated}")

# Verify the counts add up
print(f"\nVerification: {new_in_430 + removed_in_430 + updated} rows have changes")
print(f"Remaining rows: {total_rows - (new_in_430 + removed_in_430 + updated)} rows are unchanged") 