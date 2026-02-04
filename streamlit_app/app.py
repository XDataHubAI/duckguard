"""
DuckGuard — Data Quality Explorer
Upload a CSV or Parquet file and get an instant quality report.

Deploy: streamlit run streamlit_app/app.py
Cloud: https://streamlit.io/cloud (connect GitHub repo, point to streamlit_app/app.py)
"""

import io
import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="DuckGuard — Data Quality Explorer",
    page_icon="🦆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Header ---
st.markdown(
    """
    <div style="text-align: center; padding: 1rem 0;">
        <h1>🦆 DuckGuard — Data Quality Explorer</h1>
        <p style="font-size: 1.2rem; color: #666;">
            Upload your data. Get a quality report in seconds.
        </p>
        <p>
            <a href="https://github.com/XDataHubAI/duckguard" target="_blank">⭐ GitHub</a> ·
            <a href="https://xdatahubai.github.io/duckguard/" target="_blank">📚 Docs</a> ·
            <a href="https://pypi.org/project/duckguard/" target="_blank">📦 PyPI</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    deep_profile = st.checkbox("Deep profiling", value=False, help="Distribution analysis + outlier detection (slower)")
    show_pii = st.checkbox("PII detection", value=True, help="Scan for emails, phones, SSNs, etc.")
    show_anomalies = st.checkbox("Anomaly detection", value=True, help="Z-score anomaly scan on numeric columns")
    anomaly_method = st.selectbox("Anomaly method", ["zscore", "iqr", "modified_zscore"], index=0)
    show_rules = st.checkbox("Auto-suggest rules", value=True, help="Generate YAML validation rules")

    st.divider()
    st.markdown(
        """
        ### 💡 Works with any source

        This demo uses file uploads. In Python, DuckGuard connects to:

        ```python
        connect("s3://bucket/data.parquet")
        connect("snowflake://acct/db", table="t")
        connect("databricks://host", table="t")
        connect("bigquery://proj", table="t")
        ```

        `pip install duckguard`
        """
    )


# --- File upload ---
uploaded = st.file_uploader(
    "Upload CSV or Parquet",
    type=["csv", "parquet", "pq", "json"],
    help="Max 200MB. Your data stays in the browser session — nothing is stored.",
)

# --- Demo data ---
use_demo = st.checkbox("Or use demo data (e-commerce orders with quality issues)")

if not uploaded and not use_demo:
    st.info("👆 Upload a file or check the demo box to get started.")
    st.stop()


# --- Load data ---
@st.cache_data(show_spinner="Loading data...")
def load_data(file_bytes: bytes, filename: str) -> "Dataset":
    from duckguard import connect

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    return connect(tmp_path)


@st.cache_data(show_spinner="Loading demo data...")
def load_demo() -> "Dataset":
    from duckguard import connect

    demo_csv = """order_id,customer_id,product_name,quantity,unit_price,subtotal,tax,shipping,total_amount,status,country,email,phone,created_at,ship_date
ORD001,CUST001,Widget Pro,2,29.99,59.98,5.40,4.99,70.37,shipped,US,alice@example.com,555-0101,2024-01-15,2024-01-17
ORD002,CUST002,Gadget Plus,1,49.99,49.99,4.50,0.00,54.49,delivered,US,bob@example.com,555-0102,2024-01-15,2024-01-18
ORD003,,Widget Pro,-3,29.99,-89.97,-8.10,4.99,-93.08,pending,UK,charlie@example.com,+44-20-7946-0958,2024-01-16,
ORD004,CUST004,Super Gizmo,1,199.99,199.99,18.00,0.00,217.99,shipped,US,,555-0104,2024-01-16,2024-01-19
ORD005,CUST005,Widget Pro,500,29.99,14995.00,1349.55,4.99,16349.54,pending,CA,eve@example.com,555-0105,2024-01-17,
ORD006,CUST006,Gadget Plus,2,49.99,99.98,9.00,4.99,113.97,INVALID,US,frank@example.com,555-0106,2024-01-17,2024-01-20
ORD007,CUST007,Basic Widget,1,9.99,9.99,0.90,4.99,15.88,delivered,US,grace@example,555-0107,2024-01-18,2024-01-20
ORD008,CUST008,Premium Bundle,3,99.99,299.97,27.00,0.00,326.97,shipped,DE,hans@example.de,+49-30-12345678,2024-01-18,2024-01-22
ORD009,CUST009,Widget Pro,1,29.99,29.99,2.70,4.99,37.68,delivered,US,ivan@example.com,,2024-01-19,2024-01-21
ORD010,CUST010,Super Gizmo,2,199.99,399.98,36.00,0.00,435.98,pending,JP,jun@example.jp,+81-3-1234-5678,2024-01-19,"""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        tmp.write(demo_csv.strip())
        tmp_path = tmp.name
    return connect(tmp_path)


try:
    if uploaded:
        data = load_data(uploaded.getvalue(), uploaded.name)
        st.success(f"Loaded **{uploaded.name}** — {data.row_count:,} rows, {len(data.columns)} columns")
    else:
        data = load_demo()
        st.success(f"Loaded **demo data** — {data.row_count:,} rows, {len(data.columns)} columns")
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()


# --- Overview ---
st.header("📊 Overview")

col1, col2, col3, col4 = st.columns(4)

score = data.score()
col1.metric("Quality Grade", score.grade)
col2.metric("Completeness", f"{score.completeness:.1f}%")
col3.metric("Uniqueness", f"{score.uniqueness:.1f}%")
col4.metric("Validity", f"{score.validity:.1f}%")

st.progress(score.overall / 100, text=f"Overall Score: {score.overall:.1f}/100")


# --- Column Profile ---
st.header("🔍 Column Profile")

from duckguard import AutoProfiler

profiler = AutoProfiler(deep=deep_profile)
profile = profiler.profile(data)

profile_rows = []
for col in profile.columns:
    row = {
        "Column": col.name,
        "Type": col.dtype,
        "Nulls %": round(col.null_percent, 1),
        "Unique %": round(col.unique_percent, 1),
        "Grade": col.quality_grade,
    }
    if hasattr(col, "min_value") and col.min_value is not None:
        row["Min"] = col.min_value
        row["Max"] = col.max_value
    profile_rows.append(row)

st.dataframe(profile_rows, use_container_width=True, hide_index=True)


# --- PII Detection ---
if show_pii:
    st.header("🔒 PII Detection")
    from duckguard import SemanticAnalyzer

    analysis = SemanticAnalyzer().analyze(data)
    if analysis.pii_columns:
        for col_info in analysis.columns:
            if col_info.is_pii:
                st.warning(
                    f"**{col_info.name}** — detected as `{col_info.semantic_type.value}` "
                    f"(confidence: {col_info.confidence:.0%})"
                )
        st.caption(f"Found PII in {len(analysis.pii_columns)} column(s): {', '.join(analysis.pii_columns)}")
    else:
        st.success("No PII detected.")


# --- Anomaly Detection ---
if show_anomalies:
    st.header("🚨 Anomaly Detection")
    from duckguard import detect_anomalies

    # Get numeric columns
    numeric_cols = [
        col.name for col in profile.columns if col.dtype in ("BIGINT", "INTEGER", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "SMALLINT", "TINYINT")
    ]

    if numeric_cols:
        try:
            report = detect_anomalies(data, method=anomaly_method, columns=numeric_cols)
            if report.has_anomalies:
                for a in report.anomalies:
                    if a.is_anomaly:
                        st.error(f"**{a.column}** — anomaly score: {a.score:.2f}")
                    else:
                        st.success(f"**{a.column}** — score: {a.score:.2f} (normal)")
            else:
                st.success("No anomalies detected.")
        except Exception as e:
            st.warning(f"Anomaly detection skipped: {e}")
    else:
        st.info("No numeric columns found for anomaly detection.")


# --- Auto-Suggest Rules ---
if show_rules:
    st.header("📋 Suggested Validation Rules")
    from duckguard import generate_rules

    try:
        yaml_rules = generate_rules(data, dataset_name="uploaded_data")
        st.code(yaml_rules, language="yaml")
        st.download_button(
            "📥 Download duckguard.yaml",
            data=yaml_rules,
            file_name="duckguard.yaml",
            mime="text/yaml",
        )
    except Exception as e:
        st.warning(f"Rule generation skipped: {e}")


# --- Data Preview ---
st.header("👀 Data Preview")
try:
    preview = data.head(20)
    st.dataframe(preview, use_container_width=True, hide_index=True)
except Exception:
    st.info("Preview not available for this data source.")


# --- Code snippet ---
st.divider()
st.header("🐍 Use in Python")

source_name = uploaded.name if uploaded else "your_data.csv"
st.code(
    f"""from duckguard import connect

data = connect("{source_name}")

# Quality score
score = data.score()
print(f"Grade: {{score.grade}}")

# Validate columns
assert data.{data.columns[0]}.is_not_null()
assert data.{data.columns[0]}.is_unique()

# Profile
from duckguard import AutoProfiler
profile = AutoProfiler().profile(data)
for col in profile.columns:
    print(f"{{col.name}}: {{col.quality_grade}}")
""",
    language="python",
)

st.caption(
    "Install: `pip install duckguard` · "
    "Connects to S3, Snowflake, Databricks, BigQuery, and 15+ sources · "
    "[GitHub](https://github.com/XDataHubAI/duckguard) · "
    "[Docs](https://xdatahubai.github.io/duckguard/)"
)
