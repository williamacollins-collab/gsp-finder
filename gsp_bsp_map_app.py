import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import FeatureGroup, LayerControl, Circle, CircleMarker, Marker, Icon


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="UK GSP & BSP Map", layout="wide")

st.title("⚡ UK Electricity Network Map – GSPs & BSPs")
st.write("Interactive map of Grid Supply Points (GSPs) and Bulk Supply Points (BSPs) in England & Wales.")


# ---------------------------------------------------------
# SIDEBAR – FILE UPLOADS
# ---------------------------------------------------------
st.sidebar.header("📁 Upload Your Data")

gsp_file = st.sidebar.file_uploader("Upload GSP CSV", type=["csv"])
bsp_file = st.sidebar.file_uploader("Upload BSP CSV (optional)", type=["csv"])


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
if gsp_file is None:
    st.warning("Please upload your GSP CSV file to continue.")
    st.stop()

gsp_df = pd.read_csv(gsp_file)

if bsp_file:
    bsp_df = pd.read_csv(bsp_file)
else:
    bsp_df = pd.DataFrame(columns=["BSP_Name", "DNO", "Latitude", "Longitude", "Voltage_kV"])


# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("🔍 Filters")

# GSP filters
dno_options = ["All"] + sorted(gsp_df["DNO"].unique().tolist())
status_options = ["All"] + sorted(gsp_df["Fault_Level_Status"].unique().tolist())

selected_dno = st.sidebar.selectbox("GSP — Filter by DNO", dno_options)
selected_status = st.sidebar.selectbox("GSP — Fault-Level Status", status_options)

if selected_dno != "All":
    gsp_df = gsp_df[gsp_df["DNO"] == selected_dno]

if selected_status != "All":
    gsp_df = gsp_df[gsp_df["Fault_Level_Status"] == selected_status]

# BSP toggles
show_bsp = st.sidebar.checkbox("Show BSPs", value=True)
bsp_as_circles = st.sidebar.checkbox("Show BSPs as circles instead of icons", value=False)


# ---------------------------------------------------------
# BASE MAP
# ---------------------------------------------------------
m = folium.Map(location=[52.5, -1.5], zoom_start=7, tiles="cartodb positron")

gsp_layer = FeatureGroup(name="GSPs", show=True)
bsp_layer = FeatureGroup(name="BSPs", show=show_bsp)


# ---------------------------------------------------------
# DRAW GSPs – 3-MILE RADIUS CIRCLES
# ---------------------------------------------------------
color_map = {
    "No Restriction": "green",
    "Restricted": "orange",
    "Zero Headroom": "red"
}

radius_m = 4828  # 3 miles in metres

for _, row in gsp_df.iterrows():
    color = color_map.get(row["Fault_Level_Status"], "gray")

    popup = (
        f"<b>{row['GSP_Name']}</b><br>"
        f"DNO: {row['DNO']}<br>"
        f"Status: {row['Fault_Level_Status']}<br>"
        f"Headroom: {row['Fault_Level_Headroom_kA']} kA"
    )

    Circle(
        location=[row["Latitude"], row["Longitude"]],
        radius=radius_m,
        color=color,
        fill=True,
        fill_opacity=0.35,
        popup=popup
    ).add_to(gsp_layer)


# ---------------------------------------------------------
# DRAW BSPs – ICONS OR CIRCLES
# ---------------------------------------------------------
for _, row in bsp_df.iterrows():

    popup = (
        f"<b>{row['BSP_Name']}</b><br>"
        f"DNO: {row['DNO']}<br>"
        f"Voltage: {row['Voltage_kV']} kV"
    )

    if bsp_as_circles:
        CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=8,
            color="blue",
            fill=True,
            fill_opacity=0.9,
            popup=popup
        ).add_to(bsp_layer)
    else:
        Marker(
            location=[row["Latitude"], row["Longitude"]],
            icon=Icon(color="blue", icon="bolt", prefix="fa"),
            popup=popup
        ).add_to(bsp_layer)


# ---------------------------------------------------------
# ADD LAYERS
# ---------------------------------------------------------
gsp_layer.add_to(m)
bsp_layer.add_to(m)

LayerControl(collapsed=False).add_to(m)


# ---------------------------------------------------------
# RENDER MAP
# ---------------------------------------------------------
st_folium(m, width=1200, height=750)
