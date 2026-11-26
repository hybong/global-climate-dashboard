import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# ==========================================
# 1. PAGE CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="Global Climate Explorer", layout="wide")

DEFAULT_YEAR = 2022
DEFAULT_JUMP = 5
COASTAL_SURVEY_YEARS = (1990, 2000, 2015)

if 'selected_iso' not in st.session_state:
    st.session_state.selected_iso = 'GLOBAL'

# --- ANIMATION & MAP MEMORY VARIABLES ---
if 'playing' not in st.session_state:
    st.session_state.playing = False
if 'current_year' not in st.session_state:
    st.session_state.current_year = DEFAULT_YEAR
if 'last_clicked' not in st.session_state:
    st.session_state.last_clicked = None
st.session_state.setdefault('map_selection_revision', 0)
# ----------------------------------

st.title("Global Climate Dashboard: Drivers & Impacts")
st.markdown("Explore historical emissions, future climate projections, and their impacts on vulnerable coastal populations worldwide. Use the sidebar to customize your view and animate through time.")

# ==========================================
# 2. LOCAL DATA LOADING (CRASH-PROOF)
# ==========================================
@st.cache_data
def load_owid_data():
    return pd.read_csv("data/owid-co2-data.csv")

@st.cache_data
def load_wb_historical():
    file_path = "data/historical_climate.csv"
    df = pd.read_csv(file_path)
    if 'Percentile' not in df.columns:
        df['Percentile'] = 'median' 
    return df

@st.cache_data
def load_wb_projections():
    file_path = "data/world_bank_projections.csv"
    df = pd.read_csv(file_path)
    return df

@st.cache_data
def load_sea_level():
    return pd.read_csv("data/sea_level.csv")

@st.cache_data
def load_coastal_pop():
    return pd.read_csv("data/coastal_pop.csv")

def coastal_percentage(exposure):
    population = exposure['Total_Population']
    valid_population = population.where(np.isfinite(population) & population.gt(0))
    percentage = exposure['Pop_At_Risk'].div(valid_population).mul(100)
    return percentage.where(np.isfinite(percentage))

with st.spinner('Loading local datasets...'):
    owid_data = load_owid_data()
    df_owid_world = owid_data.loc[owid_data['country'] == 'World'].sort_values('year')
    df_owid = owid_data.dropna(subset=['iso_code'])
    df_proj_future = load_wb_projections()
    df_proj_hist = load_wb_historical()
    df_sea_level = load_sea_level()
    df_coastal_pop = load_coastal_pop()
    df_climate = pd.concat([df_proj_hist, df_proj_future], ignore_index=True)
    coastal_min_year = int(df_coastal_pop['Year'].min())
    coastal_max_year = int(df_coastal_pop['Year'].max())

    # WLD already includes the global exposure count. Other rows overlap it.
    world_population = df_owid_world[['year', 'population']].rename(
        columns={'year': 'Year', 'population': 'Total_Population'}
    )
    df_coastal_global = df_coastal_pop.loc[
        df_coastal_pop['ISO3'] == 'WLD', ['Year', 'Pop_At_Risk']
    ].merge(world_population, on='Year', how='left').sort_values('Year')
    df_coastal_global['Percentage_At_Risk'] = coastal_percentage(df_coastal_global)

    df_pop_lookup = df_owid[['iso_code', 'year', 'population']].rename(
        columns={'iso_code': 'ISO3', 'year': 'Year', 'population': 'Total_Population'}
    )
    df_coastal_pop = df_coastal_pop.merge(df_pop_lookup, on=['ISO3', 'Year'], how='left')
    df_coastal_pop['Percentage_At_Risk'] = coastal_percentage(df_coastal_pop)

    iso_to_name = {'GUF': 'French Guiana', 'REU': 'Réunion'}
    iso_to_name.update(zip(df_owid['iso_code'], df_owid['country']))
    iso_to_name['GLOBAL'] = "🌍 Global Overview"


# ==========================================
# 3. COMMAND CENTER (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Dashboard Controls")

# --- 1. Region Selection ---
country_codes = frozenset(iso for iso in df_owid['iso_code'].unique() if len(iso) == 3)
options = ['GLOBAL', *sorted(country_codes)]
display_options = [iso_to_name[iso] for iso in options]

# --- METRIC OPTIONS LIST ---
metric_options = [
    "Total CO2 (Emissions)", 
    "CO2 Per Capita", 
    "Temperature (°C)", 
    "Extreme Heat Days (>30°C)", 
    "Precipitation (mm)", 
    "Coastal Population at Risk (Absolute)", 
    "Coastal Population at Risk (%)" 
]
century_metrics = [
    "Temperature (°C) [tas]",
    "Extreme Heat (>30°C) [hd30]",
    "Maximum 1-Day Precipitation (mm) [rx1day]",
]
scenario_modes = ["Compare Scenarios", "Deep Dive: SSP5 Confidence Interval"]

# Initialize Master States
if 'map_metric_state' not in st.session_state:
    st.session_state.map_metric_state = metric_options[0]
st.session_state.setdefault('speed_slider', DEFAULT_JUMP)

def set_region_from_controls(code):
    st.session_state.selected_iso = code
    st.session_state.last_clicked = None
    st.session_state.map_selection_revision += 1

# Callback 1: Handle Region
def handle_dropdown():
    chosen_name = st.session_state.region_dropdown
    set_region_from_controls(options[display_options.index(chosen_name)])

# Callback 2: Handle Metric (THE FIX FOR THE UI BUG)
def handle_metric():
    st.session_state.map_metric_state = st.session_state.metric_dropdown

# Callback 3: Soft Reset
def reset_view():
    set_region_from_controls('GLOBAL')

# Callback 4: The "Nuclear" Master Reset
def reset_everything():
    reset_view()
    st.session_state.current_year = DEFAULT_YEAR
    st.session_state.playing = False
    st.session_state.map_metric_state = metric_options[0]
    st.session_state.speed_slider = DEFAULT_JUMP
    st.session_state.century_metric = century_metrics[0]
    st.session_state.century_scenario = scenario_modes[0]

# Force UI to match Master State
if st.session_state.selected_iso not in options:
    reset_view()
st.session_state.region_dropdown = iso_to_name[st.session_state.selected_iso]
st.session_state.metric_dropdown = st.session_state.map_metric_state

st.sidebar.subheader(
    "1. Focus Region",
    anchor=False,
    help="Choose Global Overview for planetary aggregates or select a country to view its data.",
)
st.sidebar.selectbox(
    "1. Focus Region:",
    options=display_options,
    key="region_dropdown",
    on_change=handle_dropdown,
    label_visibility="collapsed",
)

st.sidebar.button("Reset region", on_click=reset_view, width="stretch",
                  help="Return the focus to Global Overview.")

# --- 2. Map Variable Selection ---
st.sidebar.subheader(
    "2. Map Metric",
    anchor=False,
    help="Choose the metric displayed on the interactive map.",
)
map_var = st.sidebar.selectbox(
    "2. Map Metric:",
    options=metric_options,
    key="metric_dropdown",
    on_change=handle_metric,
    label_visibility="collapsed",
)

# --- 3. The Time Machine ---
st.sidebar.subheader("3. Timeline Animation", anchor=False)

if "CO2" in map_var:
    co2_column = 'co2' if map_var == metric_options[0] else 'co2_per_capita'
    available_years = df_owid.loc[np.isfinite(df_owid[co2_column]), 'year']
    min_year = 1950
    max_year = int(available_years.max()) if not available_years.empty else DEFAULT_YEAR
elif "Coastal" in map_var:
    min_year, max_year = coastal_min_year, coastal_max_year
else:
    min_year, max_year = 1950, 2100
    
if st.session_state.current_year > max_year:
    st.session_state.current_year = max_year
if st.session_state.current_year < min_year:
    st.session_state.current_year = min_year

def toggle_play():
    st.session_state.playing = not st.session_state.playing
    if st.session_state.playing and st.session_state.current_year >= max_year:
        st.session_state.current_year = min_year

play_control = st.sidebar.empty()

ui_year = st.sidebar.slider(
    "Selected Year:", 
    min_value=min_year, 
    max_value=max_year, 
    value=st.session_state.current_year,
    help="Drag to manually explore a specific year, or use the Play button to animate historical trends and future projections."
)

step_size = st.sidebar.slider(
    "Animation Jump (Years/Frame):", 
    min_value=1, 
    max_value=10, 
    step=1,
    key="speed_slider", 
    help="Adjust how many years the timeline skips forward with each tick."
)

st.sidebar.button("Reset all", key="reset_dashboard", on_click=reset_everything, width="stretch",
                  help="Restore region, map, timeline, and century defaults.")

if ui_year != st.session_state.current_year:
    st.session_state.current_year = ui_year
    st.session_state.playing = False
    st.rerun()

# Update the playback label once the rest of the timeline controls are in place.
play_control.button("⏸ Pause Timeline" if st.session_state.playing else "▶ Play Timeline",
                    key="toggle_timeline", on_click=toggle_play, width="stretch")
st.sidebar.divider()
st.sidebar.markdown("**Current Focus:**")
st.sidebar.info(f"{iso_to_name.get(st.session_state.selected_iso)}")
if st.session_state.selected_iso == 'GLOBAL':
    st.sidebar.write("Viewing aggregate data for the entire planet.")
else:
    st.sidebar.write("Viewing isolated national data. Dashed lines represent the global benchmark.")

# ==========================================
# 4. DATA FILTERING HELPER
# ==========================================
is_global = st.session_state.selected_iso == 'GLOBAL'
selected_year = st.session_state.current_year

if is_global:
    df_owid_view = df_owid_world
    df_climate_view = df_climate.groupby(['Year', 'Metric', 'Scenario', 'Percentile'])['Value'].mean().reset_index()
else:
    df_owid_view = df_owid[df_owid['iso_code'] == st.session_state.selected_iso]
    df_climate_view = df_climate[df_climate['ISO3'] == st.session_state.selected_iso]

df_climate_global = df_climate.groupby(['Year', 'Metric', 'Scenario', 'Percentile'])['Value'].mean().reset_index()


# ==========================================
# 5. ROW 1: INSTANT KPI SCORECARDS
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

if st.session_state.selected_iso == 'GLOBAL':
    location_label = "Global"
else:
    location_label = iso_to_name.get(st.session_state.selected_iso, st.session_state.selected_iso)

# --- KPI 1 ---
total_co2 = df_owid_view['co2'].where(np.isfinite(df_owid_view['co2'])).sum(min_count=1)
val_co2 = total_co2 / 1000 if is_global else total_co2
unit_label = "Gt" if is_global else "Mt"

kpi1.metric(
    label=f"Total CO2 ({location_label})", 
    value=f"{val_co2:,.0f} {unit_label}" if np.isfinite(val_co2) else "Data unavailable",
    help="Cumulative historical CO2 emissions from fossil fuels and industry."
)

# --- KPI 2 ---
df_kpi_projection = df_climate_view.loc[
    (df_climate_view['Scenario'] == 'ssp585') & (df_climate_view['Percentile'] == 'median')
]
temp_by_year = df_kpi_projection.loc[df_kpi_projection['Metric'] == 'tas'].set_index('Year')['Value']
temp_change = temp_by_year.get(2100, np.nan) - temp_by_year.get(2015, np.nan)
kpi2.metric(
    label=f"Temp Increase ({location_label})",
    value=f"{temp_change:+.2f} °C" if np.isfinite(temp_change) else "Data unavailable",
    help="Projected temperature change from 2015 to 2100 under the SSP5-8.5 (pessimistic) scenario."
)

# --- KPI 3 ---
heat_by_year = df_kpi_projection.loc[df_kpi_projection['Metric'] == 'hd30'].set_index('Year')['Value']
heat_2100 = heat_by_year.get(2100, np.nan)
kpi3.metric(
    label=f"Extreme Hot Days ({location_label})",
    value=f"{heat_2100:.0f} Days" if np.isfinite(heat_2100) else "Data unavailable",
    help="Projected number of days exceeding 30°C in the year 2100 (SSP5-8.5 scenario)."
)

# --- KPI 4: Coastal Population at Risk ---
if is_global:
    df_pop_view = df_coastal_global
else:
    df_pop_view = df_coastal_pop[df_coastal_pop['ISO3'] == st.session_state.selected_iso]

first_survey_year, last_survey_year = COASTAL_SURVEY_YEARS[0], COASTAL_SURVEY_YEARS[-1]
coastal_note = ""
if coastal_min_year <= selected_year < first_survey_year:
    coastal_note = f"{first_survey_year} exposure estimate carried backward."
elif last_survey_year < selected_year <= coastal_max_year:
    coastal_note = f"{last_survey_year} exposure estimate carried forward."

show_coastal_percentage = "%" in map_var
coastal_column = 'Percentage_At_Risk' if show_coastal_percentage else 'Pop_At_Risk'
coastal_unit = "%" if show_coastal_percentage else "Abs"
coastal_values = df_pop_view.loc[df_pop_view['Year'] == selected_year, coastal_column]
pop_val = coastal_values.iloc[0] if not coastal_values.empty else np.nan
if not np.isfinite(pop_val):
    pop_str = "No Data"
elif show_coastal_percentage:
    pop_str = f"{pop_val:.2f} %"
elif pop_val >= 1_000_000_000:
    pop_str = f"{pop_val / 1_000_000_000:.2f} B"
elif pop_val >= 1_000_000:
    pop_str = f"{pop_val / 1_000_000:.1f} M"
else:
    pop_str = f"{pop_val:,.0f}"

coastal_help = "Estimated population living below 5 meters elevation."
if show_coastal_percentage:
    coastal_help = f"Estimated share of the {selected_year} population living below 5 meters elevation."
kpi4.metric(label=f"Pop. at Risk ({coastal_unit}) ({location_label})", value=pop_str, help=coastal_help)
if coastal_note and np.isfinite(pop_val):
    kpi4.caption(coastal_note)

st.divider()


# ==========================================
# 6. ROW 2: THE MASTER MAP (ANIMATED)
# ==========================================
st.header(f"1. Spatial Distribution: {map_var} ({selected_year})")
st.markdown("Use the sidebar controls to change the metric, focus region, or animate through time. Click on countries in the map to isolate their data in the subsequent charts.")

if "CO2" in map_var:
    df_map = df_owid[df_owid['year'] == selected_year]
    color_col = co2_column
    color_scale = px.colors.sequential.Reds
    
    if "Total" in map_var:
        global_max = df_owid['co2'].quantile(1)
        fixed_range = [0, global_max]
    else:
        global_max = df_owid['co2_per_capita'].quantile(0.98)
        fixed_range = [0, global_max]

elif "Coastal" in map_var:
    df_map = df_coastal_pop[df_coastal_pop['Year'] == selected_year]
    color_col = coastal_column
    color_scale = px.colors.sequential.Blues 
    
    global_max = df_coastal_pop[color_col].quantile(0.95)
    fixed_range = [0, global_max]
    if show_coastal_percentage and not np.isfinite(df_map[color_col]).any():
        st.info(f"Coastal percentages are unavailable for {selected_year}. Population data is missing.")
    else:
        map_note = coastal_note
        if show_coastal_percentage:
            map_note = f"{coastal_note} Percentages use {selected_year} population estimates.".strip()
        if map_note:
            st.caption(map_note)

else:
    # 1. Determine the metric code dynamically
    if "Temperature" in map_var:
        metric_filter = 'tas'
    elif "Extreme Heat" in map_var:
        metric_filter = 'hd30'
    else:
        metric_filter = 'rx1day'
        
    scenario_filter = 'historical' if selected_year <= 2014 else 'ssp585'
    
    df_map = df_climate[
        (df_climate['Year'] == selected_year) &
        (df_climate['Metric'] == metric_filter) & 
        (df_climate['Scenario'] == scenario_filter) & 
        (df_climate['Percentile'] == 'median')
    ]
    color_col = 'Value'
    df_metric_all = df_climate[df_climate['Metric'] == metric_filter]
    
    # 2. Assign distinctive color scales and boundaries
    if "Temperature" in map_var:
        color_scale = px.colors.sequential.Inferno
        global_min = df_metric_all['Value'].quantile(0.01)
        global_max = df_metric_all['Value'].quantile(0.99)
        fixed_range = [global_min, global_max]
    elif "Extreme Heat" in map_var:
        color_scale = px.colors.sequential.YlOrRd
        global_max = df_metric_all['Value'].quantile(0.99)
        fixed_range = [0, global_max]
    else:
        color_scale = px.colors.sequential.Teal
        global_max = df_metric_all['Value'].quantile(0.99)
        fixed_range = [0, global_max]

fig_map = px.choropleth(
    df_map, locations="ISO3" if "CO2" not in map_var else "iso_code", color=color_col,
    hover_name="ISO3" if "CO2" not in map_var else "country", 
    color_continuous_scale=color_scale,
    range_color=fixed_range
)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, uirevision=map_var)

# A new key clears the previous selection when a sidebar action changes focus.
map_revision = st.session_state.map_selection_revision
map_key = f"focus_map_{map_revision}"

def handle_map_selection():
    # A rerun can carry a selection for the chart that was just replaced.
    if map_revision != st.session_state.map_selection_revision:
        return
    points = st.session_state[map_key].selection.points
    if points:
        clicked_iso = points[0].get("location")
        if isinstance(clicked_iso, str) and clicked_iso in country_codes:
            st.session_state.selected_iso = clicked_iso
            st.session_state.last_clicked = clicked_iso
    elif st.session_state.last_clicked is not None:
        st.session_state.selected_iso = 'GLOBAL'
        st.session_state.last_clicked = None

st.plotly_chart(fig_map, key=map_key, on_select=handle_map_selection,
                selection_mode="points", width="stretch")

st.divider()


# ==========================================
# 7. ROW 3: DYNAMIC TOP 10 & REGIONAL IMPACT
# ==========================================
st.header("2. Primary Emitters & Localized Regional Impacts")
st.markdown("The left chart highlights the top 10 emitters or most vulnerable countries based on the selected metric. The right chart focuses on ASEAN nations, showing their historical and projected trends.")
col_bar, col_heat = st.columns(2)

asean_iso = ['MYS', 'IDN', 'THA', 'VNM', 'PHL', 'SGP', 'KHM', 'LAO', 'MMR', 'BRN']

if "CO2" in map_var:
    metric_col = co2_column
    df_bar_source = df_map.loc[df_map['iso_code'].isin(country_codes) & np.isfinite(df_map[metric_col])]
    df_bar = df_bar_source.nlargest(10, metric_col).sort_values(metric_col, ascending=True)
    bar_x, bar_y = metric_col, 'country'
    bar_title = "Top 10 Emitters" if "Total" in map_var else "Top 10 Per Capita Emitters"
    bar_color = '#ef553b'

    df_heat_source = df_owid[df_owid['iso_code'].isin(asean_iso)].copy()
    df_heat_source = df_heat_source[df_heat_source['year'] >= 1950]
    df_heat_source['Country'] = df_heat_source['iso_code'].map(iso_to_name)
    df_pivot = df_heat_source.pivot(index='Country', columns='year', values=metric_col)
    heat_title = "ASEAN CO2 Matrix"
    heat_color = "Reds"
    heat_label = "CO2 (Mt)" if "Total" in map_var else "CO2 (Per Capita)"

elif "Coastal" in map_var:
    df_bar_source = df_map.loc[df_map['ISO3'].isin(country_codes) & np.isfinite(df_map[coastal_column])]
    df_bar = df_bar_source.nlargest(10, coastal_column).sort_values(coastal_column, ascending=True)
    df_bar['Country'] = df_bar['ISO3'].map(iso_to_name)
    bar_x, bar_y = coastal_column, 'Country'
    bar_title = f"Top 10 Countries by Coastal Risk ({'%' if show_coastal_percentage else 'Absolute'})"
    bar_color = '#636efa' 

    df_heat_source = df_coastal_pop[df_coastal_pop['ISO3'].isin(asean_iso)].copy()
    df_heat_source['Country'] = df_heat_source['ISO3'].map(iso_to_name)
    df_pivot = df_heat_source.pivot(index='Country', columns='Year', values=coastal_column)
    heat_title = "ASEAN Coastal Vulnerability Matrix"
    heat_color = "Blues"
    heat_label = "% of Population" if show_coastal_percentage else "Absolute Pop"

else:
    # Select the labels for the climate ranking and matrix.
    if "Temperature" in map_var:
        bar_title = "Top 10 Highest Temperatures"
        bar_color = '#FFA15A'
        heat_title = "ASEAN Temperature Matrix"
        heat_color = "Inferno"
        heat_label = "Temp (°C)"
    elif "Extreme Heat" in map_var:
        bar_title = "Top 10 Extreme Heat Zones"
        bar_color = '#EF553B' 
        heat_title = "ASEAN Extreme Heat Matrix"
        heat_color = "YlOrRd"
        heat_label = "Days >30°C"
    else:
        bar_title = "Top 10 Highest Precipitation"
        bar_color = '#00CC96'
        heat_title = "ASEAN Precipitation Matrix"
        heat_color = "Teal"
        heat_label = "Rain (mm)"

    df_bar_source = df_map.loc[np.isfinite(df_map['Value'])]
    df_bar = df_bar_source.nlargest(10, 'Value').sort_values('Value', ascending=True)
    df_bar['Country'] = df_bar['ISO3'].map(iso_to_name).fillna(df_bar['ISO3'])
    bar_x, bar_y = 'Value', 'Country'

    hist_part = df_climate[(df_climate['ISO3'].isin(asean_iso)) & (df_climate['Metric'] == metric_filter) & (df_climate['Scenario'] == 'historical') & (df_climate['Percentile'] == 'median') & (df_climate['Year'] <= 2014)]
    fut_part = df_climate[(df_climate['ISO3'].isin(asean_iso)) & (df_climate['Metric'] == metric_filter) & (df_climate['Scenario'] == 'ssp585') & (df_climate['Percentile'] == 'median') & (df_climate['Year'] > 2014)]
    df_heat_source = pd.concat([hist_part, fut_part]).copy()
    
    df_heat_source['Country'] = df_heat_source['ISO3'].map(iso_to_name)
    df_pivot = df_heat_source.pivot(index='Country', columns='Year', values='Value')

title_style = """
<div style="height: 85px; display: flex; align-items: flex-end; padding-bottom: 5px;">
    <h3 style="margin: 0; line-height: 1.2; font-size: 1.4rem;">{text}</h3>
</div>
"""

with col_bar:
    # THE FIX 1: Use HTML to force a minimum height so wrapping doesn't push the chart down
    st.markdown(title_style.format(text=f"{bar_title} ({selected_year})"), unsafe_allow_html=True)
    
    fig_bar = px.bar(
        df_bar, x=bar_x, y=bar_y, orientation='h',
        labels={bar_x: heat_label, bar_y: ''},
        color_discrete_sequence=[bar_color] 
    )
    if df_bar.empty:
        fig_bar.add_annotation(text="No data for this year", x=0.5, y=0.5,
                               xref="paper", yref="paper", showarrow=False)
    # THE FIX 2: Give the bottom margin (b=40) enough room for the X-axis text
    fig_bar.update_layout(margin=dict(t=10, b=40), height=400, uirevision=map_var)
    st.plotly_chart(fig_bar, width="stretch", theme=None)

with col_heat:
    # Match the minimum height of the left title
    st.markdown(title_style.format(text=heat_title), unsafe_allow_html=True)

    fig_heat = px.imshow(
        df_pivot,
        labels=dict(x="Year", y="", color=heat_label),
        x=df_pivot.columns,
        y=df_pivot.index,
        aspect="auto", 
        color_continuous_scale=heat_color
    )
    # Match the exact same margins as the bar chart
    fig_heat.update_layout(margin=dict(t=10, b=40), height=400, uirevision=map_var)
    fig_heat.update_xaxes(side="bottom")
    st.plotly_chart(fig_heat, width="stretch", theme=None)

st.divider()

# ==========================================
# 8. ROW 5: CENTURY OVERVIEW (MASTER CHART)
# ==========================================
st.header(f"3. The Century Overview — {location_label} (1950–2100)")
st.markdown("This dual-axis chart overlays historical fossil fuel CO2 emissions with projected climate impacts under different SSP scenarios. Use the dropdown to switch between temperature, extreme heat, and precipitation metrics, and toggle between comparing all scenarios or focusing on the confidence interval of the pessimistic SSP5-8.5 pathway.")

col_dropdown, col_toggle = st.columns([2, 1])

with col_dropdown:
    metric_choice = st.selectbox(
        "Select a Climate Impact to compare against CO2 Emissions:",
        century_metrics,
        key="century_metric",
        help="Overlay different projected climate consequences on top of historical fossil fuel consumption."
    )

with col_toggle:
    view_mode = st.radio(
        "Chart View:", 
        scenario_modes,
        key="century_scenario",
        horizontal=True,
        help="Compare multiple SSP pathways, or view the 80% statistical confidence band for the pessimistic SSP5-8.5 scenario."
    )

if "tas" in metric_choice:
    metric_code = "tas"
    right_y_title = "Temperature (°C)"
elif "hd30" in metric_choice:
    metric_code = "hd30"
    right_y_title = "Days > 30°C"
else:
    metric_code = "rx1day"
    right_y_title = "Precipitation (mm)"

fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

df_co2_recent = df_owid_view[df_owid_view['year'] >= 1950].dropna(subset=['coal_co2', 'oil_co2', 'gas_co2'])

fig_dual.add_trace(
    go.Scatter(x=df_co2_recent['year'], y=df_co2_recent['coal_co2'], name="Coal",
               mode='lines', line=dict(width=0), fillcolor='rgba(0, 0, 0, 0.2)', 
               stackgroup='co2_stack', legend='legend'), 
    secondary_y=False,
)
fig_dual.add_trace(
    go.Scatter(x=df_co2_recent['year'], y=df_co2_recent['oil_co2'], name="Oil",
               mode='lines', line=dict(width=0), fillcolor='rgba(100, 100, 100, 0.2)', 
               stackgroup='co2_stack', legend='legend'),
    secondary_y=False,
)
fig_dual.add_trace(
    go.Scatter(x=df_co2_recent['year'], y=df_co2_recent['gas_co2'], name="Gas",
               mode='lines', line=dict(width=0), fillcolor='rgba(135, 206, 235, 0.3)', 
               stackgroup='co2_stack', legend='legend'),
    secondary_y=False,
)

df_metric = df_climate_view[df_climate_view['Metric'] == metric_code]
df_hist = df_metric[df_metric['Scenario'] == 'historical']
if not df_hist.empty:
    fig_dual.add_trace(go.Scatter(x=df_hist['Year'], y=df_hist['Value'], name='Historical Climate', line=dict(color='black', width=2), legend='legend2'), secondary_y=True)

if view_mode == "Compare Scenarios":
    df_ssp1 = df_metric[(df_metric['Scenario'] == 'ssp126') & (df_metric['Percentile'] == 'median')]
    if not df_ssp1.empty:
        fig_dual.add_trace(go.Scatter(x=df_ssp1['Year'], y=df_ssp1['Value'], name='SSP1-2.6 (Optimistic)', line=dict(color='green', width=3), legend='legend2'), secondary_y=True)

    df_ssp2 = df_metric[(df_metric['Scenario'] == 'ssp245') & (df_metric['Percentile'] == 'median')]
    if not df_ssp2.empty:
        fig_dual.add_trace(go.Scatter(x=df_ssp2['Year'], y=df_ssp2['Value'], name='SSP2-4.5 (Realistic)', line=dict(color='orange', width=3), legend='legend2'), secondary_y=True)

    df_ssp5 = df_metric[(df_metric['Scenario'] == 'ssp585') & (df_metric['Percentile'] == 'median')]
    if not df_ssp5.empty:
        fig_dual.add_trace(go.Scatter(x=df_ssp5['Year'], y=df_ssp5['Value'], name='SSP5-8.5 (Pessimistic)', line=dict(color='red', width=3), legend='legend2'), secondary_y=True)

else:
    df_ssp5_med = df_metric[(df_metric['Scenario'] == 'ssp585') & (df_metric['Percentile'] == 'median')]
    df_ssp5_p10 = df_metric[(df_metric['Scenario'] == 'ssp585') & (df_metric['Percentile'] == 'p10')]
    df_ssp5_p90 = df_metric[(df_metric['Scenario'] == 'ssp585') & (df_metric['Percentile'] == 'p90')]
    
    if not df_ssp5_med.empty and not df_ssp5_p10.empty and not df_ssp5_p90.empty:
        fig_dual.add_trace(go.Scatter(x=df_ssp5_p90['Year'], y=df_ssp5_p90['Value'], mode='lines', line=dict(width=0), showlegend=False, legend='legend2'), secondary_y=True)
        fig_dual.add_trace(go.Scatter(x=df_ssp5_p10['Year'], y=df_ssp5_p10['Value'], name='SSP5 80% Confidence Band', fill='tonexty', mode='lines', line=dict(width=0), fillcolor='rgba(255, 0, 0, 0.2)', legend='legend2'), secondary_y=True)
        fig_dual.add_trace(go.Scatter(x=df_ssp5_med['Year'], y=df_ssp5_med['Value'], name='SSP5-8.5 Median', line=dict(color='red', width=3), legend='legend2'), secondary_y=True)

if not is_global:
    df_metric_glob_hist = df_climate_global[(df_climate_global['Metric'] == metric_code) & (df_climate_global['Scenario'] == 'historical') & (df_climate_global['Percentile'] == 'median')]
    if not df_metric_glob_hist.empty:
        fig_dual.add_trace(go.Scatter(x=df_metric_glob_hist['Year'], y=df_metric_glob_hist['Value'], name='Global Avg (Historical)', line=dict(color='gray', width=2, dash='dash'), showlegend=False, legend='legend2'), secondary_y=True)

    df_metric_glob = df_climate_global[(df_climate_global['Metric'] == metric_code) & (df_climate_global['Scenario'] == 'ssp585') & (df_climate_global['Percentile'] == 'median')]
    if not df_metric_glob.empty:
        fig_dual.add_trace(go.Scatter(x=df_metric_glob['Year'], y=df_metric_glob['Value'], name='Global Avg (SSP5)', line=dict(color='gray', width=2, dash='dash'), legend='legend2'), secondary_y=True)

# THE FIX: Removed l=0 and r=0 so Plotly can auto-calculate space for the Left/Right axis titles.
# Also increased b=40 to give the "Year" x-axis title room to breathe.
fig_dual.update_layout(
    xaxis_title="Year", 
    hovermode="x unified",
    margin=dict(t=80, b=40), 
    height=600,
    legend=dict(orientation="v", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    legend2=dict(orientation="v", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    uirevision=map_var
)

fig_dual.update_yaxes(title_text="Total Annual CO2 (Mt)", secondary_y=False, showgrid=False)
fig_dual.update_yaxes(title_text=right_y_title, secondary_y=True, showgrid=True)

st.plotly_chart(fig_dual, width="stretch", theme=None)

st.divider()


# ==========================================
# 8.5 ROW 6: COASTAL VULNERABILITY (DYNAMIC DUAL AXIS)
# ==========================================
st.header("4. Coastal Threat: Sea Level Rise vs. Population Exposure")
st.markdown("Compare global mean sea level rise with the population living below 5 meters elevation. Use Map Metric in the sidebar to switch between absolute and percentage views.")

sea_start, sea_end = int(df_sea_level['Year'].min()), int(df_sea_level['Year'].max())
st.caption(
    f"Sea level covers {sea_start}–{sea_end}. "
    f"The coastal exposure chart covers {first_survey_year}–{last_survey_year}."
)

if show_coastal_percentage:
    y_axis_title = "Population at Risk (%)"
    line_name_suffix = "(%)"
else:
    y_axis_title = "Absolute Population at Risk"
    line_name_suffix = "(Absolute)"

fig_coast = make_subplots(specs=[[{"secondary_y": True}]])
pop_name = "Global Population" if is_global else location_label

# Trace 1: Sea Level
fig_coast.add_trace(
    go.Scatter(
        x=df_sea_level['Year'], y=df_sea_level['GMSL_mm'], name="Sea Level Rise (mm)",
        fill='tozeroy', mode='lines', fillcolor='rgba(0, 105, 148, 0.3)', 
        line=dict(color='rgba(0, 105, 148, 0.8)', width=2),
        legend='legend'
    ),
    secondary_y=False,
)

if not df_pop_view.empty:
    df_pop_clean = df_pop_view[df_pop_view['Year'].between(first_survey_year, last_survey_year)]
    
    # Trace 2: The line 
    fig_coast.add_trace(
        go.Scatter(
            x=df_pop_clean['Year'], y=df_pop_clean[coastal_column], name=f"{pop_name} {line_name_suffix}",
            mode='lines', line=dict(color='firebrick', width=3),
            legend='legend2'
        ),
        secondary_y=True,
    )

    # Trace 3: The survey dots 
    df_survey_dots = df_pop_clean[df_pop_clean['Year'].isin(COASTAL_SURVEY_YEARS)]
    
    fig_coast.add_trace(
        go.Scatter(
            x=df_survey_dots['Year'], y=df_survey_dots[coastal_column],
            mode='markers', 
            marker=dict(size=8, color='firebrick', symbol='circle', line=dict(color='white', width=1)),
            showlegend=False, hoverinfo='skip'
        ),
        secondary_y=True,
    )

fig_coast.update_layout(
    xaxis_title="Year", 
    hovermode="x unified",
    margin=dict(l=50, r=50, t=100, b=80), height=550,
    legend=dict(orientation="v", yanchor="bottom", y=1.02, xanchor="left", x=0),
    legend2=dict(orientation="v", yanchor="bottom", y=1.02, xanchor="right", x=1),
    uirevision=map_var
)

fig_coast.update_yaxes(title_text="Global Sea Level Rise (mm)", secondary_y=False, showgrid=False)
fig_coast.update_yaxes(title_text=y_axis_title, secondary_y=True, showgrid=True)

st.plotly_chart(fig_coast, width="stretch", theme=None)
st.divider()

# ==========================================
# 9. CONTINUOUS ANIMATION ENGINE
# ==========================================
constant_sleep = 0.5  # Fixed time between frames

if st.session_state.playing:
    time.sleep(constant_sleep)
    st.session_state.current_year = min(selected_year + step_size, max_year) if selected_year < max_year else min_year
    st.rerun()

# ==========================================
# 10. FOOTER & DATA SOURCES
# ==========================================
st.caption("Data Sources: [Our World in Data](https://ourworldindata.org/co2-and-greenhouse-gas-emissions) | [World Bank Climate Change Knowledge Portal](https://climateknowledgeportal.worldbank.org/)")
