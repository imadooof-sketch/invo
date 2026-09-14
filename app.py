import sqlite3
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="Store Dashboard", page_icon="📊", layout="wide")

# تنسيق CSS مخصص للواجهة
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 6px; height: 3em; font-weight: bold; }
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

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
        cartons = row["quantity_carton"] if row["quantity_carton"] else 0
        cap = row["carton_capacity"] if row["carton_capacity"] else 12
        cost = row["cost_price"] if row["cost_price"] else 0.0
        total_value += ((cartons * cap) + units) * (cost / cap)

st.markdown("### Store Dashboard")
st.markdown(f"""
    <div class="metric-card">
        <h4 style='margin:0; color: #31333F;'>Store Inventory Value: <span style='color: #0083B8;'>${total_value:,.2f}</span></h4>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Inventory SKU", "+ Add Item", "Invoices", "Print Report", "Export PDF"])

with tab1:
    st.markdown("#### Barcode Scan / Manual")
    scan_col1, scan_col2 = st.columns([4, 1])
    with scan_col1:
        barcode_input = st.text_input("Scan Barcode or Item SKU & press Enter", placeholder="Scan Barcode or Item SKU & press Enter", label_visibility="collapsed", key="barcode_search")
    with scan_col2:
        st.button("Scan Cam")

    st.markdown("#### Live Search (By Name or Category)")
    search_input = st.text_input("Type Item Name or Category to Filter List", placeholder="Type Item Name or Category to Filter List", label_visibility="collapsed", key="live_search")

    df = pd.read_sql("SELECT * FROM inventory", conn)
    if search_input and not df.empty:
        df = df[df['name'].str.contains(search_input, case=False, na=False) | df['category'].str.contains(search_input, case=False, na=False) | df['barcode'].str.contains(search_input, case=False, na=False)]
    elif barcode_input and not df.empty:
        df = df[df['barcode'].str.contains(barcode_input, case=False, na=False)]

    if not df.empty:
        display_df = df[["name", "category", "size", "quantity_unit", "quantity_carton", "cost_price"]].copy()
        display_df["Total Purchase Cost"] = df.apply(lambda r: ((r["quantity_carton"] * r["carton_capacity"]) + r["quantity_unit"]) * (r["cost_price"] / r["carton_capacity"]), axis=1)
        display_df.columns = ["Product Name", "Category", "Size", "Units", "Cartons", "Cost Price", "Total Purchase Cost"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No items found in inventory.")

with tab2:
    st.subheader("Add New Item")
    with st.form("add_form_tab"):
        col_a, col_b = st.columns(2)
        with col_a:
            b_code = st.text_input("Barcode")
            b_cat = st.text_input("Category")
            b_name = st.text_input("Name")
            b_size = st.text_input("Size")
        with col_b:
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
            st.success("Product added successfully!")

with tab3:
    st.subheader("Invoices & Sales")
    df_inv = pd.read_sql("SELECT * FROM inventory", conn)
    if not df_inv.empty:
        sel_item = st.selectbox("Select Product to Sell", df_inv["name"].tolist())
        row = df_inv[df_inv["name"] == sel_item].iloc[0]
        avail_units = row["quantity_unit"]
        price_val = row["cost_price"]
        
        st.write(f"Available Units: {avail_units} | Cost Price: {price_val}")
        sell_qty = st.number_input("Quantity to Sell", min_value=1, max_value=max(1, int(avail_units)), step=1)
        
        if st.button("Complete Sale"):
            new_units = max(0, avail_units - sell_qty)
            cursor.execute("UPDATE inventory SET quantity_unit = ? WHERE name = ?", (new_units, sel_item))
            conn.commit()
            st.success(f"Sale completed successfully! Remaining units: {new_units}")
    else:
        st.warning("No products available for invoicing.")

with tab4:
    st.subheader("Print Report Preview")
    df_rep = pd.read_sql("SELECT name, category, size, quantity_unit, quantity_carton, cost_price FROM inventory", conn)
    if not df_rep.empty:
        st.dataframe(df_rep, use_container_width=True)
    else:
        st.info("No data available to print.")

with tab5:
    st.subheader("Export PDF Report")
    if st.button("Generate PDF File"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.drawString(100, 750, "Store Inventory Report")
        
        df_pdf = pd.read_sql("SELECT name, category, quantity_unit, cost_price FROM inventory", conn)
        y = 700
        for _, r in df_pdf.iterrows():
            p.drawString(100, y, f"Item: {r['name']} | Category: {r['category']} | Qty: {r['quantity_unit']} | Cost: {r['cost_price']}")
            y -= 20
            if y < 50:
                p.showPage()
                y = 750
        p.save()
        buffer.seek(0)
        st.download_button(label="Download PDF", data=buffer, file_name="inventory_report.pdf", mime="application/pdf")

