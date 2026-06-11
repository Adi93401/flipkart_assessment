"""
Page 3 — Delivery Log

Browse all POD records. Filter by AWB for quick lookup.
"""

import os
from datetime import datetime

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8001")

st.set_page_config(page_title="Delivery Log", page_icon="📋", layout="wide")
st.title("📋 Delivery Log")

# ── search by AWB ────────────────────────────────────────────────────────────
search_awb = st.text_input("🔎 Filter by AWB (leave blank to see all)").strip().upper()

if search_awb:
    with st.spinner(f"Fetching records for AWB {search_awb}…"):
        try:
            r = requests.get(f"{API}/api/deliveries/{search_awb}", timeout=10)
        except requests.RequestException as e:
            st.error(f"API error: {e}")
            st.stop()

    if r.status_code == 404:
        st.warning(f"No deliveries found for AWB **{search_awb}**.")
        st.stop()

    records = r.json()
    st.success(f"Found **{len(records)}** record(s) for AWB {search_awb}")

else:
    # ── paginated full list ──────────────────────────────────────────────────
    page  = st.number_input("Page", min_value=1, value=1, step=1)
    limit = st.select_slider("Rows per page", options=[25, 50, 100], value=50)

    with st.spinner("Loading deliveries…"):
        try:
            r = requests.get(
                f"{API}/api/deliveries",
                params={"page": page, "limit": limit},
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            st.error(f"API error: {e}")
            st.stop()

    data    = r.json()
    records = data.get("deliveries", [])
    st.info(
        f"**{data['total_count']:,}** total deliveries — "
        f"page {data['page']} of {data['total_pages']}"
    )

# ── render records ───────────────────────────────────────────────────────────
if not records:
    st.info("No records to display.")
    st.stop()

for rec in records:
    with st.expander(
        f"AWB: {rec['awb']}  ·  "
        f"{rec['driver_name']}  ·  "
        f"{rec['captured_at'][:19].replace('T', ' ')}",
        expanded=False,
    ):
        col1, col2 = st.columns([1, 2])
        col1.markdown(f"**Record ID:** {rec['id']}")
        col1.markdown(f"**AWB:** `{rec['awb']}`")
        col1.markdown(f"**Driver:** {rec['driver_name']}")
        col1.markdown(f"**Type:** {rec['media_type']}")
        if rec.get("notes"):
            col1.markdown(f"**Notes:** {rec['notes']}")
        col1.markdown(f"**Captured:** {rec['captured_at'][:19].replace('T', ' ')}")

        if rec["media_type"] == "image":
            col2.image(rec["media_url"], caption="Proof of delivery", use_container_width=True)
        else:
            col2.video(rec["media_url"])
            col2.markdown(f"[Open video ↗]({rec['media_url']})")
