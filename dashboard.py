import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Monthly Expenses Dashboard", layout="wide")
st.title("Monthly Expenses by Category Dashboard")
st.write("This dashboard shows monthly expenses grouped by category, as well as the top 5 categories of spending.")

# File uploader
df = None
uploaded_file = st.file_uploader("Upload your Original Expenses data file", type=['xlsx', 'csv', 'json'])
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            xl = pd.ExcelFile(uploaded_file)
            st.info(f"Found sheets: {xl.sheet_names}")
            sheet = st.selectbox("Select the sheet to analyze:", xl.sheet_names, index=xl.sheet_names.index("expenselog") if "expenselog" in xl.sheet_names else 0)
            df = xl.parse(sheet)
    except Exception as e:
        st.error(f"❌ Failed to load data: {str(e)}")

if df is not None:
    # Data cleaning and validation
    expected_columns = ["expense_category","expense_amount_in_inr","transaction_month"]
    missing = [col for col in expected_columns if col not in list(df.columns)]
    if missing:
        st.error(f"Missing columns required for analysis: {missing}")
        st.info(f"Your columns: {list(df.columns)}")
    else:
        initial_rows = len(df)
        # Clean/convert formats for key columns
        df['expense_category'] = df['expense_category'].astype(str)
        df['expense_amount_in_inr'] = pd.to_numeric(df['expense_amount_in_inr'], errors='coerce')
        df['transaction_month'] = pd.to_datetime(df['transaction_month'], errors='coerce')
        # Drop rows with missing key values
        df_clean = df.dropna(subset=['expense_category','expense_amount_in_inr','transaction_month'])
        rows_removed = initial_rows - len(df_clean)
        if rows_removed > 0:
            st.warning(f"⚠️ Skipped {rows_removed} rows with missing/invalid data. Working with {len(df_clean)} valid rows.")
        
        df = df_clean.sort_values('transaction_month')
        
        # Aggregate: Monthly expense by category
        monthly = df.groupby([pd.Grouper(key='transaction_month', freq='M'),'expense_category'], dropna=False)['expense_amount_in_inr'].sum().reset_index()
        monthly['month_str'] = monthly['transaction_month'].dt.strftime('%Y-%m')
        monthly_pivot = monthly.pivot(index='month_str', columns='expense_category', values='expense_amount_in_inr').fillna(0)

        st.header("1. Monthly Expenses by Category")
        fig1 = px.line(
            monthly,
            x='month_str',
            y='expense_amount_in_inr',
            color='expense_category',
            markers=True,
            labels={'month_str':'Month','expense_amount_in_inr':'Expense Amount (INR)','expense_category':'Category'},
            title='Monthly Expenses by Category (Line Chart)'
        )
        try:
            st.plotly_chart(fig1, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating plot: {str(e)}")

        st.markdown("---")
        st.header("2. Top 5 Categories of Total Spend")
        # Top 5 categories overall
        topcats = df.groupby('expense_category')['expense_amount_in_inr'].sum().sort_values(ascending=False).head(5).reset_index()
        fig2 = px.bar(
            topcats,
            x='expense_category',
            y='expense_amount_in_inr',
            color='expense_category',
            text='expense_amount_in_inr',
            labels={'expense_category':'Expense Category','expense_amount_in_inr':'Total Spend (INR)'},
            title='Top 5 Categories by Total Spend',
        )
        fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        try:
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating plot: {str(e)}")

        with st.expander("Show top expenses breakdown table"):
            st.dataframe(topcats, use_container_width=True)

        # Optionally: add heatmap by month/category
        with st.expander("Show monthly-category spend heatmap"):
            try:
                fig3, ax = plt.subplots(figsize=(12, 4))
                sns.heatmap(monthly_pivot, annot=True, fmt='.0f', cmap='OrRd', ax=ax, linewidths=0.5)
                plt.ylabel('Month')
                plt.xlabel('Category')
                plt.title('Heatmap: Monthly Spend by Category')
                st.pyplot(fig3)
            except Exception as e:
                st.error(f"Error creating heatmap: {str(e)}")
        
        st.markdown("---")
        st.header("Filtered Data Table")
        st.dataframe(df[['transaction_month','expense_category','expense_amount_in_inr']].sort_values(['transaction_month','expense_category']), use_container_width=True)

        # Enable download of cleaned/filtered data
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Cleaned Expense Data as CSV",
            data=csv,
            file_name='cleaned_expense_data.csv',
            mime='text/csv',
        )
else:
    st.info("Please upload the 'Original Expenses' data file (.xlsx, .csv, .json) above to view the dashboard.") import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Monthly Expenses Dashboard", layout="wide")
st.title("Monthly Expenses by Category Dashboard")
st.write("This dashboard shows monthly expenses grouped by category, as well as the top 5 categories of spending.")

# File uploader
df = None
uploaded_file = st.file_uploader("Upload your Original Expenses data file", type=['xlsx', 'csv', 'json'])
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            xl = pd.ExcelFile(uploaded_file)
            st.info(f"Found sheets: {xl.sheet_names}")
            sheet = st.selectbox("Select the sheet to analyze:", xl.sheet_names, index=xl.sheet_names.index("expenselog") if "expenselog" in xl.sheet_names else 0)
            df = xl.parse(sheet)
    except Exception as e:
        st.error(f"❌ Failed to load data: {str(e)}")

if df is not None:
    # Data cleaning and validation
    expected_columns = ["expense_category","expense_amount_in_inr","transaction_month"]
    missing = [col for col in expected_columns if col not in list(df.columns)]
    if missing:
        st.error(f"Missing columns required for analysis: {missing}")
        st.info(f"Your columns: {list(df.columns)}")
    else:
        initial_rows = len(df)
        # Clean/convert formats for key columns
        df['expense_category'] = df['expense_category'].astype(str)
        df['expense_amount_in_inr'] = pd.to_numeric(df['expense_amount_in_inr'], errors='coerce')
        df['transaction_month'] = pd.to_datetime(df['transaction_month'], errors='coerce')
        # Drop rows with missing key values
        df_clean = df.dropna(subset=['expense_category','expense_amount_in_inr','transaction_month'])
        rows_removed = initial_rows - len(df_clean)
        if rows_removed > 0:
            st.warning(f"⚠️ Skipped {rows_removed} rows with missing/invalid data. Working with {len(df_clean)} valid rows.")
        
        df = df_clean.sort_values('transaction_month')
        
        # Aggregate: Monthly expense by category
        monthly = df.groupby([pd.Grouper(key='transaction_month', freq='M'),'expense_category'], dropna=False)['expense_amount_in_inr'].sum().reset_index()
        monthly['month_str'] = monthly['transaction_month'].dt.strftime('%Y-%m')
        monthly_pivot = monthly.pivot(index='month_str', columns='expense_category', values='expense_amount_in_inr').fillna(0)

        st.header("1. Monthly Expenses by Category")
        fig1 = px.line(
            monthly,
            x='month_str',
            y='expense_amount_in_inr',
            color='expense_category',
            markers=True,
            labels={'month_str':'Month','expense_amount_in_inr':'Expense Amount (INR)','expense_category':'Category'},
            title='Monthly Expenses by Category (Line Chart)'
        )
        try:
            st.plotly_chart(fig1, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating plot: {str(e)}")

        st.markdown("---")
        st.header("2. Top 5 Categories of Total Spend")
        # Top 5 categories overall
        topcats = df.groupby('expense_category')['expense_amount_in_inr'].sum().sort_values(ascending=False).head(5).reset_index()
        fig2 = px.bar(
            topcats,
            x='expense_category',
            y='expense_amount_in_inr',
            color='expense_category',
            text='expense_amount_in_inr',
            labels={'expense_category':'Expense Category','expense_amount_in_inr':'Total Spend (INR)'},
            title='Top 5 Categories by Total Spend',
        )
        fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        try:
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating plot: {str(e)}")

        with st.expander("Show top expenses breakdown table"):
            st.dataframe(topcats, use_container_width=True)

        # Optionally: add heatmap by month/category
        with st.expander("Show monthly-category spend heatmap"):
            try:
                fig3, ax = plt.subplots(figsize=(12, 4))
                sns.heatmap(monthly_pivot, annot=True, fmt='.0f', cmap='OrRd', ax=ax, linewidths=0.5)
                plt.ylabel('Month')
                plt.xlabel('Category')
                plt.title('Heatmap: Monthly Spend by Category')
                st.pyplot(fig3)
            except Exception as e:
                st.error(f"Error creating heatmap: {str(e)}")
        
        st.markdown("---")
        st.header("Filtered Data Table")
        st.dataframe(df[['transaction_month','expense_category','expense_amount_in_inr']].sort_values(['transaction_month','expense_category']), use_container_width=True)

        # Enable download of cleaned/filtered data
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Cleaned Expense Data as CSV",
            data=csv,
            file_name='cleaned_expense_data.csv',
            mime='text/csv',
        )
else:
    st.info("Please upload the 'Original Expenses' data file (.xlsx, .csv, .json) above to view the dashboard.") 
