import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Store Dashboard", page_icon="📊", layout="wide")

conn = sqlite3.connect("liquor_store.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT,
        category TEXT,
        name TEXT,
        size TEXT,
        quantity_unit INTEGER,
        quantity_carton INTEGER,
        carton_capacity INTEGER,
        cost_price REAL
    )
""")
conn.commit()

df_calc = pd.read_sql("SELECT * FROM inventory", conn)
total_value = 0.0
if not df_calc.empty:
    for _, row in df_calc.iterrows():
        units = row["quantity_unit"] if row["quantity_unit"] else 0
        cartons = row["quantity_carton" ] if row["quantity_carton"] else 0
        cap = row["carton_capacity"] if row["carton_capacity"] else 12
        cost = row["cost_price"] if row["cost_price"] else 0.0
        total_value += ((cartons * cap) + units) * (cost / cap)

st.markdown("### Store Dashboard")
st.markdown(f"**Store Inventory Value: ${total_value:,.2f}**")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    btn_inventory = st.button("Inventory SKU")
with col2:
    btn_add = st.button("+ Add Item")
with col3:
    btn_invoices = st.button("Invoices")
with col4:
    btn_report = st.button("Print Report")
with col5:
    btn_pdf = st.button("Export PDF")

st.markdown("---")
st.markdown("#### Barcode Scan / Manual")
scan_col1, scan_col2 = st.columns([3, 1])
with scan_col1:
    barcode_input = st.text_input("Scan Barcode or Item SKU & press Enter", label_visibility="collapsed", placeholder="Scan Barcode or Item SKU & press Enter")
with scan_col2:
    scan_cam = st.button("Scan Cam")

st.markdown("#### Live Search (By Name or Category)")
search_input = st.text_input("Type Item Name or Category to Filter List", label_visibility="collapsed", placeholder="Type Item Name or Category to Filter List")

st.markdown("#### Inventory Items (Click Product Name for all sizes and details)")

df = pd.read_sql("SELECT * FROM inventory", conn)

if search_input and not df.empty:
    df = df[df['name'].str.contains(search_input, case=False, na=False) | df['category'].str.contains(search_input, case=False, na=False)]

if not df.empty:
    display_df = df[["name", "category"]].copy()
    display_df["Total Purchase Cost"] = df.apply(lambda r: ((r["quantity_carton"] * r["carton_capacity"]) + r["quantity_unit"]) * (r["cost_price"] / r["carton_capacity"]), axis=1)
    display_df.columns = ["Product Name", "Category", "Total Purchase Cost"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    empty_df = pd.DataFrame(columns=["Product Name", "Category", "Total Purchase Cost"])
    st.dataframe(empty_df, use_container_width=True, hide_index=True)

if btn_add:
    st.markdown("---")
    st.subheader("Add New Item")
    with st.form("dashboard_add_form"):
        b_code = st.text_input("Barcode")
        b_cat = st.text_input("Category")
        b_name = st.text_input("Name")
        b_size = st.text_input("Size")
        b_qu = st.number_input("Quantity Unit", min_value=0, step=1)
        b_qc = st.number_input("Quantity Carton", min_value=0, step=1)
        b_cap = st.number_input("Carton Capacity", min_value=1, value=12, step=1)
        b_cost = st.number_input("Cost Price", min_value=0.0, step=0.1)
        
        submitted = st.form_submit_button("Save Product")
        if submitted:
            cursor.execute("""
                INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (b_code, b_cat, b_name, b_size, b_qu, b_qc, b_cap, b_cost))
            conn.commit()
            st.success("Product added successfully! Refresh the page to see updates.")

