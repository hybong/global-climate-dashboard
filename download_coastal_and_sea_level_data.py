import pandas as pd
import requests
import zipfile
import io
import os

# 1. Ensure the data directory exists
os.makedirs('data', exist_ok=True)

# ==========================================
# PHASE 1: GLOBAL MEAN SEA LEVEL (EPA/CSIRO)
# ==========================================
print("🌊 Downloading Sea Level Data...")
url_sl = "https://raw.githubusercontent.com/datasets/sea-level-rise/master/data/epa-sea-level.csv"
df_sl = pd.read_csv(url_sl)

# The dataset is in inches. Convert to millimeters for scientific standard.
df_sl['GMSL_mm'] = df_sl['CSIRO Adjusted Sea Level'] * 25.4
df_sl = df_sl[['Year', 'GMSL_mm']].dropna()

df_sl.to_csv('data/sea_level.csv', index=False)
print("✅ Saved sea_level.csv")


# ==========================================
# PHASE 2: COASTAL POPULATION RISK (World Bank)
# ==========================================
print("\n🌍 Downloading Coastal Population Data (Fetching World Bank ZIPs)...")

def fetch_wb_indicator(indicator_code, value_name):
    """Downloads a World Bank dataset ZIP, extracts the CSV, and cleans it."""
    url = f"https://api.worldbank.org/v2/en/indicator/{indicator_code}?downloadformat=csv"
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    # Extract the main data CSV (it always starts with API_)
    csv_name = [f for f in z.namelist() if f.startswith('API_')][0]
    with z.open(csv_name) as f:
        df = pd.read_csv(f, skiprows=4) # Skip World Bank metadata headers
    
    # Drop junk columns and melt into a clean Time Series
    drop_cols = ['Country Name', 'Indicator Name', 'Indicator Code']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')] # Drop trailing empty columns
    
    df = df.melt(id_vars=['Country Code'], var_name='Year', value_name=value_name)
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    df = df.rename(columns={'Country Code': 'ISO3'})
    
    return df.dropna(subset=['Year'])

# Fetch % of population below 5 meters AND total population
print("   -> Fetching % of population below 5m...")
df_perc = fetch_wb_indicator('EN.POP.EL5M.ZS', 'Percentage')

print("   -> Fetching total population...")
df_tot = fetch_wb_indicator('SP.POP.TOTL', 'Total_Pop')

print("   -> Merging and calculating absolute risk...")
# Calculate absolute number of people at risk
df_pop = pd.merge(df_perc, df_tot, on=['ISO3', 'Year'])
df_pop['Pop_At_Risk'] = (df_pop['Percentage'] / 100) * df_pop['Total_Pop']
df_pop = df_pop[['ISO3', 'Year', 'Pop_At_Risk']]

# ==========================================
# PHASE 3: INTERPOLATION (For smooth Streamlit animation)
# ==========================================
print("   -> Interpolating missing years for smooth dashboard animation...")
# Pivot to grid, interpolate missing years linearly, and melt back
df_pivot = df_pop.pivot(index='ISO3', columns='Year', values='Pop_At_Risk')
df_pivot = df_pivot.interpolate(method='linear', axis=1, limit_direction='both')
df_final = df_pivot.reset_index().melt(id_vars='ISO3', var_name='Year', value_name='Pop_At_Risk').dropna()

# Round to whole people
df_final['Pop_At_Risk'] = df_final['Pop_At_Risk'].round()

df_final.to_csv('data/coastal_pop.csv', index=False)
print("✅ Saved coastal_pop.csv")
print("\n🎉 All data prepared! You can now launch your Streamlit dashboard.")