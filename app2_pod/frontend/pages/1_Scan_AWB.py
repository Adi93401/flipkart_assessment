"""
Page 1 — Scan AWB

The driver points the camera at a barcode or QR code.
pyzbar decodes the AWB string from the captured frame.
The AWB is stored in session_state for Page 2 to consume.
"""

import os

import requests
import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode

API = os.getenv("API_URL", "http://localhost:8001")

st.set_page_config(page_title="Scan AWB", page_icon="📷", layout="centered")
st.title("📷 Scan AWB Barcode")

st.info(
    "Point the camera at the package barcode or QR code, "
    "or type the AWB manually below."
)

# ── camera capture ───────────────────────────────────────────────────────────
img_file = st.camera_input("Capture barcode / QR code")

awb_detected = None

if img_file:
    pil = Image.open(img_file)
    barcodes = decode(pil)

    if barcodes:
        awb_detected = barcodes[0].data.decode("utf-8").strip().upper()
        st.success(f"✅ AWB detected: **{awb_detected}**")
    else:
        st.warning("No barcode detected. Try better lighting or enter AWB manually.")

# ── manual fallback ──────────────────────────────────────────────────────────
manual_awb = st.text_input(
    "Or enter AWB manually",
    value=st.session_state.get("awb", ""),
    placeholder="e.g. 1Z999AA1012345678",
).strip().upper()

# Prefer camera-detected over manual
awb = awb_detected or manual_awb

if awb:
    st.session_state["awb"] = awb
    st.info(f"AWB set to: **{awb}**")

    # Verify against existing records (optional — informational only)
    try:
        r = requests.get(f"{API}/api/deliveries/{awb}", timeout=5)
        if r.status_code == 200:
            count = len(r.json())
            st.caption(f"ℹ️ {count} previous POD record(s) exist for this AWB.")
    except requests.RequestException:
        pass  # don't block the flow if API is slow

    if st.button("➡️ Continue to Capture Media", type="primary"):
        st.switch_page("pages/2_Capture_Media.py")
