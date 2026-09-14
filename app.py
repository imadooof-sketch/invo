import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Inventory Management System", page_icon="📦")
st.title("Inventory and Invoicing System")

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

menu = ["View Inventory", "Add Item", "Update Stock"]
choice = st.sidebar.selectbox("Main Menu", menu)

if choice == "View Inventory":
    st.subheader("Current Inventory")
    df = pd.read_sql("SELECT * FROM inventory", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No items found in inventory.")

elif choice == "Add Item":
    st.subheader("Add New Item")
    with st.form("add_form"):
        barcode = st.text_input("Barcode")
        category = st.text_input("Category")
        name = st.text_input("Name")
        size = st.text_input("Size")
        qty_unit = st.number_input("Quantity Unit", min_value=0, step=1)
        qty_carton = st.number_input("Quantity Carton", min_value=0, step=1)
        carton_capacity = st.number_input("Carton Capacity", min_value=1, value=12, step=1)
        cost_price = st.number_input("Cost Price", min_value=0.0, step=0.1)
        
        submit = st.form_submit_button("Save Item")
        if submit:
            cursor.execute("""
                INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (barcode, category, name, size, qty_unit, qty_carton, carton_capacity, cost_price))
            conn.commit()
            st.success("Item added successfully!")

elif choice == "Update Stock":
    st.subheader("Update Item Stock")
    df = pd.read_sql("SELECT * FROM inventory", conn)
    if not df.empty:
        selected_item = st.selectbox("Select Item", df["name"].tolist())
        item_row = df[df["name"] == selected_item].iloc[0]
        
        new_unit = st.number_input("New Quantity Unit", value=int(item_row["quantity_unit"]), min_value=0, step=1)
        new_carton = st.number_input("New Quantity Carton", value=int(item_row["quantity_carton"]), min_value=0, step=1)
        
        if st.button("Update Stock"):
            cursor.execute("""
                UPDATE inventory SET quantity_unit = ?, quantity_carton = ? WHERE name = ?
            """, (new_unit, new_carton, selected_item))
            conn.commit()
            st.success("Stock updated successfully!")
    else:
        st.warning("No items available to update.")

