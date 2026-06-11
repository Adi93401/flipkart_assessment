"""
App 1 — Product Verification System
Streamlit entry point — landing page + sidebar navigation.
"""

import streamlit as st

st.set_page_config(
    page_title="Product Verification System",
    page_icon="🔍",
    layout="wide",
)

st.title("📦 Product Verification System")
st.caption("Fast, clear, and reliable product checks for warehouse teams.")

st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 18px 18px 14px 18px; border-radius: 18px; color: white;">
  <strong>What you can do here</strong><br>
  Upload bulk CSVs, verify products by WID, and review audit-ready reports in one place.
</div>
""", unsafe_allow_html=True)

st.markdown("""
### ✨ Why teams like this workspace
- Upload large batches without blocking the workflow
- Verify WID details and capture inspection notes quickly
- View status, inserted counts, and duplicates at a glance
""")

st.markdown("""
| Page | Role | What it helps with |
|------|------|---------------------|
| 📤 Upload | Warehouse Manager | Bulk-import products from a CSV file |
| 🔍 Verify | Warehouse Operator | Look up a product by WID and log a check |
| 📊 Reports | QA Manager | Generate date-range verification reports |
""")

if "username" not in st.session_state:
    st.session_state["username"] = ""

with st.sidebar:
    st.header("👤 Operator")
    name = st.text_input("Your name / ID", value=st.session_state["username"])
    if name:
        st.session_state["username"] = name
        st.success(f"Logged in as **{name}**")
    else:
        st.warning("Enter your name before verifying products.")
