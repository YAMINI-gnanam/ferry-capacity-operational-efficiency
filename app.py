import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Ferry Operational Efficiency",
    page_icon="⛴️",
    layout="wide"
)

st.title("⛴️ Ferry Capacity Utilization & Operational Efficiency")
st.caption("Toronto Island Ferry Ticket Activity | 2015–2025")

# Load the analyzed dataset
DATA_FILE = Path(__file__).parent / "ferry_analysis_2015_2025.csv"

@st.cache_data
def load_data(file_path):
    data = pd.read_csv(file_path, parse_dates=["Timestamp"])
    return data.sort_values("Timestamp")

try:
    df = load_data(DATA_FILE)
except Exception as error:
    st.error(f"Could not load the dataset: {error}")
    st.info("Ensure the CSV file is in the same folder as app.py.")
    st.stop()

# Ensure required features are available
if "Total Activity Load" not in df.columns:
    df["Total Activity Load"] = (
        df["Sales Count"].fillna(0) + df["Redemption Count"].fillna(0)
    )

df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
df = df.dropna(subset=["Timestamp"])
df["Year"] = df["Timestamp"].dt.year
df["Month"] = df["Timestamp"].dt.month
df["Hour"] = df["Timestamp"].dt.hour
df["Day"] = df["Timestamp"].dt.day_name()

if "OLI" not in df.columns:
    minimum = df["Total Activity Load"].min()
    maximum = df["Total Activity Load"].max()
    df["OLI"] = (
        (df["Total Activity Load"] - minimum) / (maximum - minimum) * 100
        if maximum > minimum else 0
    )

# Sidebar filters
st.sidebar.header("Dashboard Filters")
min_date = df["Timestamp"].min().date()
max_date = df["Timestamp"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = df[
        (df["Timestamp"].dt.date >= start_date) &
        (df["Timestamp"].dt.date <= end_date)
    ].copy()
else:
    filtered = df.copy()

season_choice = st.sidebar.selectbox(
    "Season",
    ["All", "Summer (May–August)", "Off-season"]
)

if season_choice == "Summer (May–August)":
    filtered = filtered[filtered["Month"].isin([5, 6, 7, 8])]
elif season_choice == "Off-season":
    filtered = filtered[~filtered["Month"].isin([5, 6, 7, 8])]

granularity = st.sidebar.selectbox(
    "Time aggregation",
    ["15-minute", "Hourly", "Daily"]
)

# Aggregate the selected time resolution
if granularity == "Hourly":
    chart_data = (
        filtered.set_index("Timestamp")
        .resample("h")
        .agg({
            "Sales Count": "sum",
            "Redemption Count": "sum",
            "Total Activity Load": "sum",
            "OLI": "mean"
        }).dropna().reset_index()
    )
elif granularity == "Daily":
    chart_data = (
        filtered.set_index("Timestamp")
        .resample("D")
        .agg({
            "Sales Count": "sum",
            "Redemption Count": "sum",
            "Total Activity Load": "sum",
            "OLI": "mean"
        }).dropna().reset_index()
    )
else:
    chart_data = filtered.copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

# KPI summary
total_sales = filtered["Sales Count"].sum()
total_redemptions = filtered["Redemption Count"].sum()
average_activity = filtered["Total Activity Load"].mean()
peak_threshold = filtered["Total Activity Load"].quantile(0.90)
idle_threshold = filtered["Total Activity Load"].quantile(0.10)

peak_percent = (
    filtered["Total Activity Load"].ge(peak_threshold).mean() * 100
)
idle_percent = (
    filtered["Total Activity Load"].le(idle_threshold).mean() * 100
)
variability = filtered["Total Activity Load"].std()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Tickets Sold", f"{total_sales:,.0f}")
c2.metric("Total Tickets Redeemed", f"{total_redemptions:,.0f}")
c3.metric("Average Activity / Interval", f"{average_activity:,.2f}")
c4.metric("Peak Activity Intervals", f"{peak_percent:.1f}%")

c5, c6, c7 = st.columns(3)
c5.metric("Low-Activity Intervals", f"{idle_percent:.1f}%")
c6.metric("Operational Variability (Std. Dev.)",
          f"{variability:,.2f}" if pd.notna(variability) else "N/A")
c7.metric("90th Percentile Activity", f"{peak_threshold:,.0f}")

st.info(
    "Interpretation note: ticket activity is a proxy for operational demand. "
    "Actual vessel capacity utilization requires passenger occupancy and "
    "vessel-capacity data."
)

# Activity timeline
st.subheader(f"Activity Timeline ({granularity})")
timeline = px.line(
    chart_data,
    x="Timestamp",
    y="Total Activity Load",
    title="Total Ticket Activity Over Time",
    labels={"Total Activity Load": "Sales + Redemptions"}
)
st.plotly_chart(timeline, use_container_width=True)

# Monthly comparison
st.subheader("Monthly Activity Comparison")
monthly = (
    filtered.groupby("Month")["Total Activity Load"]
    .mean().reindex(range(1, 13))
    .rename("Average Activity").reset_index()
)
monthly["Month Name"] = pd.to_datetime(
    monthly["Month"], format="%m"
).dt.month_name()

fig_month = px.bar(
    monthly,
    x="Month Name",
    y="Average Activity",
    title="Average Activity by Month"
)
st.plotly_chart(fig_month, use_container_width=True)

# Weekday comparison
st.subheader("Weekday Activity")
weekday_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]
weekday = (
    filtered.groupby("Day")["Total Activity Load"]
    .mean().reindex(weekday_order)
    .rename("Average Activity").reset_index()
)
fig_weekday = px.bar(
    weekday,
    x="Day",
    y="Average Activity",
    title="Average Ticket Activity by Day of Week"
)
st.plotly_chart(fig_weekday, use_container_width=True)

# Seasonal comparison
st.subheader("Summer vs Off-season")
season_data = filtered.copy()
season_data["Season Group"] = season_data["Month"].apply(
    lambda month: "Summer" if month in [5, 6, 7, 8] else "Off-season"
)
seasonal = (
    season_data.groupby("Season Group")["Total Activity Load"]
    .mean().reset_index(name="Average Activity")
)
fig_season = px.bar(
    seasonal,
    x="Season Group",
    y="Average Activity",
    color="Season Group",
    title="Average Activity: Summer vs Off-season"
)
st.plotly_chart(fig_season, use_container_width=True)

# Peak and low activity comparison
st.subheader("Congestion and Idle-Activity Analysis")
status_data = filtered.copy()
status_data["Activity Status"] = "Normal"
status_data.loc[
    status_data["Total Activity Load"] >= peak_threshold,
    "Activity Status"
] = "Peak activity"
status_data.loc[
    status_data["Total Activity Load"] <= idle_threshold,
    "Activity Status"
] = "Low activity"

status_counts = (
    status_data["Activity Status"].value_counts()
    .rename_axis("Status").reset_index(name="Intervals")
)
fig_status = px.bar(
    status_counts,
    x="Status",
    y="Intervals",
    color="Status",
    title="Activity Interval Classification"
)
st.plotly_chart(fig_status, use_container_width=True)

# Hour-of-day heatmap
st.subheader("Activity Heatmap: Day vs Hour")
heat_data = (
    filtered.pivot_table(
        index="Day",
        columns="Hour",
        values="Total Activity Load",
        aggfunc="mean"
    ).reindex(weekday_order)
)
fig_heat = px.imshow(
    heat_data,
    aspect="auto",
    color_continuous_scale="YlOrRd",
    labels={
        "x": "Hour of Day",
        "y": "Day of Week",
        "color": "Average Activity"
    },
    title="Average Activity by Weekday and Hour"
)
st.plotly_chart(fig_heat, use_container_width=True)

# Yearly trend
st.subheader("Yearly Activity Trend")
yearly = (
    filtered.groupby("Year")["Total Activity Load"]
    .sum().reset_index(name="Total Activity")
)
fig_year = px.line(
    yearly,
    x="Year",
    y="Total Activity",
    markers=True,
    title="Annual Total Ticket Activity"
)
st.plotly_chart(fig_year, use_container_width=True)

# Threshold alerts
st.subheader("Activity Threshold Alerts")
alert_threshold = st.slider(
    "High activity alert threshold",
    min_value=0,
    max_value=max(1, int(filtered["Total Activity Load"].max())),
    value=max(1, int(peak_threshold)),
)
alerts = filtered[filtered["Total Activity Load"] >= alert_threshold]

if not alerts.empty:
    st.warning(
        f"{len(alerts):,} intervals meet or exceed the selected "
        "activity threshold."
    )
    st.dataframe(
        alerts[["Timestamp", "Sales Count", "Redemption Count",
                "Total Activity Load"]].head(100),
        use_container_width=True
    )
else:
    st.success("No intervals meet the selected threshold.")

# Download filtered data
st.subheader("Export Filtered Data")
st.download_button(
    "Download filtered CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="ferry_filtered_analysis.csv",
    mime="text/csv"
)

st.caption(
    "Ferry Capacity Utilization & Operational Efficiency Analytics System | "
    "Historical ticket activity analysis, 2015–2025"
)