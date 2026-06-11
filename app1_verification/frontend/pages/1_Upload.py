"""
Page 1 — Bulk CSV Upload (Warehouse Manager)

Flow:
  1. Manager uploads CSV
  2. POST /api/upload  →  returns job_id immediately
  3. UI polls GET /api/jobs/{job_id} every second and shows progress bar
  4. On completion, shows inserted / duplicate counts
"""

import os
import time

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Upload Products", page_icon="📤", layout="centered")
st.title("📤 Bulk Product Upload")
st.caption("Import bulk CSVs with a smooth, guided workflow.")

st.markdown("""
<div style="background: linear-gradient(135deg, #eff6ff, #f8fafc); border: 1px solid #bfdbfe; border-radius: 16px; padding: 14px;">
  <strong>Tip:</strong> Use the sample template below to make sure your file matches the required format.
</div>
""", unsafe_allow_html=True)

# ── sample download ──────────────────────────────────────────────────────────
sample_csv = "WID,EAN,Manufacturing_Date,Expiry_Date\nWH-0001,1234567890123,2023-01-15,2025-01-15\nWH-0002,9876543210987,2023-03-20,2024-12-31\n"
st.download_button("⬇️ Download sample CSV", sample_csv, "sample_products.csv", "text/csv")

st.divider()

uploaded = st.file_uploader("Choose CSV file", type=["csv"], help="Upload a CSV up to 500 MB.")

if uploaded:
    st.info(f"📁 File selected: **{uploaded.name}** — **{uploaded.size:,} bytes**")

    if st.button("🚀 Start Import", type="primary"):
        # POST the file as a streamed upload to avoid loading 450 MB into memory
        with st.spinner("Uploading…"):
            try:
                resp = requests.post(
                    f"{API}/api/upload",
                    files={"file": (uploaded.name, uploaded, "text/csv")},
                    timeout=(30, 1200),
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        data   = resp.json()
        job_id = data["job_id"]
        st.success(f"Upload accepted — Job #{job_id} started in background.")

        # ── live progress bar ────────────────────────────────────────────────
        progress_bar = st.progress(0, text="Processing…")
        status_box   = st.empty()
        stats_cols   = st.columns(3)

        while True:
            try:
                job = requests.get(f"{API}/api/jobs/{job_id}", timeout=10).json()
            except requests.RequestException:
                time.sleep(1)
                continue

            pct  = job.get("progress_pct", 0) / 100
            stat = job.get("status", "pending")

            progress_bar.progress(
                min(pct, 1.0),
                text=f"{job.get('progress_pct', 0):.1f}% — {stat}",
            )
            stats_cols[0].metric("Processed", f"{job.get('processed_rows', 0):,}")
            stats_cols[1].metric("Inserted",  f"{job.get('inserted_rows', 0):,}")
            stats_cols[2].metric("Duplicates",f"{job.get('duplicate_rows', 0):,}")

            if stat == "done":
                progress_bar.progress(1.0, text="✅ Import complete!")
                st.balloons()
                break
            elif stat == "failed":
                st.error(f"Import failed: {job.get('error_message')}")
                break

            time.sleep(1)
