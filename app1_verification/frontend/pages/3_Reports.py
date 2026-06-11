"""
Page 3 — Verification Reports (QA Manager)

Features:
  • Date-range picker
  • Paginated table (100 rows per page by default)
  • CSV export of the full result set via re-fetching all pages
  • Expiry-status colour coding
"""

import os
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Verification Reports", page_icon="📊", layout="wide")
st.title("📊 Verification Reports")

# ── date range selector ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)
start = col1.date_input("From", value=date.today() - timedelta(days=30))
end   = col2.date_input("To",   value=date.today())

col3, col4 = st.columns([1, 3])
page  = col3.number_input("Page", min_value=1, value=1, step=1)
limit = col4.select_slider("Rows per page", options=[25, 50, 100, 250, 500], value=100)

if start > end:
    st.error("'From' date must be before 'To' date.")
    st.stop()

# ── fetch page ───────────────────────────────────────────────────────────────
if st.button("🔍 Generate Report", type="primary"):
    with st.spinner("Fetching report…"):
        try:
            r = requests.get(
                f"{API}/api/report",
                params={"start": start, "end": end, "page": page, "limit": limit},
                timeout=30,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            st.error(f"API error: {e}")
            st.stop()

    data = r.json()
    logs = data.get("logs", [])

    st.info(
        f"**{data['total_count']:,}** events found "
        f"({data['total_pages']} page(s)) — showing page {data['page']}"
    )

    if not logs:
        st.warning("No verification events in this date range.")
        st.stop()

    df = pd.DataFrame(logs)

    # ── colour-code expiry status ────────────────────────────────────────────
    today = date.today()

    def row_style(row):
        exp = pd.to_datetime(row["expiry_date"]).date()
        delta = (exp - today).days
        if delta < 0:
            return ["background-color: #f8d7da"] * len(row)   # red
        if delta <= 30:
            return ["background-color: #fff3cd"] * len(row)   # amber
        return [""] * len(row)

    styled = df.style.apply(row_style, axis=1)
    st.dataframe(styled, use_container_width=True)

    # ── legend ───────────────────────────────────────────────────────────────
    st.caption("🔴 Expired   🟡 Expiring within 30 days   ⚪ OK")

    # ── export: re-fetch all pages and build full CSV ────────────────────────
    if st.button("⬇️ Export full date range as CSV"):
        all_logs = []
        total_pages = data["total_pages"]
        prog = st.progress(0, text="Fetching all pages…")

        for p_num in range(1, total_pages + 1):
            try:
                pr = requests.get(
                    f"{API}/api/report",
                    params={"start": start, "end": end, "page": p_num, "limit": 1000},
                    timeout=30,
                )
                pr.raise_for_status()
                all_logs.extend(pr.json().get("logs", []))
                prog.progress(p_num / total_pages, text=f"Page {p_num}/{total_pages}")
            except requests.RequestException as e:
                st.warning(f"Failed fetching page {p_num}: {e}")

        prog.empty()
        full_df  = pd.DataFrame(all_logs)
        csv_data = full_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            csv_data,
            f"report_{start}_{end}.csv",
            "text/csv",
        )
