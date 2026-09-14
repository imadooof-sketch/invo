import sqlite3
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime

st.set_page_config(page_title="Store Dashboard", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 6px; height: 2.8em; font-weight: bold; }
    .metric-card { background-color: #34495e; padding: 15px; border-radius: 8px; color: white; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect("liquor_store.db", timeout=10)
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
            cost_price REAL,
            sell_price REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            date TEXT,
            supplier TEXT,
            total_amount REAL,
            status TEXT,
            image_path TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def calculate_total_store_cost():
    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory")
    rows = cursor.fetchall()
    conn.close()

    total = 0.0
    for r in rows:
        q_u, q_c, c_cap, c_pr = r
        cap = c_cap if c_cap and c_cap > 0 else 12
        units = (q_u or 0) + ((q_c or 0) * cap)
        total += units * (c_pr if c_pr else 0.0)
    return total

st.markdown("### Store Dashboard")
total_store_value = calculate_total_store_cost()

st.markdown(f"""
    <div class="metric-card">
        <h3 style='margin:0; color: white;'>Store Inventory Value: ${total_store_value:,.2f}</h3>
    </div>
""", unsafe_allow_html=True)

col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
with col_b1:
    view_all = st.button("Inventory (All)")
with col_b2:
    add_item_btn = st.button("+ Add Item")
with col_b3:
    invoices_btn = st.button("Invoices")
with col_b4:
    print_btn = st.button("Print Report")
with col_b5:
    pdf_btn = st.button("Export PDF")

st.markdown("---")

if 'page' not in st.session_state:
    st.session_state.page = "dashboard"

if add_item_btn:
    st.session_state.page = "add_item"
elif invoices_btn:
    st.session_state.page = "invoices"
elif print_btn:
    st.session_state.page = "print_report"
elif pdf_btn:
    st.session_state.page = "export_pdf"
elif view_all:
    st.session_state.page = "dashboard"

# لوحة التحكم الرئيسية وعرض المنتجات مع إمكانية فتح تفاصيل المنتج عند النقر
if st.session_state.page == "dashboard":
    st.markdown("#### Barcode Scan / Live Search")
    search_col1, search_col2 = st.columns(2)
    with search_col1:
        barcode_input = st.text_input("Scan Barcode or Type SKU", placeholder="Scan barcode...")
    with search_col2:
        search_input = st.text_input("Live Search (Name or Category)", placeholder="Type item name...")

    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()

    if barcode_input:
        cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory WHERE barcode = ? ORDER BY name ASC", (barcode_input.strip(),))
    elif search_input:
        cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory WHERE name LIKE ? OR category LIKE ? ORDER BY name ASC", (f"%{search_input}%", f"%{search_input}%"))
    else:
        cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")

    rows = cursor.fetchall()
    conn.close()

    products_dict = {}
    category_dict = {}
    for r in rows:
        name, category, q_unit, q_carton, carton_cap, cost_price = r
        cap = carton_cap if carton_cap and carton_cap > 0 else 12
        total_units = (q_unit or 0) + ((q_carton or 0) * cap)
        item_cost_val = total_units * (cost_price if cost_price else 0.0)

        if name not in products_dict:
            products_dict[name] = 0.0
            category_dict[name] = category
        products_dict[name] += item_cost_val

    st.markdown("#### Inventory Items (Click product name below to edit sizes, quantities & prices)")
    
    if products_dict:
        for prod_name, total_cost in products_dict.items():
            cat = category_dict[prod_name]
            
            # إنشاء صندوق تفاعلي لكل منتج يعرض تفاصيله وقياساته عند الضغط عليه
            with st.expander(f"📦 {prod_name}  |  Category: {cat}  |  Total Cost: ${total_cost:,.2f}"):
                conn_sub = sqlite3.connect("liquor_store.db", timeout=10)
                cur_sub = conn_sub.cursor()
                cur_sub.execute("SELECT id, size, quantity_unit, quantity_carton, carton_capacity, cost_price, barcode FROM inventory WHERE name = ?", (prod_name,))
                sizes_data = cur_sub.fetchall()
                conn_sub.close()

                st.markdown("##### Sizes, Quantities & Prices Management:")
                
                with st.form(key=f"form_prod_{prod_name}"):
                    updated_sizes = []
                    for idx, s_row in enumerate(sizes_data):
                        i_id, sz, q_u, q_c, c_cap, c_pr, b_code = s_row
                        cap = c_cap if c_cap and c_cap > 0 else 12
                        
                        st.markdown(f"**Size: {sz}**")
                        col_sz1, col_sz2, col_sz3, col_sz4 = st.columns(4)
                        with col_sz1:
                            new_u = st.number_input(f"Units ({sz})", value=int(q_u or 0), min_value=0, step=1, key=f"u_{i_id}")
                        with col_sz2:
                            new_c = st.number_input(f"Cartons ({sz})", value=int(q_c or 0), min_value=0, step=1, key=f"c_{i_id}")
                        with col_sz3:
                            new_cap = st.number_input(f"Cap ({sz})", value=int(cap), min_value=1, step=1, key=f"cap_{i_id}")
                        with col_sz4:
                            new_cost = st.number_input(f"Cost Price ($) ({sz})", value=float(c_pr or 0.0), min_value=0.0, step=0.1, key=f"cost_{i_id}")
                        
                        updated_sizes.append((i_id, new_u, new_c, new_cap, new_cost))
                        st.markdown("---")

                    submit_card = st.form_submit_button(f"Save Changes for {prod_name}")
                    if submit_card:
                        conn_up = sqlite3.connect("liquor_store.db", timeout=10)
                        cur_up = conn_up.cursor()
                        for item_id, nu, nc, ncap, ncost in updated_sizes:
                            cur_up.execute("""
                                UPDATE inventory SET quantity_unit=?, quantity_carton=?, carton_capacity=?, cost_price=? WHERE id=?
                            """, (nu, nc, ncap, ncost, item_id))
                        conn_up.commit()
                        conn_up.close()
                        st.success(f"Product '{prod_name}' updated successfully! Refreshing...")
                        st.rerun()
    else:
		    st.info("No inventory items found.")

elif st.session_state.page == "add_item":
    st.subheader("Add New Item to Inventory")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    with st.form("add_item_form_web"):
        b_code = st.text_input("Barcode")
        category = st.selectbox("Category", ["Cognac", "Whisky", "Brandy", "Rum", "Vodka", "Tequila", "Liquor", "Variety"])
        name = st.text_input("Product Name")
        size = st.selectbox("Size", ["50", "100", "200", "375", "750", "1L", "1.75"])
        qty_unit = st.number_input("Quantity (Units)", min_value=0, step=1)
        qty_carton = st.number_input("Quantity (Cartons)", min_value=0, step=1)
        carton_cap = st.selectbox("Carton Capacity", [12, 6, 24, 48])
        cost_price = st.number_input("Cost Price ($)", min_value=0.0, step=0.1)
        sell_price = st.number_input("Selling Price ($)", min_value=0.0, step=0.1)

        submitted = st.form_submit_button("Save Item")
        if submitted:
            if name.strip():
                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b_code, category, name.strip(), size, qty_unit, qty_carton, carton_cap, cost_price, sell_price))
                conn.commit()
                conn.close()
                st.success("Product added successfully!")
            else:
                st.error("Product Name is required!")

elif st.session_state.page == "invoices":
    st.subheader("Invoices Management")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    st.info("Invoices section is ready.")

elif st.session_state.page == "print_report":
    st.subheader("Print Report")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

elif st.session_state.page == "export_pdf":
    st.subheader("Export PDF")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

