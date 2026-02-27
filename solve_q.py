import pandas as pd
import numpy as np

# Load Data
df = pd.read_excel('q-clean-up-excel-sales-data.xlsx')

def clean_country(c):
    if pd.isna(c):
        return c
    c = str(c).strip().lower().replace('.', '').replace(' ', '')
    if c in ['uk', 'unitedkingdom', 'greatbritain', 'gb']:
        return 'UK'
    if c in ['us', 'usa', 'unitedstates', 'america']:
        return 'USA'
    if c in ['fra', 'france']:
        return 'France'
    if c in ['bra', 'brazil']:
        return 'Brazil'
    if c in ['ind', 'india']:
        return 'India'
    return c.upper()

df['Country'] = df['Country'].apply(clean_country)

# Clean dates - format mixed handles "MM-DD-YYYY" and "YYYY/MM/DD" automatically in newer pandas
df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
cutoff_date = pd.to_datetime('Fri Jan 20 2023 13:00:20 GMT+0530')

# Extract product
df['Product'] = df['Product/Code'].astype(str).str.split('/').str[0].str.strip()

def clean_currency(val):
    if pd.isna(val) or val == '' or str(val).lower() == 'nan':
        return np.nan
    s = str(val).replace('USD', '').replace(',', '').strip()
    try:
        return float(s)
    except:
        return np.nan

df['Sales'] = df['Sales'].apply(clean_currency)
df['Cost'] = df['Cost'].apply(clean_currency)

df['Cost'] = df.apply(lambda row: row['Sales'] * 0.5 if pd.isna(row['Cost']) else row['Cost'], axis=1)

# Convert df date to UTC aware if naive, let's localize to Asia/Kolkata (+05:30)
df['Date'] = df['Date'].dt.tz_localize('Asia/Kolkata')

df_filtered = df[
    (df['Date'] <= cutoff_date) &
    (df['Product'].str.lower() == 'iota') &
    (df['Country'] == 'UK')
]

print("Filtered rows:", len(df_filtered))

if len(df_filtered) > 0:
    total_sales = df_filtered['Sales'].sum()
    total_cost = df_filtered['Cost'].sum()
    total_margin = (total_sales - total_cost) / total_sales
    print(f"Total Sales: {total_sales}")
    print(f"Total Cost: {total_cost}")
    print(f"Total Margin: {total_margin:.4f} ({total_margin * 100:.2f}%)")
    
    # Optional print for debugging
    # print(df_filtered[['Date', 'Country', 'Product', 'Sales', 'Cost']].head(10))
else:
    print("No rows found!")

