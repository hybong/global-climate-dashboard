# Findings and discussion

These examples use the datasets bundled with the dashboard. Follow the [local setup instructions](../README.md#run-locally) to reproduce them.

## CO₂ rankings depend on the metric

In 2022, China ranked first for total annual CO₂ emissions at **11.7 Gt**. Qatar ranked first for CO₂ emissions per capita at **37.9 tonnes per person**. The two views answer different questions. Total emissions show the scale of each country’s contribution, and per-capita emissions put that total in relation to population.

Set the timeline to **2022** and switch between **Total CO2 (Emissions)** and **CO2 Per Capita**. Compare the top bar in each ranking. [Global emissions map](dashboard-preview.png) · [Bundled OWID data](../data/owid-co2-data.csv)

## Malaysia’s projected extreme heat varies by scenario

The bundled projections give Malaysia a 2100 median of **247 days above 30°C** under SSP1-2.6, **301 days** under SSP2-4.5, and **352 days** under SSP5-8.5. The difference between the lowest and highest scenario medians is about **105 days in a year**. Under SSP5-8.5, the 10th–90th percentile band spans about **323–363 days** in 2100, giving a sense of the spread in the supplied projections.

Select **Malaysia**, then choose **Extreme Heat** in **Century Overview**. In **Compare Scenarios**, hover at 2100 to compare the three median traces. Switch to **Deep Dive** to see the SSP5-8.5 median and shaded percentile band. [Malaysia’s Century Overview](century-overview-malaysia.png) · [Bundled climate projections](../data/world_bank_projections.csv)

## Malaysia’s low-elevation coastal population grew from 1990 to 2015

The estimated population in Malaysia’s low-elevation coastal areas rose from **1.95 million in 1990** to **3.16 million in 2015**. Using the bundled national population totals, the share fell from **10.9% to 10.1%**. Malaysia had about **31.2 million people** in 2015, so the estimate represents about **one in ten residents**. [Bundled coastal exposure data](../data/coastal_pop.csv) · [Bundled population data](../data/owid-co2-data.csv)

The World Bank indicator uses coastal elevation at or below 5 metres as a measure of potential exposure. Estimating flood risk would also require local flood likelihood and information about flood defences. The dashboard puts Malaysia’s exposure estimate alongside global mean sea level for a descriptive comparison during their overlapping years, **1990–2013**. [World Bank indicator definition](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/EN.POP.EL5M.ZS)

Select **Malaysia** and choose **Coastal Population at Risk (Absolute)**. In **Coastal Threat**, hover over the 1990 and 2015 points on the exposure line. On the map and summary card, later years carry forward the 2015 count. Percentage mode uses the same exposure count and the total population for the selected year. [Bundled coastal exposure data](../data/coastal_pop.csv) · [Bundled sea level observations](../data/sea_level.csv)
