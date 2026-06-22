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
from datetime import datetime

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
username = st.session_state.get("username", "").strip() or "Unknown"

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
    selected_at = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f8fafc, #eef2ff); border: 1px solid #c7d2fe; border-radius: 16px; padding: 14px; margin-bottom: 12px;">
      <div><strong>📄 File selected</strong></div>
      <div><strong>Name:</strong> {uploaded.name}</div>
      <div><strong>Size:</strong> {uploaded.size:,} bytes</div>
      <div><strong>Selected at:</strong> {selected_at}</div>
      <div><strong>Logged in as:</strong> {username}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Start Import", type="primary"):
        # POST the file as a streamed upload to avoid loading 450 MB into memory
        with st.spinner("Uploading…"):
            try:
                resp = requests.post(
                    f"{API}/api/upload",
                    files={"file": (uploaded.name, uploaded, "text/csv")},
                    data={"username": username},
                    timeout=(30, 1200),
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        data   = resp.json()
        job_id = data["job_id"]
        st.success(f"Upload accepted — Job #{job_id} started in background for **{data.get('uploaded_by', username)}**.")

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

st.subheader("📚 Recent uploads")
try:
    recent_resp = requests.get(f"{API}/api/uploads", timeout=10)
    recent_resp.raise_for_status()
    recent_uploads = recent_resp.json()
except requests.RequestException:
    recent_uploads = []

if recent_uploads:
    display_rows = []
    for item in recent_uploads:
        created_at = item.get("created_at", "")
        if created_at:
            created_at = created_at.replace("T", " ").split(".")[0]
        display_rows.append({
            "File": item.get("filename", "-"),
            "Uploaded by": item.get("uploaded_by") or "Unknown",
            "Status": item.get("status", "-"),
            "Rows": item.get("total_rows", 0),
            "Inserted": item.get("inserted_rows", 0),
            "Created": created_at,
        })
    st.dataframe(display_rows, use_container_width=True, hide_index=True)
else:
    st.caption("No uploads have been recorded in the database yet.")
