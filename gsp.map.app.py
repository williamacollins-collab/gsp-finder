import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import Circle

# Page setup
st.set_page_config(page_title="UK GSP Fault Level Map", layout="wide")
st.title("⚡ UK Grid Supply Points (England & Wales)")
st.write("Visualisation of Grid Supply Points with 3-mile radius circles showing fault-level headroom status.")

# Upload CSV
uploaded_file = st.file_uploader("Upload GSP CSV file", type=["csv"])

# Default demo file
if uploaded_file is None:
    st.info("No file uploaded — using sample dataset.")
    csv_url = "https://raw.githubusercontent.com/databeta/gsp_locations_sample/main/gsp_locations_sample.csv"  # placeholder link
    try:
        df = pd.read_csv(csv_url)
    except:
        st.error("Unable to load the sample dataset. Please upload gsp_locations_sample.csv manually.")
        st.stop()
else:
    df = pd.read_csv(uploaded_file)

# Filters
dno_list = ["All"] + sorted(df["DNO"].unique().tolist())
status_list = ["All"] + sorted(df["Fault_Level_Status"].unique().tolist())

col1, col2 = st.columns(2)
with col1:
    selected_dno = st.selectbox("Filter by DNO", dno_list)
with col2:
    selected_status = st.selectbox("Filter by Fault Level Status", status_list)

# Apply filters
if selected_dno != "All":
    df = df[df["DNO"] == selected_dno]
if selected_status != "All":
    df = df[df["Fault_Level_Status"] == selected_status]

# Create map
m = folium.Map(location=[52.5, -1.5], zoom_start=7, tiles="cartodb positron")

# Color map for statuses
color_map = {
    "No Restriction": "green",
    "Restricted": "orange",
    "Zero Headroom": "red"
}

# Radius (3 miles ≈ 4828 m)
radius_m = 4828

# Add circles for each GSP
for _, row in df.iterrows():
    color = color_map.get(row["Fault_Level_Status"], "gray")
    popup_text = (f"<b>{row['GSP_Name']}</b><br>"
                  f"DNO: {row['DNO']}<br>"
                  f"Fault Level: {row['Fault_Level_Status']}<br>"
                  f"Headroom: {row['Fault_Level_Headroom_kA']} kA")
    Circle(
        location=[row["Latitude"], row["Longitude"]],
        radius=radius_m,
        color=color,
        fill=True,
        fill_opacity=0.4,
        popup=popup_text
    ).add_to(m)

# Display map
st_data = st_folium(m, width=1200, height=700)
