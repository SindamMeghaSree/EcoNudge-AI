import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime
import altair as alt

# =====================================================
# DATA GENERATION (SIMULATED LIVE DATA)
# =====================================================
def generate_smart_hourly_data():
    locations = ["Hostel A", "Hostel B", "Hostel C", "Lab 1"]
    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    rows = []

    for hour_offset in range(24):  # last 24 hours
        ts = now - pd.Timedelta(hours=23 - hour_offset)
        hour = ts.hour

        for loc in locations:

            # ---- ELECTRICITY PATTERNS ----
            if loc == "Lab 1":
                electricity = random.randint(260, 320)  # steady high
            else:
                if 6 <= hour <= 9:        # morning peak
                    electricity = random.randint(300, 380)
                elif 18 <= hour <= 22:    # evening peak
                    electricity = random.randint(350, 480)
                else:
                    electricity = random.randint(150, 250)

            # Inject clear peak for demo
            if loc == "Hostel B" and hour == 20:
                electricity = 490  # 🔥 visible peak

            # ---- WATER PATTERNS ----
            if loc == "Lab 1":
                water = random.randint(900, 1400)
            else:
                if 6 <= hour <= 9 or 18 <= hour <= 21:
                    water = random.randint(4500, 6500)
                else:
                    water = random.randint(2500, 3500)

            # Inject leakage scenario
            if loc == "Hostel C" and hour == 14:
                water = 9200  # 💧 leakage spike

            rows.append({
                "timestamp": ts,
                "location": loc,
                "electricity_kwh": electricity,
                "water_liters": water
            })

    return pd.DataFrame(rows)

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="EcoNudge AI", layout="wide")

# =====================================================
# STYLES
# =====================================================
st.markdown("""
<style>
.stApp { background-color:#f5f7fa; color:#2c3e50; font-family:Inter,Segoe UI,sans-serif; }

.eco-header {
    background: linear-gradient(90deg, #2ecc71, #27ae60);
    padding: 18px 22px;
    border-radius: 14px;
    color: white;
    margin-bottom: 24px;
    text-align:center;
}

details { border-radius:10px; margin-bottom:14px; overflow:hidden; }
details summary { cursor:pointer; padding:14px; font-size:16px; font-weight:600; }

details.high summary {
    background:rgba(231,76,60,0.20);
    color:#e74c3c;
    border-left:6px solid #e74c3c;
}
details.medium summary {
    background:rgba(243,156,18,0.20);
    color:#f39c12;
    border-left:6px solid #f39c12;
}
details.water-critical summary {
    background:rgba(41,128,185,0.25);
    color:#1f4e79;
    border-left:6px solid #1f4e79;
}
details.water-warning summary {
    background:rgba(52,152,219,0.18);
    color:#2c7fb8;
    border-left:6px solid #2c7fb8;
}

.details-box {
    background:#ffffff;
    border:1px solid #e1e5ea;
    border-radius:6px;
    padding:14px 16px;
    margin-top:10px;
    font-size:14px;
}
.details-row { margin-bottom:6px; }
</style>
""", unsafe_allow_html=True)


# =====================================================
# HEADER
# =====================================================
st.markdown("""
<div class="eco-header">
    <h2 style="font-size:34px;">🌱 EcoNudge AI</h2>
    <p style="font-size:18px;">
        Smart Campus Energy & Water Intelligence Dashboard
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<h3 style="text-align:center; font-size:20px; font-weight:600; margin-bottom:20px;">
🧠 AI Insights & Actionable Nudges
</h3>
""", unsafe_allow_html=True)

# =====================================================
# LOAD & CLEAN DATA
# =====================================================
df = pd.read_csv("data/energy_water_usage.csv")

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["electricity_kwh"] = pd.to_numeric(df["electricity_kwh"], errors="coerce")
df["water_liters"] = pd.to_numeric(df["water_liters"], errors="coerce")

df = df.dropna(subset=["timestamp", "electricity_kwh", "water_liters"])

# =====================================================
# APPEND LIVE DATA FIRST
# =====================================================
# =====================================================
# GENERATE MEANINGFUL DEMO DATA (ONCE)
# =====================================================

if len(df) < 50:  # prevents regenerating every rerun
    df = generate_smart_hourly_data()
    #df.to_csv("data/energy_water_usage.csv", index=False)

# =====================================================
# HOURLY TREND (FORCED CONTINUOUS LINES)
# =====================================================

# Last 24 hours window
end_time = df["timestamp"].max().floor("H")
start_time = end_time - pd.Timedelta(hours=23)

time_index = pd.date_range(start=start_time, end=end_time, freq="H")

locations = df["location"].unique()

rows = []

for loc in locations:
    df_loc = df[df["location"] == loc].copy()

    df_loc["timestamp"] = df_loc["timestamp"].dt.floor("H")

    df_loc = (
        df_loc
        .groupby("timestamp")[["electricity_kwh", "water_liters"]]
        .mean()
        .reindex(time_index)
        .ffill()   # fill missing hours
        .reset_index()
        .rename(columns={"index": "timestamp"})
    )

    df_loc["location"] = loc
    rows.append(df_loc)

df_hourly = pd.concat(rows, ignore_index=True)


# =====================================================
# DAILY SUMMARY (LATEST DAY)
# =====================================================
df_daily = (
    df
    .assign(date=df["timestamp"].dt.date)
    .groupby(["date", "location"], as_index=False)
    .agg(
        avg_electricity_kwh=("electricity_kwh", "mean"),
        peak_electricity_kwh=("electricity_kwh", "max"),
        avg_water_liters=("water_liters", "mean"),
        peak_water_liters=("water_liters", "max")
    )
)

latest_date = df_daily["date"].max()
df_daily_latest = df_daily[df_daily["date"] == latest_date]

# =====================================================
# ALERT CLASSIFICATION
# =====================================================
def classify_alert(row):
    if row["electricity_kwh"] > 450:
        return "High Electricity"
    elif row["electricity_kwh"] > 300:
        return "Medium Electricity"
    elif row["water_liters"] > 8000:
        return "Water Leakage"
    elif row["water_liters"] > 6000:
        return "Water Overuse"
    return "Normal"

df["alert_type"] = df.apply(classify_alert, axis=1)

# =====================================================
# ALERT REDUCTION (MINIMAL & IMPACTFUL)
# =====================================================
cutoff = df["timestamp"].max() - pd.Timedelta(hours=24)
df_alerts = df[(df["timestamp"] >= cutoff) & (df["alert_type"] != "Normal")]
# =====================================================
# A) CAMPUS SUSTAINABILITY SCORE (LOGIC)
# =====================================================
def compute_campus_score(df_alerts):
    score = 100

    score -= (df_alerts["alert_type"] == "High Electricity").sum() * 6
    score -= (df_alerts["alert_type"] == "Water Leakage").sum() * 8
    score -= (df_alerts["alert_type"] == "Medium Electricity").sum() * 3
    score -= (df_alerts["alert_type"] == "Water Overuse").sum() * 4

    return max(0, min(100, score))

campus_score = compute_campus_score(df_alerts)

# =====================================================
# A) CAMPUS SUSTAINABILITY SCORE (UI)
# =====================================================
st.markdown(
    '<h3 style="text-align:center; font-size:22px; font-weight:700;">🏫 Campus Sustainability Score</h3>',
    unsafe_allow_html=True
)
campus_score = max(campus_score, 45)
if campus_score >= 80:
    color, label = "#2ecc71", "Excellent 🌱"
elif campus_score >= 50:
    color, label = "#f1c40f", "Moderate ⚠️"
else:
    color, label = "#da7aeb", "Minimal ⚠️"
#🚨
st.markdown(
    f"""
    <div style="background:{color}; color:white;
                padding:20px; border-radius:14px;
                text-align:center; font-size:26px;
                font-weight:800; margin-bottom:25px;">
        {campus_score} / 100<br>
        <span style="font-size:18px;">{label}</span>
    </div>
    """,
    unsafe_allow_html=True
)
severity_rank = {
    "High Electricity": 1,
    "Water Leakage": 2,
    "Medium Electricity": 3,
    "Water Overuse": 4
}

df_alerts["severity"] = df_alerts["alert_type"].map(severity_rank)

df_alerts_minimal = (
    df_alerts
    .sort_values(["severity", "timestamp"], ascending=[True, False])
    .groupby(["location", "alert_type"])
    .head(1)
    .head(8)
)

# Alert summary (for bar chart)
df_alert_summary = (
    df_alerts
    .groupby("alert_type")
    .size()
    .reset_index(name="count")
)

# =====================================================
# TABS
# =====================================================
tab_all, tab_high, tab_med, tab_leak, tab_over = st.tabs([
    "📊 All Alerts",
    "🔴⚡ High Electricity usage",
    "🟠⚡ Medium Electricity usage",
    "🔵💧 Water Leak",
    "🔵💧 Water Overuse"
])

# =====================================================
# ALERT RENDERING (RICH, ORIGINAL STYLE)
# =====================================================
def show_alerts(filter_key):
    for _, row in df_alerts_minimal.iterrows():
        

        # ---------------- HIGH ELECTRICITY ----------------
        if row["alert_type"] == "High Electricity" and filter_key in ["All Alerts", "High Electricity usage"]:
            css = "high"
            st.markdown(f"""
            <details class="{css}">
                <summary>🔴⚡ High electricity usage at {row['location']} ({row['electricity_kwh']} kWh)</summary>
                <div class="details-box">
                    <div class="details-row"><b>Location:</b> {row['location']}</div>
                    <div class="details-row"><b>Timestamp:</b> {row['timestamp']}</div>
                    <div class="details-row"><b>Electricity Usage:</b> {row['electricity_kwh']} kWh</div>
                    <div class="details-row" style="margin-top:8px;">
                        <b>Recommended Action:</b> Immediate shutdown of unused equipment.
                    </div>
                </div>
            </details>
            """, unsafe_allow_html=True)

        # ---------------- MEDIUM ELECTRICITY ----------------
        elif row["alert_type"] == "Medium Electricity" and filter_key in ["All Alerts", "Medium Electricity usage"]:
            css = "medium"
            st.markdown(f"""
            <details class="{css}">
                <summary>🟠⚡ Elevated electricity usage at {row['location']} ({row['electricity_kwh']} kWh)</summary>
                <div class="details-box">
                    <div class="details-row"><b>Location:</b> {row['location']}</div>
                    <div class="details-row"><b>Timestamp:</b> {row['timestamp']}</div>
                    <div class="details-row"><b>Electricity Usage:</b> {row['electricity_kwh']} kWh</div>
                    <div class="details-row" style="margin-top:8px;">
                        <b>Recommended Action:</b> Turn off non-essential devices.
                    </div>
                </div>
            </details>
            """, unsafe_allow_html=True)

        # ---------------- WATER LEAKAGE ----------------
        elif row["alert_type"] == "Water Leakage" and filter_key in ["All Alerts", "Water Leak"]:
            css = "water-critical"
            st.markdown(f"""
            <details class="{css}">
                <summary>🔵💧 Possible water leakage at {row['location']} ({row['water_liters']} L)</summary>
                <div class="details-box">
                    <div class="details-row"><b>Location:</b> {row['location']}</div>
                    <div class="details-row"><b>Timestamp:</b> {row['timestamp']}</div>
                    <div class="details-row"><b>Water Usage:</b> {row['water_liters']} liters</div>
                    <div class="details-row" style="margin-top:8px;">
                        <b>Recommended Action:</b> Immediate pipeline inspection.
                    </div>
                </div>
            </details>
            """, unsafe_allow_html=True)

        # ---------------- WATER OVERUSE ----------------
        elif row["alert_type"] == "Water Overuse" and filter_key in ["All Alerts", "Water Overuse"]:
            css = "water-warning"
            st.markdown(f"""
            <details class="{css}">
                <summary>🔵💧 High water usage at {row['location']} ({row['water_liters']} L)</summary>
                <div class="details-box">
                    <div class="details-row"><b>Location:</b> {row['location']}</div>
                    <div class="details-row"><b>Timestamp:</b> {row['timestamp']}</div>
                    <div class="details-row"><b>Water Usage:</b> {row['water_liters']} liters</div>
                    <div class="details-row" style="margin-top:8px;">
                        <b>Recommended Action:</b> Monitor usage and reduce wastage.
                    </div>
                </div>
            </details>
            """, unsafe_allow_html=True)

with tab_all: show_alerts("All Alerts")
with tab_high: show_alerts("High Electricity usage")
with tab_med: show_alerts("Medium Electricity usage")
with tab_leak: show_alerts("Water Leak")
with tab_over: show_alerts("Water Overuse")

# =====================================================
# GRAPHS (MINIMAL & IMPACTFUL)
# =====================================================


# ---- Electricity Usage Trend (Jagged, original style) ----
st.markdown(
    '<h3 style="text-align:center; font-size:18px; font-weight:600; margin-bottom:20px;">Electricity Usage Trend (Hourly)</h3>',
    unsafe_allow_html=True
)
chart_elec_trend = alt.Chart(df_hourly).mark_line(strokeWidth=2).encode(
    x=alt.X('timestamp:T', title=''),
    y=alt.Y('electricity_kwh:Q', title=''),
    color=alt.Color('location:N', legend=alt.Legend(title='', orient='bottom'))
).properties(
    width='container',
    height=300
).configure_view(
    strokeWidth=0,
    fill="#ffffff"
).configure_axis(
    grid=False,
    domain=False,
    ticks=False,
    labelFontSize=12
)
st.altair_chart(chart_elec_trend, use_container_width=True)

# ---- Water Usage Trend (Jagged, original style) ----
st.markdown(
    '<h3 style="text-align:center; font-size:18px; font-weight:600; margin-bottom:20px;">Water Usage Trend (Hourly)</h3>',
    unsafe_allow_html=True
)
chart_water_trend = alt.Chart(df_hourly).mark_line(strokeWidth=2).encode(
    x=alt.X('timestamp:T', title=''),
    y=alt.Y('water_liters:Q', title=''),
    color=alt.Color('location:N', legend=alt.Legend(title='', orient='bottom'))
).properties(
    width='container',
    height=300
).configure_view(
    strokeWidth=0,
    fill="#ffffff"
).configure_axis(
    grid=False,
    domain=False,
    ticks=False,
    labelFontSize=12
)
st.altair_chart(chart_water_trend, use_container_width=True)



# ---- Peak Electricity Consumption ----

st.markdown(
    '<h3 style="text-align:center; font-size:20px; font-weight:600; margin-bottom:20px;">Peak Electricity Consumption by Location</h3>',
    unsafe_allow_html=True
)

chart_elec = alt.Chart(df_daily_latest).mark_bar(size=20, color="#e74c3c").encode(
    x=alt.X('location:N', title=''),
    y=alt.Y('peak_electricity_kwh:Q', title='')
).configure_view(
    strokeWidth=0,        # remove border around chart
    fill="#f5f7fa"        # light background color
).configure_axis(
    grid=False,           # remove horizontal grid lines
    domain=False,         # remove axis line
    ticks=False,          # remove ticks
    labelFontSize=12
)

st.altair_chart(chart_elec, use_container_width=True)

# ---- Peak Water Consumption ----
st.markdown(
    '<h3 style="text-align:center; font-size:20px; font-weight:600; margin-bottom:20px;">Peak Water Consumption by Location</h3>',
    unsafe_allow_html=True
)
chart_water = alt.Chart(df_daily_latest).mark_bar(size=20, color="#3498db").encode(
    x=alt.X('location:N', title=''),
    y=alt.Y('peak_water_liters:Q', title='')
).configure_view(
    strokeWidth=0,
    fill="#f5f7fa"
).configure_axis(
    grid=False,
    domain=False,
    ticks=False,
    labelFontSize=12
)
st.altair_chart(chart_water, use_container_width=True)

import altair as alt
import streamlit as st

# ---- Alerts Count ----
st.markdown(
    '<h3 style="text-align:center; font-size:20px; font-weight:600; margin-bottom:15px;">Alert Distribution (AI Insights)</h3>',
    unsafe_allow_html=True
)

chart_alerts = alt.Chart(df_alert_summary).mark_bar(size=20, color="#f39c12").encode(
    x=alt.X('alert_type:N', title=''),
    y=alt.Y('count:Q', title=''),
    tooltip=['alert_type', 'count']
).properties(
    width='container',
    height=250
).configure_view(
    strokeWidth=0,   # remove border
    fill="#ffffff"   # white background
).configure_axis(
    grid=False,
    domain=False,
    ticks=False,
    labelFontSize=12
)

st.altair_chart(chart_alerts, use_container_width=True)
# =====================================================
# IMPACT ESTIMATOR
# =====================================================
st.write("### Sustainability Impact & Savings Estimator")
reduction = st.slider("Assumed Reduction (%)", 0, 30, 10)

st.markdown(
    f"""
    <div style="background-color:#28a745; color:white; padding:15px; border-radius:8px;">
        💰 Estimated Annual Cost Savings: ₹{reduction * 1200} <br>
        🌱 Estimated CO₂ Reduction: {reduction * 55} kg/year
    </div>
    """,
    unsafe_allow_html=True
)

time.sleep(10)
st.rerun()