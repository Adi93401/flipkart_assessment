"""
Page 2 — Product Verification (Warehouse Operator)

Flow:
  1. Operator enters / scans WID
  2. System fetches product details and shows EAN + dates + expiry status
  3. Operator takes a photo (optional)
  4. Photo is uploaded to Cloudinary via /upload-photo
  5. Verification event is logged via /log with operator identity
"""

import os
import time

import requests
import streamlit as st
from PIL import Image

API      = os.getenv("API_URL", "http://localhost:8000")
username = st.session_state.get("username", "")

st.set_page_config(page_title="Verify Product", page_icon="🔍", layout="centered")
st.title("🔍 Product Verification")

# ── operator guard ───────────────────────────────────────────────────────────
if not username:
    st.warning("⚠️ Set your name in the sidebar before verifying products.")
    st.stop()

st.caption(f"Operator: **{username}**")

# ── WID input ────────────────────────────────────────────────────────────────
st.subheader("Step 1 — Enter or scan WID")
wid = st.text_input("Warehouse ID (WID)", placeholder="e.g. WH-0001").strip()

# ── product lookup ───────────────────────────────────────────────────────────
if wid:
    with st.spinner("Looking up product…"):
        try:
            r = requests.get(f"{API}/api/verify/{wid}", timeout=10)
        except requests.RequestException as e:
            st.error(f"Could not reach API: {e}")
            st.stop()

    if r.status_code == 404:
        st.error(f"WID **{wid}** not found in the system.")
        st.stop()
    elif r.status_code != 200:
        st.error(f"Unexpected error: {r.text}")
        st.stop()

    p = r.json()

    st.divider()
    st.subheader("Step 2 — Review product details")

    col1, col2, col3 = st.columns(3)
    col1.metric("EAN", p["ean"])
    col2.metric("Manufactured", p["manufacturing_date"])
    col3.metric("Expires", p["expiry_date"])

    # Expiry status banner
    status = p.get("status", "ok")
    days   = p.get("days_to_expiry", 0)

    if status == "expired":
        st.error(f"🚨 EXPIRED — {abs(days)} days ago. Do NOT dispatch.")
    elif status == "expiring_soon":
        st.warning(f"⚠️ Expiring soon — {days} day(s) remaining.")
    else:
        st.success(f"✅ Good — expires in {days} day(s).")

    # ── photo capture ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Step 3 — Capture product photo (optional)")
    photo = st.camera_input("Take a photo of the physical item")

    photo_url = None
    if photo:
        st.image(photo, caption="Captured image", use_container_width=True)

        with st.spinner("Uploading photo…"):
            try:
                up = requests.post(
                    f"{API}/api/verify/{wid}/upload-photo",
                    files={"file": ("photo.jpg", photo.getvalue(), "image/jpeg")},
                    timeout=30,
                )
                up.raise_for_status()
                photo_url = up.json().get("photo_url")
                st.caption(f"📎 [View uploaded photo]({photo_url})")
            except requests.RequestException as e:
                st.warning(f"Photo upload failed (verification can still be logged): {e}")

    # ── log verification ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Step 4 — Log verification")

    if st.button("✅ Log Verification", type="primary"):
        payload = {"username": username, "photo_url": photo_url}
        try:
            lr = requests.post(
                f"{API}/api/verify/{wid}/log",
                json=payload,
                timeout=10,
            )
            lr.raise_for_status()
            result = lr.json()
            st.success(f"Verification logged — Log ID #{result['log_id']}")
        except requests.RequestException as e:
            st.error(f"Failed to log: {e}")
