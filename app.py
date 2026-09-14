import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk
import os
import shutil
from datetime import datetime

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import cv2

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

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

def center_window(win, width, height, parent=None):
    win.update_idletasks()
    if parent and parent.winfo_exists():
        p_x = parent.winfo_rootx()
        p_y = parent.winfo_rooty()
        p_w = parent.winfo_width()
        p_h = parent.winfo_height()
        x = p_x + (p_w // 2) - (width // 2)
        y = p_y + (p_h // 2) - (height // 2)
    else:
        s_w = win.winfo_screenwidth()
        s_h = win.winfo_screenheight()
        x = (s_w // 2) - (width // 2)
        y = (s_h // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

def scan_barcode_with_camera(parent_win):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Could not open camera!", parent=parent_win)
        return None

    try:
        detector = cv2.barcode.BarcodeDetector()
    except Exception:
        detector = None

    messagebox.showinfo("Camera Scanner", "Point camera at the barcode. Press 'q' on your keyboard to close.", parent=parent_win)
    
    scanned_code = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if detector:
            retval, decoded_info, decoded_type, points = detector.detectAndDecode(frame)
            if retval and decoded_info:
                scanned_code = decoded_info[0] if isinstance(decoded_info, tuple) else decoded_info
                break

        cv2.imshow("Scan Barcode (Press Q to quit)", frame)
        if scanned_code or cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return scanned_code

class LiquorStoreApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("IDiNventory - Liquor Store Management")
        self.geometry("1100x780")
        center_window(self, 1100, 780)

        init_db()
        self.show_main_dashboard()

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_main_dashboard(self, filter_query=None, filter_type=None):
        self.clear_window()

        try:
            logo_filename = "logo.png"
            if os.path.exists(logo_filename):
                watermark_img = ctk.CTkImage(
                    light_image=Image.open(logo_filename), 
                    dark_image=Image.open(logo_filename), 
                    size=(50, 50)
                )
                lbl_watermark = ctk.CTkLabel(self, text="", image=watermark_img)
                lbl_watermark.place(relx=0.03, rely=0.95, anchor="sw")
                lbl_watermark.lower()
        except Exception as e:
            print("Watermark load error:", e)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=15)

        lbl_title = ctk.CTkLabel(top_frame, text="Store Dashboard", font=("Arial", 22, "bold"))
        lbl_title.pack(side="left")

        btn_export_pdf = ctk.CTkButton(top_frame, text="Export PDF", fg_color="#2c3e50", hover_color="#34495e", font=("Arial", 14, "bold"), width=125, height=42)
        btn_export_pdf.configure(command=self.export_inventory_pdf)
        btn_export_pdf.pack(side="right", padx=5)

        btn_print = ctk.CTkButton(top_frame, text="Print Report", fg_color="#2c3e50", hover_color="#34495e", font=("Arial", 14, "bold"), width=125, height=42)
        btn_print.configure(command=self.print_inventory_report)
        btn_print.pack(side="right", padx=5)

        btn_invoices = ctk.CTkButton(top_frame, text="Invoices", fg_color="#2c3e50", hover_color="#34495e", font=("Arial", 14, "bold"), width=115, height=42)
        btn_invoices.configure(command=lambda: self.show_invoices_window(self))
        btn_invoices.pack(side="right", padx=5)

        btn_add = ctk.CTkButton(top_frame, text="+ Add Item", fg_color="#1abc9c", hover_color="#16a085", font=("Arial", 14, "bold"), width=125, height=42)
        btn_add.configure(command=lambda: self.show_add_item_window(None))
        btn_add.pack(side="right", padx=5)

        btn_all_inventory = ctk.CTkButton(top_frame, text="Inventory (All)", fg_color="#7f8c8d", hover_color="#95a5a6", font=("Arial", 14, "bold"), width=135, height=42)
        btn_all_inventory.configure(command=lambda: self.show_main_dashboard())
        btn_all_inventory.pack(side="right", padx=5)

        total_store_value = self.calculate_total_store_cost()
        val_frame = ctk.CTkFrame(self, fg_color="#34495e", corner_radius=8)
        val_frame.pack(fill="x", padx=20, pady=5)
        lbl_store_value = ctk.CTkLabel(val_frame, text=f"Store Inventory Value: ${total_store_value:.2f}", font=("Arial", 16, "bold"), text_color="white")
        lbl_store_value.pack(pady=12, padx=15, anchor="w")

        search_frame = ctk.CTkFrame(self, fg_color=("gray92", "gray17"), corner_radius=8)
        search_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(search_frame, text="Barcode Scan / Manual:", font=("Arial", 13, "bold")).pack(anchor="w", padx=15, pady=5)
        
        bc_dash_f = ctk.CTkFrame(search_frame, fg_color="transparent")
        bc_dash_f.pack(anchor="w", padx=15, pady=5)

        self.barcode_entry = ctk.CTkEntry(bc_dash_f, placeholder_text="Scan barcode or type and press Enter...", width=320, height=38, border_width=2, font=("Arial", 12, "bold"))
        self.barcode_entry.pack(side="left", padx=2)
        self.barcode_entry.focus()
        self.barcode_entry.bind("<Return>", self.process_barcode_search)

        def dash_camera_scan():
            code = scan_barcode_with_camera(self)
            if code:
                self.barcode_entry.delete(0, tk.END)
                self.barcode_entry.insert(0, code)
                self.process_barcode_search(None)
            else:
                messagebox.showwarning("Not Detected", "No barcode detected by camera.", parent=self)

        btn_dash_cam = ctk.CTkButton(bc_dash_f, text="Scan Cam", fg_color="#34495e", hover_color="#2c3e50", font=("Arial", 12, "bold"), width=100, height=38, command=dash_camera_scan)
        btn_dash_cam.pack(side="left", padx=5)

        ctk.CTkLabel(search_frame, text="Live Search (by Name or Category):", font=("Arial", 13, "bold")).pack(anchor="w", padx=15, pady=5)
        self.search_name_entry = ctk.CTkEntry(search_frame, placeholder_text="Type item name or category to filter live...", width=420, height=38, border_width=2, font=("Arial", 12, "bold"))
        self.search_name_entry.pack(anchor="w", padx=15, pady=15)
        self.search_name_entry.bind("<KeyRelease>", self.live_search_by_name_or_category)

        ctk.CTkLabel(self, text="Inventory Items (Click Product Name for all sizes and details):", font=("Arial", 14, "bold")).pack(anchor="w", padx=25, pady=5)
        
        self.list_frame = ctk.CTkScrollableFrame(self, width=1000, height=250, corner_radius=8)
        self.list_frame.pack(padx=20, pady=5)

        self.load_inventory_items(filter_query, filter_type)

    def calculate_total_store_cost(self):
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

    def process_barcode_search(self, event):
        code = self.barcode_entry.get().strip()
        if not code:
            return

        conn = sqlite3.connect("liquor_store.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE barcode = ?", (code,))
        item = cursor.fetchone()
        conn.close()

        if item:
            self.show_product_card(item[3])
        else:
            if messagebox.askyesno("Not Found", "Barcode not found. Do you want to add it as a new item?"):
                self.show_add_item_window(prefilled_barcode=code)
        self.barcode_entry.delete(0, tk.END)

    def live_search_by_name_or_category(self, event):
        query = self.search_name_entry.get().strip()
        self.load_inventory_items(filter_query=query, filter_type="search_all")

    def load_inventory_items(self, filter_query=None, filter_type=None):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        conn = sqlite3.connect("liquor_store.db", timeout=10)
        cursor = conn.cursor()

        if filter_type == "search_all" and filter_query:
            cursor.execute("""
                SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price 
                FROM inventory 
                WHERE name LIKE ? OR category LIKE ? 
                ORDER BY name ASC
            """, (f"%{filter_query}%", f"%{filter_query}%"))
        elif filter_type == "category" and filter_query:
            cursor.execute("SELECT name, category, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory WHERE category = ? ORDER BY name ASC", (filter_query,))
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

        header_frame = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(header_frame, text="Product Name", font=("Arial", 13, "bold"), width=340, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Category", font=("Arial", 13, "bold"), width=180, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Total Purchase Cost", font=("Arial", 13, "bold"), width=220, anchor="w").pack(side="left", padx=5)

        for prod_name, total_cost in products_dict.items():
            cat = category_dict[prod_name]
            
            row_frame = ctk.CTkFrame(self.list_frame, fg_color=("gray88", "gray22"), corner_radius=6)
            row_frame.pack(fill="x", pady=4)

            btn_name = ctk.CTkButton(row_frame, text=prod_name, fg_color="transparent", hover_color=("gray75", "gray30"), text_color=("black", "white"), font=("Arial", 13, "bold"), anchor="w", width=340, command=lambda p=prod_name: self.show_product_card(p))
            btn_name.pack(side="left", padx=5)

            btn_cat = ctk.CTkButton(row_frame, text=cat, fg_color="transparent", hover_color=("gray75", "gray30"), text_color=("#2980b9", "#5dade2"), font=("Arial", 13, "bold"), anchor="w", width=180, command=lambda c=cat: self.show_main_dashboard(filter_query=c, filter_type="category"))
            btn_cat.pack(side="left", padx=5)

            formatted_cost = f"${float(total_cost):.2f}"
            ctk.CTkLabel(row_frame, text=formatted_cost, font=("Arial", 13, "bold"), width=220, anchor="w").pack(side="left", padx=5)

    def export_inventory_pdf(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"Inventory_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            title="Save Inventory PDF"
        )
        if not file_path:
            return

        try:
            conn = sqlite3.connect("liquor_store.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT name, category, size, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")
            rows = cursor.fetchall()
            conn.close()

            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter

            c.setFillColorRGB(0.15, 0.25, 0.35)
            c.rect(0, height - 70, width, 70, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(40, height - 42, "IDiNventory - INVENTORY REPORT")
            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(width - 40, height - 42, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            y = height - 100
            grand_total = 0.0

            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Product Name")
            c.drawString(200, y, "Category")
            c.drawString(300, y, "Size")
            c.drawString(370, y, "Units/Cartons")
            c.drawRightString(width - 40, y, "Cost Value")
            y -= 15
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.line(40, y, width - 40, y)
            y -= 20

            c.setFont("Helvetica-Bold", 10)
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
                c.drawString(370, y, f"U:{q_u or 0} | C:{q_c or 0} (c:{cap})")
                c.drawRightString(width - 40, y, f"${val:.2f}")
                y -= 18

            y -= 10
            c.line(40, y, width - 40, y)
            y -= 25
            c.setFont("Helvetica-Bold", 12)
            c.setFillColorRGB(0.1, 0.3, 0.2)
            c.drawString(40, y, "GRAND TOTAL STORE INVENTORY COST:")
            c.drawRightString(width - 40, y, f"${grand_total:.2f}")

            c.save()
            messagebox.showinfo("Success", f"PDF report successfully saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {e}")

    def print_inventory_report(self):
        try:
            conn = sqlite3.connect("liquor_store.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT name, category, size, quantity_unit, quantity_carton, carton_capacity, cost_price FROM inventory ORDER BY name ASC")
            rows = cursor.fetchall()
            conn.close()

            report_path = "inventory_report.txt"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("="*60 + "\n")
                f.write("         IDiNventory - OFFICIAL INVENTORY REPORT         \n")
                f.write(f"         Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}         \n")
                f.write("="*60 + "\n\n")
                
                grand_total = 0.0
                for r in rows:
                    name, cat, sz, q_u, q_c, c_cap, c_pr = r
                    cap = c_cap if c_cap and c_cap > 0 else 12
                    tot_u = (q_u or 0) + ((q_c or 0) * cap)
                    val = tot_u * (c_pr if c_pr else 0.0)
                    grand_total += val

                    f.write(f"Product: {name} | Category: {cat} | Size: {sz}\n")
                    f.write(f"Units: {q_u or 0} | Cartons: {q_c or 0} (Cap: {cap}) | Cost Value: ${val:.2f}\n")
                    f.write("-" * 60 + "\n")

                f.write(f"\nGRAND TOTAL STORE INVENTORY COST: ${grand_total:.2f}\n")
                f.write("="*60 + "\n")

            os.startfile(report_path) if os.name == "nt" else os.system(f"open {report_path}")
            
            if messagebox.askyesno("Confirm Print", "The report file has been opened for your review.\nDo you want to confirm and send this report to the printer?"):
                os.startfile(report_path, "print") if os.name == "nt" else os.system(f"lp {report_path}")
                messagebox.showinfo("Success", "Report sent to printer successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print report: {e}")

    def show_invoices_window(self, parent_window):
        inv_win = ctk.CTkToplevel(parent_window)
        inv_win.title("Invoices Management")
        center_window(inv_win, 820, 600, parent_window)
        inv_win.transient(parent_window)
        inv_win.attributes("-topmost", True)
        inv_win.lift()
        inv_win.focus_force()

        ctk.CTkLabel(inv_win, text="Invoices Management", font=("Arial", 18, "bold")).pack(pady=12)

        btn_add_inv = ctk.CTkButton(inv_win, text="+ Add New Invoice", fg_color="#2c3e50", hover_color="#34495e", font=("Arial", 13, "bold"), command=lambda: self.show_add_invoice_form(inv_win, refresh_invoices))
        btn_add_inv.pack(pady=5)

        scroll_inv = ctk.CTkScrollableFrame(inv_win, width=760, height=440, corner_radius=8)
        scroll_inv.pack(padx=20, pady=10)

        def refresh_invoices():
            for widget in scroll_inv.winfo_children():
                widget.destroy()

            conn = sqlite3.connect("liquor_store.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT id, invoice_number, date, supplier, total_amount, status, image_path, notes FROM invoices ORDER BY id DESC")
            invoices = cursor.fetchall()
            conn.close()

            for inv in invoices:
                inv_data = inv
                i_id, inv_num, inv_date, supp, amt, status, img_path, notes = inv
                
                inv_frame = ctk.CTkFrame(scroll_inv, fg_color=("gray88", "gray22"), corner_radius=6)
                inv_frame.pack(fill="x", pady=5, padx=5)

                left_text = f"Inv #: {inv_num}   |   Date: {inv_date}   |   Supplier: {supp}   |   Total: ${amt:.2f}   |   Status: "
                
                btn_inv_detail = ctk.CTkButton(
                    inv_frame, 
                    text=left_text, 
                    fg_color="transparent", 
                    hover_color=("gray75", "gray30"), 
                    text_color=("black", "white"), 
                    font=("Arial", 12, "bold"), 
                    anchor="w", 
                    width=540, 
                    command=lambda data=inv_data, p=inv_win, ref=refresh_invoices: self.show_invoice_details(data, p, ref)
                )
                btn_inv_detail.pack(side="left", padx=5, pady=10)

                status_str = status if status in ["Paid", "Unpaid"] else "Unpaid"
                status_color = "#27ae60" if status_str == "Paid" else "#e74c3c"

                btn_status = ctk.CTkButton(
                    inv_frame, 
                    text=status_str, 
                    fg_color=status_color, 
                    hover_color=status_color, 
                    text_color="white", 
                    font=("Arial", 13, "bold"), 
                    width=90, 
                    height=32,
                    command=lambda data=inv_data, p=inv_win, ref=refresh_invoices: self.show_invoice_details(data, p, ref)
                )
                btn_status.pack(side="left", padx=5, pady=10)

        refresh_invoices()

    def show_invoice_details(self, inv_data, parent_window, refresh_callback):
        i_id, inv_num, inv_date, supp, amt, status, img_path, notes = inv_data

        det_win = ctk.CTkToplevel(parent_window)
        det_win.title(f"Invoice Details: {inv_num}")
        center_window(det_win, 600, 650, parent_window)
        det_win.transient(parent_window)
        det_win.attributes("-topmost", True)
        det_win.lift()
        det_win.focus_force()

        main_container = ctk.CTkFrame(det_win, fg_color=("gray92", "gray17"), corner_radius=8)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main_container, text=f"Invoice Details (#{inv_num})", font=("Arial", 18, "bold")).pack(pady=12)

        scroll_det = ctk.CTkScrollableFrame(main_container, width=520, height=460, corner_radius=6)
        scroll_det.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_det, text="Invoice Number:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        num_e = ctk.CTkEntry(scroll_det, width=460, height=35, border_width=2, font=("Arial", 12, "bold"))
        num_e.insert(0, inv_num)
        num_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_det, text="Date (YYYY-MM-DD):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        date_e = ctk.CTkEntry(scroll_det, width=460, height=35, border_width=2, font=("Arial", 12, "bold"))
        date_e.insert(0, inv_date)
        date_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_det, text="Supplier Name:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        supp_e = ctk.CTkEntry(scroll_det, width=460, height=35, border_width=2, font=("Arial", 12, "bold"))
        supp_e.insert(0, supp)
        supp_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_det, text="Total Amount ($):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        amt_e = ctk.CTkEntry(scroll_det, width=460, height=35, border_width=2, font=("Arial", 12, "bold"))
        amt_e.insert(0, str(amt))
        amt_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_det, text="Payment Status:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        status_var = ctk.StringVar(value=status if status in ["Paid", "Unpaid"] else "Unpaid")
        
        status_menu = ctk.CTkOptionMenu(scroll_det, values=["Paid", "Unpaid"], variable=status_var, width=460, height=35, font=("Arial", 12, "bold"))
        status_menu.pack(padx=10, pady=5)

        def update_colors(*args):
            current_status = status_var.get()
            if current_status == "Paid":
                status_menu.configure(fg_color="#27ae60", button_color="#219653")
                main_container.configure(border_width=3, border_color="#27ae60")
            else:
                status_menu.configure(fg_color="#c0392b", button_color="#962d22")
                main_container.configure(border_width=3, border_color="#c0392b")

        status_var.trace_add("write", update_colors)
        update_colors()

        ctk.CTkLabel(scroll_det, text=f"Attached File/Image: {os.path.basename(img_path) if img_path else 'None'}", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=10, pady=5)

        def open_attached_file():
            if img_path and os.path.exists(img_path):
                os.startfile(img_path) if os.name == "nt" else os.system(f"open {img_path}")
            else:
                messagebox.showerror("Error", "No attachment found or file missing!", parent=det_win)

        if img_path:
            btn_open_img = ctk.CTkButton(scroll_det, text="View Attached Image / File", fg_color="#34495e", hover_color="#2c3e50", font=("Arial", 12, "bold"), command=open_attached_file, width=460, height=35)
            btn_open_img.pack(padx=10, pady=5)

        def print_invoice():
            try:
                rep_p = f"invoice_{inv_num}.txt"
                with open(rep_p, "w", encoding="utf-8") as f:
                    f.write("="*50 + "\n")
                    f.write(f"           IDiNventory - INVOICE #{inv_num}          \n")
                    f.write("="*50 + "\n\n")
                    f.write(f"Date: {date_e.get()}\n")
                    f.write(f"Supplier: {supp_e.get()}\n")
                    f.write(f"Total Amount: ${amt_e.get()}\n")
                    f.write(f"Status: {status_var.get()}\n")
                    f.write("-"*50 + "\n")
                
                os.startfile(rep_p) if os.name == "nt" else os.system(f"open {rep_p}")
                if messagebox.askyesno("Confirm Print", "Invoice file opened for review. Do you want to send it to the printer?", parent=det_win):
                    os.startfile(rep_p, "print") if os.name == "nt" else os.system(f"lp {rep_p}")
                    messagebox.showinfo("Success", "Invoice sent to printer successfully!", parent=det_win)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to print invoice: {e}", parent=det_win)

        def update_invoice():
            try:
                n_num = num_e.get().strip()
                n_date = date_e.get().strip()
                n_supp = supp_e.get().strip()
                n_amt = float(amt_e.get().strip() or 0.0)
                n_status = status_var.get()

                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE invoices SET invoice_number=?, date=?, supplier=?, total_amount=?, status=?
                    WHERE id=?
                """, (n_num, n_date, n_supp, n_amt, n_status, i_id))
                conn.commit()
                conn.close()

                refresh_callback()

                messagebox.showinfo("Success", "Invoice updated successfully!", parent=det_win)
                det_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update invoice: {e}", parent=det_win)

        btn_action_frame = ctk.CTkFrame(det_win, fg_color="transparent")
        btn_action_frame.pack(pady=10)

        btn_update = ctk.CTkButton(btn_action_frame, text="Update Invoice", fg_color="#27ae60", hover_color="#219653", font=("Arial", 13, "bold"), command=update_invoice, width=150, height=38)
        btn_update.pack(side="left", padx=5)

        btn_print_inv = ctk.CTkButton(btn_action_frame, text="Print Invoice", fg_color="#34495e", hover_color="#2c3e50", font=("Arial", 13, "bold"), command=print_invoice, width=150, height=38)
        btn_print_inv.pack(side="left", padx=5)

    def show_add_invoice_form(self, parent_win, refresh_callback):
        form_win = ctk.CTkToplevel(parent_win)
        form_win.title("Add New Invoice")
        center_window(form_win, 450, 600, parent_win)
        form_win.transient(parent_win)
        form_win.attributes("-topmost", True)
        form_win.lift()
        form_win.focus_force()

        ctk.CTkLabel(form_win, text="Invoice Details", font=("Arial", 18, "bold")).pack(pady=12)

        ctk.CTkLabel(form_win, text="Invoice Number:", font=("Arial", 12, "bold")).pack(anchor="w", padx=30)
        num_e = ctk.CTkEntry(form_win, width=350, height=35, border_width=2, font=("Arial", 12, "bold"))
        num_e.pack(padx=30, pady=5)

        ctk.CTkLabel(form_win, text="Date (YYYY-MM-DD):", font=("Arial", 12, "bold")).pack(anchor="w", padx=30)
        date_e = ctk.CTkEntry(form_win, width=350, height=35, border_width=2, font=("Arial", 12, "bold"))
        date_e.insert(0, datetime.now().strftime('%Y-%m-%d'))
        date_e.pack(padx=30, pady=5)

        ctk.CTkLabel(form_win, text="Supplier Name:", font=("Arial", 12, "bold")).pack(anchor="w", padx=30)
        supp_e = ctk.CTkEntry(form_win, width=350, height=35, border_width=2, font=("Arial", 12, "bold"))
        supp_e.pack(padx=30, pady=5)

        ctk.CTkLabel(form_win, text="Total Amount ($):", font=("Arial", 12, "bold")).pack(anchor="w", padx=30)
        amt_e = ctk.CTkEntry(form_win, width=350, height=35, border_width=2, font=("Arial", 12, "bold"))
        amt_e.pack(padx=30, pady=5)

        ctk.CTkLabel(form_win, text="Payment Status:", font=("Arial", 12, "bold")).pack(anchor="w", padx=30)
        status_var = ctk.StringVar(value="Unpaid")
        status_menu = ctk.CTkOptionMenu(form_win, values=["Paid", "Unpaid"], variable=status_var, width=350, height=35, font=("Arial", 12, "bold"))
        status_menu.pack(padx=30, pady=5)

        def update_add_colors(*args):
            if status_var.get() == "Paid":
                status_menu.configure(fg_color="#27ae60", button_color="#219653")
            else:
                status_menu.configure(fg_color="#c0392b", button_color="#962d22")

        status_var.trace_add("write", update_add_colors)
        update_add_colors()

        selected_image_path = tk.StringVar(value="")

        def browse_image():
            file_path = filedialog.askopenfilename(title="Select Invoice Image", filetypes=[("Image Files", "*.jpg *.png *.jpeg *.pdf")])
            if file_path:
                selected_image_path.set(file_path)
                messagebox.showinfo("Selected", "Invoice file attached successfully!", parent=form_win)

        btn_img = ctk.CTkButton(form_win, text="Attach Invoice Image / File", fg_color="#7f8c8d", hover_color="#95a5a6", font=("Arial", 12, "bold"), command=browse_image, width=350, height=35)
        btn_img.pack(padx=30, pady=10)

        def save_invoice():
            try:
                num = num_e.get().strip()
                dt = date_e.get().strip()
                supp = supp_e.get().strip()
                amt = float(amt_e.get().strip() or 0.0)
                status = status_var.get()
                img_src = selected_image_path.get()

                img_dest = ""
                if img_src and os.path.exists(img_src):
                    os.makedirs("invoices_docs", exist_ok=True)
                    img_dest = os.path.join("invoices_docs", os.path.basename(img_src))
                    shutil.copy(img_src, img_dest)

                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO invoices (invoice_number, date, supplier, total_amount, status, image_path, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (num, dt, supp, amt, status, img_dest, ""))
                conn.commit()
                conn.close()

                refresh_callback()

                messagebox.showinfo("Success", "Invoice saved successfully!", parent=form_win)
                form_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save invoice: {e}", parent=form_win)

        btn_save_inv = ctk.CTkButton(form_win, text="Save Invoice", fg_color="#27ae60", hover_color="#219653", font=("Arial", 13, "bold"), command=save_invoice, width=200, height=40)
        btn_save_inv.pack(pady=20)

    def show_product_card(self, product_name):
        card_win = ctk.CTkToplevel(self)
        card_win.title(f"Product File: {product_name}")
        center_window(card_win, 700, 650, self)
        card_win.attributes("-topmost", True)

        ctk.CTkLabel(card_win, text=f"Product File: {product_name}", font=("Arial", 18, "bold")).pack(pady=12)

        sizes_list = ["50", "100", "200", "375", "750", "1L", "1.75"]
        
        conn = sqlite3.connect("liquor_store.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT id, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price, barcode, category FROM inventory WHERE name = ?", (product_name,))
        db_items = cursor.fetchall()
        conn.close()

        items_by_size = {item[1]: item for item in db_items}

        scroll_sizes = ctk.CTkScrollableFrame(card_win, width=650, height=380, corner_radius=8)
        scroll_sizes.pack(padx=20, pady=5)

        header_f = ctk.CTkFrame(scroll_sizes, fg_color="transparent")
        header_f.pack(fill="x", pady=2)
        ctk.CTkLabel(header_f, text="Size", font=("Arial", 13, "bold"), width=80, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_f, text="Units", font=("Arial", 13, "bold"), width=90, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_f, text="Cartons", font=("Arial", 13, "bold"), width=90, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_f, text="Cap.", font=("Arial", 13, "bold"), width=80, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_f, text="Cost", font=("Arial", 13, "bold"), width=120, anchor="w").pack(side="left", padx=5)

        entries_data = []
        overall_product_cost = 0.0

        for sz in sizes_list:
            existing = items_by_size.get(sz)
            
            q_u = existing[2] if existing and existing[2] is not None else ""
            q_c = existing[3] if existing and existing[3] is not None else ""
            c_cap = existing[4] if existing and existing[4] is not None else 12
            c_pr = existing[5] if existing and existing[5] is not None else ""
            b_code = existing[7] if existing and existing[7] is not None else ""
            cat_val = existing[8] if existing else "Variety"
            item_id = existing[0] if existing else None

            num_u = int(q_u) if str(q_u).isdigit() else 0
            num_c = int(q_c) if str(q_c).isdigit() else 0
            num_cap = int(c_cap) if str(c_cap).isdigit() else 12
            num_cp = float(c_pr) if str(c_pr).replace('.', '', 1).isdigit() else 0.0

            tot_u = num_u + (num_c * num_cap)
            size_cost_val = tot_u * num_cp
            overall_product_cost += size_cost_val

            row_f = ctk.CTkFrame(scroll_sizes, fg_color=("gray88", "gray22"), corner_radius=6)
            row_f.pack(fill="x", pady=4)

            ctk.CTkLabel(row_f, text=sz, font=("Arial", 13, "bold"), width=80, anchor="w").pack(side="left", padx=5)

            u_entry = ctk.CTkEntry(row_f, width=90, height=32, border_width=2, font=("Arial", 12, "bold"))
            if q_u != "":
                u_entry.insert(0, str(q_u))
            u_entry.pack(side="left", padx=5)

            c_entry = ctk.CTkEntry(row_f, width=90, height=32, border_width=2, font=("Arial", 12, "bold"))
            if q_c != "":
                c_entry.insert(0, str(q_c))
            c_entry.pack(side="left", padx=5)

            cap_entry = ctk.CTkEntry(row_f, width=80, height=32, border_width=2, font=("Arial", 12, "bold"))
            cap_entry.insert(0, str(c_cap))
            cap_entry.pack(side="left", padx=5)

            cost_entry = ctk.CTkEntry(row_f, width=120, height=32, border_width=2, font=("Arial", 12, "bold"))
            if c_pr != "":
                cost_entry.insert(0, f"{num_cp:.2f}")
            cost_entry.pack(side="left", padx=5)

            entries_data.append((item_id, sz, u_entry, c_entry, cap_entry, cost_entry, b_code, cat_val))

        lbl_total_all = ctk.CTkLabel(card_win, text=f"Total Product Cost (All Sizes): ${overall_product_cost:.2f}", font=("Arial", 16, "bold"), text_color="#27ae60")
        lbl_total_all.pack(pady=10)

        def save_all_product_data():
            try:
                conn_sub = sqlite3.connect("liquor_store.db", timeout=10)
                cur_sub = conn_sub.cursor()

                for i_id, s_name, u_ent, c_ent, cap_ent, cost_ent, old_bc, cat_v in entries_data:
                    new_u = int(u_ent.get().strip() or 0)
                    new_c = int(c_ent.get().strip() or 0)
                    new_cap = int(cap_ent.get().strip() or 12)
                    new_cost = float(cost_ent.get().strip() or 0.0)

                    if i_id:
                        cur_sub.execute("UPDATE inventory SET quantity_unit=?, quantity_carton=?, carton_capacity=?, cost_price=? WHERE id=?", (new_u, new_c, new_cap, new_cost, i_id))
                    else:
                        cur_sub.execute("""
                            INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0)
                        """, (old_bc, cat_v, product_name, s_name, new_u, new_c, new_cap, new_cost))

                conn_sub.commit()
                conn_sub.close()
                messagebox.showinfo("Success", "All product sizes updated successfully!", parent=card_win)
                card_win.destroy()
                self.show_product_card(product_name)
                self.load_inventory_items()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}", parent=card_win)

        btn_save_all = ctk.CTkButton(card_win, text="Save Changes", fg_color="#27ae60", hover_color="#219653", font=("Arial", 13, "bold"), width=220, height=40, command=save_all_product_data)
        btn_save_all.pack(pady=10)

    def show_add_item_window(self, prefilled_barcode):
        add_win = ctk.CTkToplevel(self)
        add_win.title("Add New Item")
        center_window(add_win, 480, 720, self)
        add_win.attributes("-topmost", True)

        scroll_add = ctk.CTkScrollableFrame(add_win, width=440, height=620, corner_radius=8)
        scroll_add.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(scroll_add, text="Add Item to Inventory", font=("Arial", 18, "bold")).pack(pady=12)

        ctk.CTkLabel(scroll_add, text="Barcode (Scan / Type / Camera):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        
        bc_frame = ctk.CTkFrame(scroll_add, fg_color="transparent")
        bc_frame.pack(fill="x", padx=10, pady=5)

        barcode_e = ctk.CTkEntry(bc_frame, width=260, height=35, border_width=2, font=("Arial", 12, "bold"))
        barcode_e.pack(side="left", padx=2)
        if prefilled_barcode:
            barcode_e.insert(0, prefilled_barcode)

        def add_camera_scanner():
            code = scan_barcode_with_camera(add_win)
            if code:
                barcode_e.delete(0, tk.END)
                barcode_e.insert(0, code)
            else:
                messagebox.showwarning("Not Detected", "No barcode detected by camera.", parent=add_win)

        btn_cam = ctk.CTkButton(bc_frame, text="Scan Cam", fg_color="#34495e", hover_color="#2c3e50", font=("Arial", 11, "bold"), width=110, height=35, command=add_camera_scanner)
        btn_cam.pack(side="left", padx=5)

        ctk.CTkLabel(scroll_add, text="Category:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        categories = ["Cognac", "Whisky", "Brandy", "Rum", "Vodka", "Tequila", "Liquor", "Variety"]
        category_var = ctk.StringVar(value=categories[0])
        category_menu = ctk.CTkOptionMenu(scroll_add, values=categories, variable=category_var, width=380, height=35, font=("Arial", 12, "bold"))
        category_menu.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Or Type New Category (Optional):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        new_category_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, placeholder_text="Type custom category if needed...", font=("Arial", 12, "bold"))
        new_category_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Product Name:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        name_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, font=("Arial", 12, "bold"))
        name_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Size (7 standard measurements):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        sizes = ["50", "100", "200", "375", "750", "1L", "1.75"]
        size_var = ctk.StringVar(value=sizes[4])
        size_menu = ctk.CTkOptionMenu(scroll_add, values=sizes, variable=size_var, width=380, height=35, font=("Arial", 12, "bold"))
        size_menu.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Quantity (Units):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        qty_unit_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, font=("Arial", 12, "bold"))
        qty_unit_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Quantity (Cartons):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        qty_carton_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, font=("Arial", 12, "bold"))
        qty_carton_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Carton Capacity (Pieces per Carton):", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        capacities = ["12", "6", "24", "48"]
        cap_var = ctk.StringVar(value=capacities[0])
        cap_menu = ctk.CTkOptionMenu(scroll_add, values=capacities, variable=cap_var, width=380, height=35, font=("Arial", 12, "bold"))
        cap_menu.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Or Type Custom Carton Capacity:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        custom_cap_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, placeholder_text="Type custom number if needed...", font=("Arial", 12, "bold"))
        custom_cap_e.pack(padx=10, pady=5)

        cost_var = ctk.StringVar(value="")
        sell_var = ctk.StringVar(value="")

        def format_price(var):
            val = var.get()
            if not val:
                return
            text = "".join([c for c in val if c.isdigit()])
            if not text:
                var.set("")
                return
            value = int(text) / 100.0
            formatted = f"{value:.2f}"
            if var.get() != formatted:
                var.set(formatted)

        cost_var.trace_add("write", lambda *args: format_price(cost_var))
        sell_var.trace_add("write", lambda *args: format_price(sell_var))

        ctk.CTkLabel(scroll_add, text="Cost Price:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        cost_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, textvariable=cost_var, font=("Arial", 12, "bold"))
        cost_e.pack(padx=10, pady=5)

        ctk.CTkLabel(scroll_add, text="Selling Price:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
        sell_e = ctk.CTkEntry(scroll_add, width=380, height=35, border_width=2, textvariable=sell_var, font=("Arial", 12, "bold"))
        sell_e.pack(padx=10, pady=5)

        def save_item():
            conn = None
            try:
                b_code = barcode_e.get().strip()
                custom_cat = new_category_e.get().strip()
                cat = custom_cat if custom_cat else category_var.get()
                
                nam = name_e.get().strip()
                siz = size_var.get()
                q_unit = int(qty_unit_e.get().strip() or 0)
                q_carton = int(qty_carton_e.get().strip() or 0)
                
                cust_cap = custom_cap_e.get().strip()
                carton_cap = int(cust_cap) if cust_cap.isdigit() else int(cap_var.get())

                c_price = float(cost_var.get() or 0.0)
                s_price = float(sell_var.get() or 0.0)

                if not nam:
                    messagebox.showerror("Error", "Product Name is required!", parent=add_win)
                    return

                conn = sqlite3.connect("liquor_store.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory (barcode, category, name, size, quantity_unit, quantity_carton, carton_capacity, cost_price, sell_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b_code, cat, nam, siz, q_unit, q_carton, carton_cap, c_price, s_price))
                
                conn.commit()
                conn.close()

                messagebox.showinfo("Success", "Product file created / updated successfully!", parent=add_win)
                add_win.destroy()
                self.show_main_dashboard()
            except ValueError:
                if conn:
                    conn.close()
                messagebox.showerror("Error", "Please enter valid numbers for quantities and prices!", parent=add_win)
            except Exception as e:
                if conn:
                    conn.close()
                messagebox.showerror("Error", f"An error occurred while saving: {e}", parent=add_win)

        btn_save = ctk.CTkButton(scroll_add, text="Save Item", fg_color="#27ae60", hover_color="#219653", font=("Arial", 13, "bold"), command=save_item, width=220, height=40)
        btn_save.pack(pady=20)

        form_fields = [barcode_e, new_category_e, name_e, qty_unit_e, qty_carton_e, custom_cap_e, cost_e, sell_e]

        def focus_next(event):
            widget = event.widget
            if widget in form_fields:
                idx = form_fields.index(widget)
                next_widget = form_fields[(idx + 1) % len(form_fields)]
                next_widget.focus_set()
                return "break"

        def focus_prev(event):
            widget = event.widget
            if widget in form_fields:
                idx = form_fields.index(widget)
                prev_widget = form_fields[(idx - 1) % len(form_fields)]
                prev_widget.focus_set()
                return "break"

        for field in form_fields:
            field.bind("<Return>", focus_next)
            field.bind("<Tab>", focus_next)
            field.bind("<Down>", focus_next)
            field.bind("<Up>", focus_prev)

        btn_save.bind("<Return>", lambda e: save_item())

if __name__ == "__main__":
    app = LiquorStoreApp()
    app.mainloop()

