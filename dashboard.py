import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import date

st.set_page_config(page_title="Monthly Expenses Dashboard", layout="wide")

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with normalized snake_case column names."""
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace("[^a-z0-9]+", "_", regex=True)
        .str.replace("__+", "_", regex=True)
        .str.strip("_")
    )
    return df

def coerce_amount(series: pd.Series) -> pd.Series:
    """Coerce an amount-like series to numeric, removing commas and spaces."""
    s = series.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce")

def first_present(d: dict, keys: list):
    for k in keys:
        if k in d:
            return k
    return None

def month_floor(ts: pd.Series) -> pd.Series:
    # Normalize to month start for consistent grouping
    return ts.dt.to_period("M").dt.to_timestamp(how="S")  # Month Start

# ------------------------------------------------------------
# App UI
# ------------------------------------------------------------
st.title("Monthly Expenses by Category Dashboard")
st.caption("Upload your expenses file (CSV/XLSX/JSON). Select the correct sheet if prompted. Columns are auto-harmonized.")

# Sidebar - About
with st.sidebar:
    st.header("Controls")

# File uploader
uploaded_file = st.file_uploader("Upload your Original Expenses data file", type=["csv", "xlsx", "xls", "json"]) 

df = None
sheet_selected = None

if uploaded_file:
    try:
        fname = uploaded_file.name.lower()
        if fname.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif fname.endswith(".json"):
            df = pd.read_json(uploaded_file)
        elif fname.endswith((".xlsx", ".xls")):
            xl = pd.ExcelFile(uploaded_file)
            st.info(f"Found sheets: {xl.sheet_names}")
            # Prefer 'ExpenseLog' if present (matches your workbook), else first
            default_idx = xl.sheet_names.index("ExpenseLog") if "ExpenseLog" in xl.sheet_names else 0
            sheet_selected = st.selectbox("Select the sheet to analyze:", xl.sheet_names, index=default_idx)
            df = xl.parse(sheet_selected)
        else:
            st.error("Unsupported file type. Please upload CSV, XLSX, or JSON.")
    except Exception as e:
        st.error(f"❌ Failed to load data: {str(e)}")

if df is None:
    st.stop()

# ------------------------------------------------------------
# Harmonize and map required columns
# ------------------------------------------------------------
original_columns = list(df.columns)
df = normalize_columns(df)

# Automatic canonical mapping for common variants
col_map_candidates = {
    # canonical_name: list of possible variants already normalized
    "expense_category": [
        "expense_category", "category", "expense_type"
    ],
    "expense_amount_in_inr": [
        "expense_amount_in_inr", "expense_approved_amount", "amount", "total_amount", "approved_amount", "value"
    ],
    "transaction_month": [
        "transaction_month", "transaction_date", "date", "date_of_expense_transaction",
        "approval_date", "date_of_claim_upload_or_submission", "last_updated_date", "reimbursement_settlement_date"
    ],
}

# Build a dynamic rename map if canonical not already there but variants exist
rename_map = {}
cols_set = set(df.columns)
for canonical, variants in col_map_candidates.items():
    if canonical not in cols_set:
        # find the first present variant
        var = next((v for v in variants if v in cols_set), None)
        if var is not None:
            rename_map[var] = canonical

if rename_map:
    df = df.rename(columns=rename_map)

# Special handling: if transaction_month still missing but we have any date-like column, create it
if "transaction_month" not in df.columns:
    possible_dt_cols = [
        "date_of_expense_transaction", "transaction_date", "approval_date",
        "date_of_claim_upload_or_submission", "last_updated_date", "reimbursement_settlement_date",
        "date", "created_at", "updated_at"
    ]
    dt_src = first_present({c: True for c in df.columns}, possible_dt_cols)
    if dt_src:
        parsed = pd.to_datetime(df[dt_src], errors="coerce")
        df["transaction_month"] = month_floor(parsed)

# Ensure datatypes
if "expense_amount_in_inr" in df.columns:
    df["expense_amount_in_inr"] = coerce_amount(df["expense_amount_in_inr"])  # numeric
if "transaction_month" in df.columns:
    df["transaction_month"] = pd.to_datetime(df["transaction_month"], errors="coerce")
if "expense_category" in df.columns:
    df["expense_category"] = df["expense_category"].astype(str).str.strip()

# Validate required columns
required = ["expense_category", "expense_amount_in_inr", "transaction_month"]
missing = [c for c in required if c not in df.columns]

with st.expander("Column diagnostics", expanded=False):
    st.write("Original columns:", original_columns)
    st.write("Harmonized columns:", list(df.columns))
    if rename_map:
        st.write("Auto-mapped columns:", rename_map)

if missing:
    st.error(f"Missing columns required for analysis: {missing}")
    st.stop()

# Clean data: drop rows with missing criticals
initial_rows = len(df)
df = df.dropna(subset=required)
rows_removed = initial_rows - len(df)
if rows_removed > 0:
    st.warning(f"⚠️ Skipped {rows_removed} rows with missing/invalid critical values. Working with {len(df)} valid rows.")

# If no valid rows after cleaning
if df.empty:
    st.error("No valid rows available after cleaning. Please check your data.")
    st.stop()

# Sort by month
df = df.sort_values("transaction_month")

# ------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------
with st.sidebar:
    # Categories
    cats = sorted(df["expense_category"].dropna().unique().tolist())
    selected_cats = st.multiselect("Expense categories", options=cats, default=cats)

    # Date range
    if pd.api.types.is_datetime64_any_dtype(df["transaction_month"]):
        min_d = pd.to_datetime(df["transaction_month"].min()).date()
        max_d = pd.to_datetime(df["transaction_month"].max()).date()
        dr = st.date_input("Transaction month range", value=[min_d, max_d], min_value=min_d, max_value=max_d)
        if isinstance(dr, (list, tuple)) and len(dr) == 2:
            start_d, end_d = dr
        else:
            # If single date selected, treat as both start and end
            start_d = end_d = dr if isinstance(dr, date) else min_d
        mask = (df["transaction_month"] >= pd.to_datetime(start_d)) & (df["transaction_month"] <= pd.to_datetime(end_d))
        df = df.loc[mask]

    # Apply category filter
    if selected_cats:
        df = df[df["expense_category"].isin(selected_cats)]

if df.empty:
    st.warning("No data after applying filters. Adjust filters to see results.")
    st.stop()

# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------
st.subheader("Key Metrics")
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Total Expenses (INR)", f"{df['expense_amount_in_inr'].sum():,.0f}")
with k2:
    st.metric("Transactions", f"{len(df):,}")
with k3:
    st.metric("Unique Categories", int(df["expense_category"].nunique()))

# ------------------------------------------------------------
# Aggregations
# ------------------------------------------------------------
# Monthly aggregation at month-end ('ME') for consistency with modern pandas
try:
    monthly = (
        df.groupby([pd.Grouper(key="transaction_month", freq="ME"), "expense_category"], dropna=False)["expense_amount_in_inr"]
        .sum()
        .reset_index()
        .sort_values(["transaction_month", "expense_category"])
    )
    monthly["month_str"] = monthly["transaction_month"].dt.strftime("%Y-%m")
except Exception as e:
    st.error(f"Monthly aggregation failed: {e}")
    st.stop()

monthly_pivot = monthly.pivot(index="month_str", columns="expense_category", values="expense_amount_in_inr").fillna(0)

# ------------------------------------------------------------
# Layout: Tabs
# ------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Distributions", "Correlations", "Data"])

with tab1:
    st.markdown("### Monthly Expenses by Category")
    try:
        fig_line = px.line(
            monthly,
            x="month_str",
            y="expense_amount_in_inr",
            color="expense_category",
            markers=True,
            labels={
                "month_str": "Month",
                "expense_amount_in_inr": "Expense (INR)",
                "expense_category": "Category",
            },
        )
        st.plotly_chart(fig_line, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating line chart: {e}")
        st.info("Please check your data format and try again.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Top 5 Categories by Total Spend")
        try:
            topcats = (
                df.groupby("expense_category")["expense_amount_in_inr"].sum().sort_values(ascending=False).head(5).reset_index()
            )
            fig_bar = px.bar(
                topcats,
                x="expense_category",
                y="expense_amount_in_inr",
                color="expense_category",
                text="expense_amount_in_inr",
                labels={"expense_category": "Category", "expense_amount_in_inr": "Total (INR)"},
            )
            fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating top categories chart: {e}")

    with c2:
        st.markdown("#### Spend Proportions (Donut)")
        try:
            totals = df.groupby("expense_category")["expense_amount_in_inr"].sum().reset_index()
            fig_pie = px.pie(
                totals,
                names="expense_category",
                values="expense_amount_in_inr",
                hole=0.45,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating donut chart: {e}")

    with st.expander("Heatmap: Monthly x Category"):
        try:
            fig_hm, ax = plt.subplots(figsize=(12, 4))
            sns.heatmap(monthly_pivot, annot=True, fmt=".0f", cmap="OrRd", ax=ax, linewidths=0.5)
            ax.set_xlabel("Category")
            ax.set_ylabel("Month")
            ax.set_title("Monthly Spend by Category")
            st.pyplot(fig_hm)
        except Exception as e:
            st.error(f"Error creating heatmap: {e}")

with tab2:
    st.markdown("### Distributions")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Expense Amounts Histogram")
        try:
            fig_hist = px.histogram(df, x="expense_amount_in_inr", nbins=40, opacity=0.85)
            fig_hist.update_layout(xaxis_title="Expense Amount (INR)", yaxis_title="Count")
            st.plotly_chart(fig_hist, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating histogram: {e}")

    with c2:
        st.markdown("#### Box Plot by Category")
        try:
            fig_box = px.box(df, x="expense_category", y="expense_amount_in_inr", points="outliers")
            fig_box.update_layout(xaxis_title="Category", yaxis_title="Expense Amount (INR)")
            st.plotly_chart(fig_box, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating box plot: {e}")

with tab3:
    st.markdown("### Correlations (numeric columns)")
    try:
        num_df = df.select_dtypes(include=[np.number])
        if num_df.shape[1] >= 2:
            corr = num_df.corr(numeric_only=True)
            fig_corr, ax = plt.subplots(figsize=(6, 4))
            sns.heatmap(corr, annot=True, cmap="Blues", fmt=".2f", ax=ax)
            ax.set_title("Correlation Heatmap")
            st.pyplot(fig_corr)
            with st.expander("Correlation matrix data"):
                st.dataframe(corr)
        else:
            st.info("Not enough numeric columns to compute correlations.")
    except Exception as e:
        st.error(f"Error computing correlations: {e}")
        st.info("Please check your data format and try again.")

with tab4:
    st.markdown("### Data Preview & Download")
    show_cols = [c for c in ["transaction_month", "expense_category", "expense_amount_in_inr"] if c in df.columns]
    st.dataframe(df[show_cols + [c for c in df.columns if c not in show_cols]].head(1000), use_container_width=True)

    # Download filtered/cleaned data
    try:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Cleaned & Filtered Data (CSV)",
            data=csv,
            file_name="cleaned_expenses.csv",
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Error preparing download: {e}")

# Footer note
st.caption("Tip: If your columns have different names, the app auto-detects and maps common variants (e.g., 'Expense Amount in INR' → expense_amount_in_inr, 'Transaction Month' → transaction_month). Use the 'Column diagnostics' expander above to review mappings.") 
