import requests
import pandas as pd
import os
import time

os.makedirs('data', exist_ok=True)

# ==========================================
# THE SMART DATA EXTRACTOR
# ==========================================
def extract_data(json_data, metric, scenario, target_list):
    """Recursively hunts for country codes in the messy JSON."""
    def dig(node, current_percentile):
        if isinstance(node, dict):
            for key, value in node.items():
                # If the key is a percentile, remember it
                if key in ['median', 'p10', 'p90']:
                    dig(value, key)
                # If the key is exactly 3 uppercase letters, it's an ISO3 Country Code!
                elif isinstance(key, str) and len(key) == 3 and key.isalpha() and key.isupper():
                    if isinstance(value, dict):
                        for year_date, temp_val in value.items():
                            try:
                                clean_year = int(str(year_date).split('-')[0])
                                target_list.append({
                                    'ISO3': key,
                                    'Year': clean_year,
                                    'Metric': metric,
                                    'Scenario': scenario,
                                    'Percentile': current_percentile,
                                    'Value': temp_val
                                })
                            except ValueError:
                                pass
                # Otherwise, keep digging deeper into the layers
                else:
                    dig(value, current_percentile)

    # Start digging from the 'data' root
    if 'data' in json_data:
        dig(json_data['data'], current_percentile='median')

# ==========================================
# THE DOWNLOAD LOOP
# ==========================================
metrics = ['tas', 'hd30', 'rx1day']
scenarios = ['ssp126', 'ssp245', 'ssp585']

print("🌍 Starting World Bank SMART Download...")
print("Hunting for data using recursive search...\n")

# 1. FUTURE PROJECTIONS
future_records = []
for metric in metrics:
    for scenario in scenarios:
        print(f"⏳ Fetching FUTURE: {metric.upper()} | {scenario.upper()}...")
        url = f"https://cckpapi.worldbank.org/api/v1/cmip6-x0.25_timeseries_{metric}_timeseries_annual_2015-2100_median,p10,p90_{scenario}_ensemble_all_mean/global_countries?_format=json"
        
        response = requests.get(url)
        if response.status_code == 200:
            extract_data(response.json(), metric, scenario, future_records)
            print("  ✅ Success. Pausing 1s...")
        else:
            print(f"  ❌ Failed (Status {response.status_code})")
        time.sleep(1)

df_future = pd.DataFrame(future_records)
df_future.to_csv("data/world_bank_projections.csv", index=False)
print(f"\n💾 Saved world_bank_projections.csv ({len(df_future)} rows)\n")


# 2. HISTORICAL BASELINE
hist_records = []
for metric in metrics:
    print(f"⏳ Fetching HISTORICAL: {metric.upper()}...")
    url = f"https://cckpapi.worldbank.org/api/v1/cmip6-x0.25_timeseries_{metric}_timeseries_annual_1950-2014_median_historical_ensemble_all_mean/global_countries?_format=json"
    
    response = requests.get(url)
    if response.status_code == 200:
        # Notice we hardcode the scenario as 'historical' here
        extract_data(response.json(), metric, "historical", hist_records)
        print("  ✅ Success. Pausing 1s...")
    else:
        print(f"  ❌ Failed (Status {response.status_code})")
    time.sleep(1)

df_hist = pd.DataFrame(hist_records)
df_hist.to_csv("data/historical_climate.csv", index=False)
print(f"\n💾 Saved historical_climate.csv ({len(df_hist)} rows)\n")

print("🎉 ALL DONE!")