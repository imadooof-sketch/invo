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

    st.markdown("#### Inventory Items (Click product name to manage sizes, quantities & prices)")
    
    if products_dict:
        for prod_name, total_cost in products_dict.items():
            cat = category_dict[prod_name]
            
            with st.expander(f"📦 {prod_name}  |  Category: {cat}  |  Total Cost: ${total_cost:,.2f}"):
                conn_sub = sqlite3.connect("liquor_store.db", timeout=10)
                cur_sub = conn_sub.cursor()
                cur_sub.execute("SELECT id, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price, barcode, category FROM inventory WHERE name = ?", (prod_name,))
                sizes_data = cur_sub.fetchall()
                conn_sub.close()

                items_by_size = {item[1]: item for item in sizes_data}
                standard_sizes = ["50", "100", "200", "375", "750", "1L", "1.75"]

                st.markdown("##### Existing Sizes, Quantities & Prices:")
                with st.form(key=f"form_prod_{prod_name}"):
                    updated_sizes = []
                    for sz in standard_sizes:
                        if sz in items_by_size:
                            i_id, _, q_u, q_c, c_cap, c_pr, s_pr, _, _ = items_by_size[sz]
                            cap = c_cap if c_cap and c_cap > 0 else 12
                            
                            st.markdown(f"**Size: {sz}**")
                            col_u1, col_u2, col_u3, col_c1, col_c2, col_c3 = st.columns([2, 1, 1, 2, 1, 1])
                            
                            with col_u1:
                                new_u = st.number_input(f"Units", value=int(q_u or 0), min_value=0, step=1, key=f"u_{i_id}")
                            with col_u2:
                                if st.form_submit_button(f"- (U)", key=f"min_u_{i_id}"):
                                    new_u = max(0, new_u - 1)
                            with col_u3:
                                if st.form_submit_button(f"+ (U)", key=f"plus_u_{i_id}"):
                                    new_u += 1

                            with col_c1:
                                new_c = st.number_input(f"Cartons", value=int(q_c or 0), min_value=0, step=1, key=f"c_{i_id}")
                            with col_c2:
                                if st.form_submit_button(f"- (C)", key=f"min_c_{i_id}"):
                                    new_c = max(0, new_c - 1)
                            with col_c3:
                                if st.form_submit_button(f"+ (C)", key=f"plus_c_{i_id}"):
                                    new_c += 1

                            col_cap, col_cost, col_sell = st.columns(3)
                            with col_cap:
                                new_cap = st.number_input(f"Carton Capacity", value=int(cap), min_value=1, step=1, key=f"cap_{i_id}")
                            with col_cost:
                                new_cost = st.number_input(f"Cost Price ($)", value=float(c_pr or 0.0), min_value=0.0, step=0.1, key=f"cost_{i_id}")
                            with col_sell:
                                new_sell = st.number_input(f"Selling Price ($)", value=float(s_pr or 0.0), min_value=0.0, step=0.1, key=f"sell_{i_id}")
                            
                            updated_sizes.append((i_id, new_u, new_c, new_cap, new_cost, new_sell))
                            st.markdown("---")

                    submit_card = st.form_submit_button(f"Save Changes for {prod_name}")
                    if submit_card:
                        conn_up = sqlite3.connect("liquor_store.db", timeout=10)
                        cur_up = conn_up.cursor()
                        for item_id, nu, nc, ncap, ncost, nsell in updated_sizes:
                            cur_up.execute("""
                                UPDATE inventory SET quantity_unit=?, quantity_carton=?, carton_capacity=?, cost_price=?, sell_price=? WHERE id=?
                            """, (nu, nc, ncap, ncost, nsell, item_id))
                        conn_up.commit()
                        conn_up.close()
                        st.success(f"Product '{prod_name}' updated successfully!")
                        st.rerun()

                with st.expander(f"➕ Add New Size/Measurement & Update Price for {prod_name}"):
                    with st.form(key=f"add_size_form_{prod_name}"):
                        avail_sizes = [s for s in standard_sizes if s not in items_by_size]
                        new_sz = st.selectbox(f"Select Size to Add", avail_sizes if avail_sizes else standard_sizes, key=f"new_sz_{prod_name}")
                        add_type = st.radio("Add Type", ["Units (فردية)", "Cartons (كرتونة)"], key=f"add_type_{prod_name}")
                        add_qty = st.number_input("Quantity to Add", min_value=1, value=1, step=1, key=f"add_qty_{prod_name}")
                        add_cap = st.number_input("Carton Capacity", min_value=1, value=12, step=1, key=f"add_cap_{prod_name}")
                        add_cost = st.number_input("New Cost Price ($)", min_value=0.0, value=0.0, step=0.1, key=f"add_cost_{prod_name}")
                        add_sell = st.number_input("New Selling Price ($)", min_value=0.0, value=0.0, step=0.1, key=f"add_sell_{prod_name}")

                        submit_add_size = st.form_submit_button("Add & Update Price")
                        if submit_add_size:
                            conn_add = sqlite3.connect("liquor_store.db", timeout=10)
                            cur_add = conn_add.cursor()
                            
                            u_val = add_qty if "Units" in add_type else 0
                            c_val = add_qty if "Cartons" in add_type else 0

                            cur_add.execute("SELECT id, quantity_unit, quantity_carton FROM inventory WHERE name = ? AND size = ?", (prod_name, new_sz))
                            existing_row = cur_add.fetchone()

                            if existing_row:
                                ex_id, ex_u, ex_c = existing_row
                                if "Units" in add_type:
                                    final_u = (ex_u or 0) + add_qty
                                    cur_add.execute("UPDATE inventory SET quantity_unit = ?, cost_price = ?, sell_price = ? WHERE id = ?", (final_u, add_cost, add_sell, ex_id))
                                else:
                                    final_c = (ex_c or 0) + add_qty
                                    cur_add.execute("UPDATE inventory SET quantity_carton = ?, cost_price = ?, sell_price = ? WHERE id = ?", (final_c, add_cost, add_sell, ex_id))
                            else:
                                sample_row = sizes_data[0] if sizes_data else ("", "", 0, 0, 12, 0.0, 0.0, "", cat)
                                cur_add.execute("""
                                    INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (sample_row[7], sample_row[8], prod_name, new_sz, u_val, c_val, add_cap, add_cost, add_sell))

                            conn_add.commit()
                            conn_add.close()
                            st.success("Size, quantity and new price added successfully!")
                            st.rerun()
    else:
        st.info("No inventory items found.")

elif st.session_state.page == "add_item":
    st.subheader("Add New Item")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    
    with st.form("add_item_form_web"):
        b_code = st.text_input("Barcode")
        category = st.selectbox("Category", ["Cognac", "Whisky", "Brandy", "Rum", "Vodka", "Tequila", "Liquor", "Variety"])
        name = st.text_input("Product Name")
        size = st.selectbox("Size", ["50", "100", "200", "375", "750", "1L", "1.75"])
        qty_type = st.radio("Quantity Type", ["Units (فردية)", "Cartons (كرتونة)"])
        qty_val = st.number_input("Quantity", min_value=0, step=1)
        carton_cap = st.selectbox("Carton Capacity", [12, 6, 24, 48])
        cost_price = st.number_input("Cost Price ($)", min_value=0.0, step=0.1)
        sell_price = st.number_input("Selling Price ($)", min_value=0.0, step=0.1)

        submitted = st.form_submit_button("Save Item")
        if submitted:
            if name.strip():
                u_qty = qty_val if "Units" in qty_type else 0
                c_qty = qty_val if "Cartons" in qty_type else 0

                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b_code, category, name.strip(), size, u_qty, c_qty, carton_cap, cost_price, sell_price))
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

