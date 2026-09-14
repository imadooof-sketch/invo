import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# إعدادات صفحة ستريمليت
st.set_page_icon("📦")
st.title("برنامج المخزون والفواتير")

# الاتصال بقاعدة البيانات المحليّة
conn = sqlite3.connect("liquor_store.db", check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجدول إذا لم يكن موجوداً
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL
    )
"""
)
conn.commit()

# القائمة الجانبية للتنقل
menu = ["عرض المخزون", "إضافة منتج", "إنشاء فاتورة"]
choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

if choice == "عرض المخزون":
  st.subheader("المنتجات المتوفرة في المخزون")
  df = pd.read_sql("SELECT * FROM inventory", conn)
  if not df.empty:
    st.dataframe(df, use_container_width=True)
  else:
    st.info("لا توجد منتجات مسجلة حالياً.")

elif choice == "إضافة منتج":
  st.subheader("إضافة منتج جديد للمخزون")
  with st.form("add_item_form"):
    item_name = st.text_input("اسم المنتج")
    quantity = st.number_input("الكمية", min_value=0, step=1)
    price = st.number_input("السعر", min_value=0.0, step=0.5)
    submit = st.form_submit_button("حفظ المنتج")

    if submit:
      if item_name:
        cursor.execute(
            "INSERT INTO inventory (item_name, quantity, price) VALUES"
            " (?, ?, ?)",
            (item_name, quantity, price),
        )
        conn.commit()
        st.success(f"تم إضافة المنتج '{item_name}' بنجاح!")
      else:
        st.warning("الرجاء إدخال اسم المنتج على الأقل.")

elif choice == "إنشاء فاتورة":
  st.subheader("نظام الفواتير والمبيعات")
  df = pd.read_sql("SELECT * FROM inventory", conn)

  if not df.empty:
    selected_item = st.selectbox(
        "اختر المنتج", df["item_name"].tolist()
    )
    item_row = df[df["item_name"] == selected_item].iloc[0]
    available_qty = item_row["quantity"]
    item_price = item_row["price"]

    st.write(f"السعر: {item_price} | المتوفر في المخزون: {available_qty}")

    sold_qty = st.number_input(
        "الكمية المباعة", min_value=1, max_value=int(available_qty), step=1
    )

    if st.button("إتمام البيع وتحديث المخزون"):
      new_qty = available_qty - sold_qty
      cursor.execute(
          "UPDATE inventory SET quantity = ? WHERE item_name = ?",
          (new_qty, selected_item),
      )
      conn.commit()
      total_price = sold_qty * item_price
      st.success(
          f"تم إتمام الفاتورة بنجاح! الإجمالي المطلوب: {total_price} | الكمية"
          f" المتبقية من {selected_item} هي: {new_qty}"
      )
  else:
    st.warning("لا توجد منتجات لبيعها، قم بإضافة منتجات أولاً.")

