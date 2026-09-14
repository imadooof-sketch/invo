import sqlite3
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import os
from datetime import datetime

# إعداد صفحة الويب
st.set_page_config(page_title="IDiNventory - Store Management", page_icon="📦", layout="wide")

# تنسيق CSS مخصص لتحسين مظهر الواجهة وتناسبها مع الويب
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 6px; height: 2.8em; font-weight: bold; }
    .metric-card { background-color: #34495e; padding: 15px; border-radius: 8px; color: white; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# تهيئة قاعدة البيانات SQLite
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

# حساب إجمالي قيمة المخزون في المتجر
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

# رأس الصفحة ولوحة التحكم الرئيسية
st.markdown("### Store Dashboard")
total_store_value = calculate_total_store_cost()

st.markdown(f"""
    <div class="metric-card">
        <h3 style='margin:0; color: white;'>Store Inventory Value: ${total_store_value:,.2f}</h3>
    </div>
""", unsafe_allow_html=True)

# الأزرار الرئيسية العلوية
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

# حالة التنقل بين الأقسام عبر الـ Session State
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

# 1. لوحة التحكم الرئيسية وعرض المخزون والبحث
if st.session_state.page == "dashboard":
    st.markdown("#### Barcode Scan / Manual & Live Search")
    
    search_col1, search_col2 = st.columns(2)
    with search_col1:
        barcode_input = st.text_input("Scan Barcode or Type SKU", placeholder="Scan barcode and press Enter...")
    with search_col2:
        search_input = st.text_input("Live Search (Name or Category)", placeholder="Type item name or category...")

    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()

    if barcode_input:
        cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory WHERE barcode = ? ORDER BY name ASC", (barcode_input.strip(),))
    elif search_input:
        cursor.execute("""
            SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price 
            FROM inventory 
            WHERE name LIKE ? OR category LIKE ? 
            ORDER BY name ASC
        """, (f"%{search_input}%", f"%{search_input}%"))
    else:
        cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")

    rows = cursor.fetchall()
    conn.close()

    # تجميع المنتجات بناءً على الاسم وتجميع التكاليف
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

    st.markdown("#### Inventory Items List")
    if products_dict:
        data_list = []
        for prod_name, total_cost in products_dict.items():
            cat = category_dict[prod_name]
            data_list.append({"Product Name": prod_name, "Category": cat, "Total Purchase Cost": f"${total_cost:,.2f}"})
        
        df_display = pd.DataFrame(data_list)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No inventory items found.")

# 2. إضافة منتج جديد
elif st.session_state.page == "add_item":
    st.subheader("Add New Item to Inventory")
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

# 3. إدارة الفواتير
elif st.session_state.page == "invoices":
    st.subheader("Invoices Management")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    with st.form("add_invoice_web"):
        st.markdown("#### Add New Invoice")
        inv_num = st.text_input("Invoice Number")
        inv_date = st.text_date_input if hasattr(st, 'text_date_input') else st.text_input("Date (YYYY-MM-DD)", value=datetime.now().strftime('%Y-%m-%d'))
        supplier = st.text_input("Supplier Name")
        total_amount = st.number_input("Total Amount ($)", min_value=0.0, step=0.1)
        status = st.selectbox("Payment Status", ["Unpaid", "Paid"])
        
        inv_submit = st.form_submit_button("Save Invoice")
        if inv_submit:
            if inv_num.strip():
                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO invoices (invoice_number, date, supplier, total_amount, status, image_path, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (inv_num, inv_date, supplier, total_amount, status, "", ""))
                conn.commit()
                conn.close()
                st.success("Invoice saved successfully!")
            else:
                st.error("Invoice Number is required!")

    st.markdown("#### Existing Invoices")
    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT invoice_number, date, supplier, total_amount, status FROM invoices ORDER BY id DESC")
    inv_rows = cursor.fetchall()
    conn.close()

    if inv_rows:
        df_inv = pd.DataFrame(inv_rows, columns=["Invoice #", "Date", "Supplier", "Total Amount", "Status"])
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("No invoices found.")

# 4. طباعة التقرير
elif st.session_state.page == "print_report":
    st.subheader("Inventory Official Report")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    conn = sqlite3.connect("liquor_store.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, size, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        report_data = []
        grand_total = 0.0
        for r in rows:
            name, cat, sz, q_u, q_c, c_cap, c_pr = r
            cap = c_cap if c_cap and c_cap > 0 else 12
            tot_u = (q_u or 0) + ((q_c or 0) * cap)
            val = tot_u * (c_pr if c_pr else 0.0)
            grand_total += val
            report_data.append({
                "Product": name, "Category": cat, "Size": sz, 
                "Units": q_u or 0, "Cartons": q_c or 0, "Cost Value": f"${val:.2f}"
            })
        
        st.dataframe(pd.DataFrame(report_data), use_container_width=True, hide_index=True)
        st.markdown(f"### Grand Total Store Inventory Cost: ${grand_total:,.2f}")
    else:
        st.info("No inventory data available for reporting.")

# 5. تصدير ملف PDF
elif st.session_state.page == "export_pdf":
    st.subheader("Export Inventory PDF")
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button("Generate & Download PDF Report"):
        try:
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

            c.setFillColorRGB(0.15, 0.25, 0.35)
            c.rect(0, height - 70, width, 70, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(40, height - 42, "IDiNventory - INVENTORY REPORT")
            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(width - 40, height - 42, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

            conn = sqlite3.connect("liquor_store.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT name, category, size, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")
            rows = cursor.fetchall()
            conn.close()

            y = height - 100
            grand_total = 0.0

            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Product Name")
            c.drawString(200, y, "Category")
            c.drawString(300, y, "Size")
            c.drawString(370, y, "Units/Cartons")
            c.drawRightString(width - 40, y, "Cost Value")
            y -= 20

            for r in rows:
                if y < 60:
                    c.showPage()
                    y = height - 60
                name, cat, sz, q_u, q_c, c_cap, c_pr = r
                cap = c_cap if c_cap and c_cap > 0 else 12
                tot_u = (q_u or 0) + ((q_c or 0) * cap)
                val = tot_u * (c_pr if c_pr else 0.0)
                grand_total += val

                c.drawString(40, y, str(name)[:25])
                c.drawString(200, y, str(cat)[:15])
                c.drawString(300, y, str(sz))
                c.drawString(370, y, f"U:{q_u or 0} | C:{q_c or 0}")
                c.drawRightString(width - 40, y, f"${val:.2f}")
                y -= 18

            y -= 10
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, y, f"GRAND TOTAL: ${grand_total:.2f}")
            c.save()
            buffer.seek(0)

            st.download_button(
                label="Click here to download PDF file",
                data=buffer,
                file_name=f"Inventory_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")

