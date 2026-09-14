import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Inventory and Invoicing System", page_icon="📦")
st.title("Inventory and Invoicing System")

conn = sqlite3.connect("liquor_store.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL
    )
""")
conn.commit()

menu = ["View Inventory", "Add Item", "Create Invoice"]
choice = st.sidebar.selectbox("Main Menu", menu)

if choice == "View Inventory":
    st.subheader("Available Inventory")
    df = pd.read_sql("SELECT * FROM inventory", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No products registered currently.")

elif choice == "Add Item":
    st.subheader("Add New Item to Inventory")
    with st.form("add_item_form"):
        item_name = st.text_input("Item Name")
        quantity = st.number_input("Quantity", min_value=0, step=1)
        price = st.number_input("Price", min_value=0.0, step=0.5)
        submit = st.form_submit_button("Save Item")

        if submit:
            if item_name:
                cursor.execute(
                    "INSERT INTO inventory (item_name, quantity, price) VALUES (?, ?, ?)",
                    (item_name, quantity, price),
                )
                conn.commit()
                st.success(f"Item '{item_name}' added successfully!")
            else:
                st.warning("Please enter at least the item name.")

elif choice == "Create Invoice":
    st.subheader("Sales and Invoicing System")
    df = pd.read_sql("SELECT * FROM inventory", conn)

    if not df.empty:
        selected_item = st.selectbox("Select Item", df["item_name"].tolist())
        item_row = df[df["item_name"] == selected_item].iloc[0]
        available_qty = item_row["quantity"]
        item_price = item_row["price"]

        st.write(f"Price: {item_price} | Available in Stock: {available_qty}")

        sold_qty = st.number_input("Sold Quantity", min_value=1, max_value=int(available_qty), step=1)

        if st.button("Complete Sale and Update Inventory"):
            new_qty = available_qty - sold_qty
            cursor.execute(
                "UPDATE inventory SET quantity = ? WHERE item_name = ?",
                (new_qty, selected_item),
            )
            conn.commit()
            total_price = sold_qty * item_price
            st.success(
                f"Invoice completed successfully! Total amount: {total_price} | Remaining quantity of {selected_item}: {new_qty}"
            )
    else:
        st.warning("No items available to sell. Please add items first.")

