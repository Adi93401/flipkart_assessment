"""
App 2 — Proof of Delivery (POD)
Streamlit entry point
"""

import streamlit as st

st.set_page_config(
    page_title="Proof of Delivery App",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 Proof of Delivery App")
st.markdown("""
Use the sidebar to navigate.

| Page | Purpose |
|------|---------|
| 📷 Scan AWB | Scan a package barcode / QR code to get the AWB |
| 📸 Capture Media | Take a photo or upload a video as proof of delivery |
| 📋 Delivery Log | Browse all past POD records |
""")

with st.sidebar:
    st.header("🚗 Driver")
    name = st.text_input("Driver name / ID", value=st.session_state.get("driver_name", ""))
    if name:
        st.session_state["driver_name"] = name
        st.success(f"Logged in as **{name}**")
    else:
        st.warning("Enter your name before submitting a delivery.")
