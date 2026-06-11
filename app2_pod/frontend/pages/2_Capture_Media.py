"""
Page 2 — Capture & Submit POD

Driver can:
  • Take a photo via the built-in camera
  • OR upload a video file (Streamlit camera_input doesn't support video recording)

On submit:
  1. POST /api/media/upload  → Cloudinary URL
  2. POST /api/deliveries    → persist the delivery record
"""

import os

import requests
import streamlit as st

API         = os.getenv("API_URL", "http://localhost:8001")
awb         = st.session_state.get("awb", "")
driver_name = st.session_state.get("driver_name", "")

st.set_page_config(page_title="Capture POD Media", page_icon="📸", layout="centered")
st.title("📸 Capture Proof of Delivery")

# ── guards ───────────────────────────────────────────────────────────────────
if not driver_name:
    st.warning("Set your driver name in the sidebar first.")
    st.stop()

if not awb:
    st.warning("No AWB selected. Go to **Scan AWB** first.")
    if st.button("← Go to Scan AWB"):
        st.switch_page("pages/1_Scan_AWB.py")
    st.stop()

st.info(f"AWB: **{awb}**  ·  Driver: **{driver_name}**")
st.divider()

# ── media choice ─────────────────────────────────────────────────────────────
media_type_choice = st.radio(
    "Media type", ["📷 Photo", "🎥 Video"], horizontal=True
)

media_bytes = None
mime_type   = None
media_type  = None

if media_type_choice == "📷 Photo":
    photo = st.camera_input("Take delivery photo")
    if photo:
        media_bytes = photo.getvalue()
        mime_type   = "image/jpeg"
        media_type  = "image"
        st.image(photo, caption="Preview", use_container_width=True)
else:
    video = st.file_uploader(
        "Upload delivery video (MP4, MOV, WEBM — max 200 MB)",
        type=["mp4", "mov", "webm"],
    )
    if video:
        media_bytes = video.read()
        mime_type   = video.type or "video/mp4"
        media_type  = "video"
        st.video(video)

notes = st.text_area("Delivery notes (optional)", placeholder="e.g. Left with receptionist, Unit 4B")

# ── submit ───────────────────────────────────────────────────────────────────
if media_bytes and st.button("✅ Submit POD", type="primary"):
    with st.spinner("Uploading media to cloud…"):
        try:
            up = requests.post(
                f"{API}/api/media/upload",
                files={"file": ("pod_media", media_bytes, mime_type)},
                timeout=120,   # videos can be large
            )
            up.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Media upload failed: {e}")
            st.stop()

    cloud_data = up.json()
    media_url  = cloud_data["media_url"]

    with st.spinner("Saving delivery record…"):
        try:
            dr = requests.post(
                f"{API}/api/deliveries",
                json={
                    "awb":         awb,
                    "driver_name": driver_name,
                    "media_url":   media_url,
                    "media_type":  media_type,
                    "notes":       notes or None,
                },
                timeout=15,
            )
            dr.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Failed to save delivery: {e}")
            st.stop()

    record = dr.json()
    st.success(f"🎉 POD submitted — Record ID #{record['id']}")
    st.markdown(f"📎 [View media]({media_url})")

    # Clear AWB so driver starts fresh for next package
    del st.session_state["awb"]

    if st.button("📷 Scan next package"):
        st.switch_page("pages/1_Scan_AWB.py")
