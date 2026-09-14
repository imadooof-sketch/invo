import sqlite3
import streamlit as st
import os
import shutil
from datetime import datetime
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# إعداد الصفحة لتكون عريضة ومنسقة
st.set_page_config(page_title="IDiNventory - Store Management", layout="wide")

def backup_database():
    try:
        os.makedirs("backups", exist_ok=True)
        backup_name = f"backups/liquor_store_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        if os.path.exists("liquor_store.db"):
            shutil.copy("liquor_store.db", backup_name)
    except Exception as e:
        print("Backup error:", e)

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
    
    try:
        cursor.execute("ALTER TABLE inventory ADD COLUMN carton_capacity INTEGER DEFAULT 12")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'Unpaid'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    backup_database()

init_db()

# حساب إجمالي قيمة المخزون
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

# القائمة الجانبية للتنقل بين أقسام الويب
st.sidebar.title("IDiNventory Menu")
menu_option = st.sidebar.radio("Go to:", ["Store Dashboard", "Add New Item", "Invoices Management"])

if menu_option == "Store Dashboard":
    st.title("Store Dashboard")
    
    # عرض إجمالي قيمة المخزون
    total_val = calculate_total_store_cost()
    st.metric(label="Store Inventory Value", value=f"${total_val:.2f}")

    # شريط البحث
    search_query = st.text_input("Live Search (by Name or Category):", "")

    # عرض جدول المنتجات
    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()
    
    if search_query:
        cursor.execute("""
            SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price 
            FROM inventory 
            WHERE name LIKE ? OR category LIKE ? 
            ORDER BY name ASC
        """, (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")

    rows = cursor.fetchall()
    conn.close()

    if rows:
        st.write("### Inventory Items Summary")
        for r in rows:
            name, cat, q_u, q_c, c_cap, c_pr = r
            cap = c_cap if c_cap and c_cap > 0 else 12
            tot_units = (q_u or 0) + ((q_c or 0) * cap)
            tot_cost = tot_units * (c_pr if c_pr else 0.0)
            
            st.info(f"**Product:** {name} | **Category:** {cat} | **Total Units:** {tot_units} | **Cost Value:** ${tot_cost:.2f}")
    else:
        st.warning("No products found in inventory.")

elif menu_option == "Add New Item":
    st.title("Add Item to Inventory")
    
    with st.form("add_item_form"):
        barcode = st.text_input("Barcode:")
        category = st.selectbox("Category", ["Cognac", "Whisky", "Brandy", "Rum", "Vodka", "Tequila", "Liquor", "Variety"])
        custom_cat = st.text_input("Or Type Custom Category (Optional):")
        name = st.text_input("Product Name:")
        size = st.selectbox("Size", ["50", "100", "200", "375", "750", "1L", "1.75"])
        quantity_unit = st.number_input("Quantity (Units):", min_value=0, value=0)
        quantity_carton = st.number_input("Quantity (Cartons):", min_value=0, value=0)
        carton_capacity = st.selectbox("Carton Capacity (Pieces per Carton):", [12, 6, 24, 48])
        cost_price = st.number_input("Cost Price ($):", min_value=0.0, format="%.2f")
        sell_price = st.number_input("Selling Price ($):", min_value=0.0, format="%.2f")

        submitted = st.form_submit_button("Save Item")
        if submitted:
            if not name:
                st.error("Product Name is required!")
            else:
                final_cat = custom_cat if custom_cat else category
                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (barcode, final_cat, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price))
                conn.commit()
                conn.close()
                st.success("Product added successfully!")

elif menu_option == "Invoices Management":
    st.title("Invoices Management")
    
    with st.expander("+ Add New Invoice"):
        with st.form("add_invoice_form"):
            inv_num = st.text_input("Invoice Number:")
            inv_date = st.date_input("Date:", datetime.now())
            supplier = st.text_input("Supplier Name:")
            total_amount = st.number_input("Total Amount ($):", min_value=0.0, format="%.2f")
            status = st.selectbox("Payment Status", ["Paid", "Unpaid"])
            
            inv_submitted = st.form_submit_button("Save Invoice")
            if inv_submitted:
                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO invoices (invoice_number, date, supplier, total_amount, status, image_path, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (inv_num, str(inv_date), supplier, total_amount, status, "", ""))
                conn.commit()
                conn.close()
                st.success("Invoice saved successfully!")

    st.write("### Existing Invoices")
    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT invoice_number, date, supplier, total_amount, status FROM invoices ORDER BY id DESC")
    invoices = cursor.fetchall()
    conn.close()

    for inv in invoices:
        i_num, i_date, i_supp, i_amt, i_status = inv
        st.write(f"**Inv #:** {i_num} | **Date:** {i_date} | **Supplier:** {i_supp} | **Total:** ${i_amt:.2f} | **Status:** {i_status}")

