import json
import os
import csv
import math
import sys
import textwrap
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, simpledialog, colorchooser


APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(APP_DIR) if os.path.basename(APP_DIR).lower() == "outputs" else APP_DIR
DATA_DIR = os.path.join(PROJECT_DIR, "work", "pos_data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
MENU_FILE = os.path.join(APP_DIR, "menu.json")

DEFAULT_SETTINGS = {
    "language": "zh", "tax_rate": 0.05, "currency": "TWD",
    "history_password": "1234",
    "system_font": "Segoe UI", "system_font_size": 10,
    "menu_font": "Segoe UI", "menu_font_size": 10,
    "floating_order": False,
    "rates": {"TWD": 1.0, "USD": 0.031, "HKD": 0.242, "JPY": 4.62},
    "tip_options": [0, 0.05, 0.10, 0.15], "theme": "#f4f6f8",
    "receipt_header": "好味道餐廳\nThank you for dining with us", "receipt_width": 38,
    "show_tax": True, "show_tip": True,
}

TEXT = {
    "zh": {"title": "好味道｜點餐收銀系統", "menu": "菜單", "cart": "目前訂單", "qty": "數量", "price": "單價", "subtotal": "小計", "tax": "稅額", "tip": "小費", "total": "應付合計", "pay": "結帳 (F9)", "clear": "清空 (F4)", "settings": "系統設定 (F2)", "stats": "業績統計", "print": "列印收據 (Ctrl+P)", "split": "AA制分單", "currency": "幣別", "cash": "收款", "change": "找零", "add": "加入", "tip_rate": "小費比例", "guide": "操作提示", "completed": "已完成訂單", "sales": "營業額", "tip_total": "小費總額", "close": "關閉", "save": "儲存", "category": "分類", "all": "全部", "empty": "尚未加入餐點", "success": "交易完成", "name": "餐點名稱"},
    "en": {"title": "Good Taste | Restaurant POS", "menu": "Menu", "cart": "Current order", "qty": "Qty", "price": "Unit price", "subtotal": "Subtotal", "tax": "Tax", "tip": "Tip", "total": "Total", "pay": "Checkout (F9)", "clear": "Clear (F4)", "settings": "Settings (F2)", "stats": "Sales stats", "print": "Print receipt (Ctrl+P)", "split": "Split AA", "currency": "Currency", "cash": "Cash received", "change": "Change", "add": "Add", "tip_rate": "Tip rate", "guide": "Quick guide", "completed": "Completed orders", "sales": "Sales", "tip_total": "Tips", "close": "Close", "save": "Save", "category": "Category", "all": "All", "empty": "No items yet", "success": "Payment complete", "name": "Item name"},
}

MENU = [
    ("主食", "Rice Bowl", 120, "", ""), ("主食", "Beef Noodles", 160, "", ""), ("主食", "Vegetable Pasta", 150, "", ""),
    ("小食", "French Fries", 70, "", ""), ("小食", "Fried Chicken", 110, "", ""), ("小食", "Salad", 90, "", ""),
    ("飲品", "Cola", 35, "", ""), ("飲品", "Coffee", 80, "", ""), ("飲品", "Fresh Juice", 100, "", ""),
    ("甜點", "Cheesecake", 120, "", ""), ("甜點", "Ice Cream", 85, "", ""),
]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_menu():
    """Load menu items from menu.json; fall back to the sample menu if needed."""
    raw = load_json(MENU_FILE, None)
    if not isinstance(raw, list):
        return MENU.copy()
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            category = item["category"]
            name = item["name"]
            price = float(item["price"])
            image = str(item.get("image", "")).strip()
            if category and name and price >= 0:
                result.append((category, name, price, image, str(item.get("barcode", "")).strip()))
        except (KeyError, TypeError, ValueError):
            continue
    return result or MENU.copy()


def localized(value, language):
    if isinstance(value, dict):
        return str(value.get(language) or value.get("zh") or value.get("en") or "")
    return str(value)


def display_width(value):
    return sum(2 if ord(char) > 255 else 1 for char in str(value))


def fit_receipt_text(value, width):
    result = ""
    used = 0
    for char in str(value):
        char_width = 2 if ord(char) > 255 else 1
        if used + char_width > width: break
        result += char; used += char_width
    return result + (" " * max(0, width - used))


class POSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = {**DEFAULT_SETTINGS, **load_json(SETTINGS_FILE, {})}
        self.settings["rates"] = {**DEFAULT_SETTINGS["rates"], **self.settings.get("rates", {})}
        self.orders = load_json(ORDERS_FILE, [])
        self.menu = load_menu()
        self.cart = {}
        self.lang = self.settings.get("language", "zh")
        self.current_category = "全部"
        self.tip_rate = 0
        self.menu_images = []
        self.floating_order_win = None
        self.current_order_no = self.next_order_no()
        self.title(self.t("title")); self.geometry("1180x720"); self.resizable(False, False); self.protocol("WM_DELETE_WINDOW", self.request_exit)
        try: self.overrideredirect(True); self.attributes("-fullscreen", True)
        except tk.TclError: self.state("zoomed")
        self.configure(bg=self.settings.get("theme", "#f4f6f8"))
        self.make_style(); self.build_ui(); self.bind_shortcuts()
        if self.settings.get("floating_order", False): self.after(300, self.open_floating_order)
        self.after(250, self.show_guide)

    def t(self, key): return TEXT[self.lang].get(key, key)
    def request_exit(self):
        password = simpledialog.askstring("Password", "請輸入離開密碼 / Exit password", show="*", parent=self)
        if password is None: return
        if password != self.settings.get("history_password", "1234"):
            messagebox.showerror("", "密碼錯誤 / Incorrect password", parent=self); return
        self.destroy()
    def protected_action(self, action):
        password = simpledialog.askstring("Password", "請輸入管理密碼 / Admin password", show="*", parent=self)
        if password is None: return
        if password != self.settings.get("history_password", "1234"):
            messagebox.showerror("", "密碼錯誤 / Incorrect password", parent=self); return
        action()
    def make_style(self):
        s = ttk.Style(self); s.theme_use("clam")
        self.apply_theme(s)
        base_font = self.settings.get("system_font", "Segoe UI"); base_size = int(self.settings.get("system_font_size", 10))
        s.configure("Header.TLabel", font=(base_font, base_size + 8, "bold"))
        s.configure("Card.TFrame", background="white", relief="groove", borderwidth=1)
        s.configure("TButton", padding=7, font=(base_font, base_size))

    def apply_theme(self, style=None):
        color = self.settings.get("theme", "#f4f6f8")
        self.configure(bg=color)
        style = style or ttk.Style(self)
        style.configure("TFrame", background=color)
        style.configure("TLabel", background=color, font=(self.settings.get("system_font", "Segoe UI"), int(self.settings.get("system_font_size", 10))))
        style.configure("TLabelframe", background=color)
        style.configure("TLabelframe.Label", background=color)
        style.configure("TCheckbutton", background=color)

    def build_ui(self):
        for w in self.winfo_children(): w.destroy()
        top = ttk.Frame(self); top.pack(fill="x", padx=16, pady=(14, 8))
        ttk.Label(top, text=self.t("title"), style="Header.TLabel").pack(side="left")
        ttk.Button(top, text="離開 / Exit", command=self.request_exit).pack(side="right", padx=4)
        ttk.Button(top, text="中 / EN", command=self.toggle_language).pack(side="right", padx=4)
        ttk.Button(top, text="計算機 / Calc", command=self.show_calculator).pack(side="right", padx=4)
        ttk.Button(top, text="菜單編輯 / Edit", command=lambda: self.protected_action(self.show_menu_editor)).pack(side="right", padx=4)
        ttk.Button(top, text="歷史訂單 / History", command=lambda: self.protected_action(self.show_order_history)).pack(side="right", padx=4)
        ttk.Button(top, text=self.t("stats"), command=lambda: self.protected_action(self.show_stats)).pack(side="right", padx=4)
        ttk.Button(top, text=self.t("settings"), command=lambda: self.protected_action(self.show_settings)).pack(side="right", padx=4)
        main = ttk.Frame(self); main.pack(fill="both", expand=True, padx=16, pady=8)
        main.columnconfigure(0, weight=2, uniform="pos_columns"); main.columnconfigure(1, weight=1, uniform="pos_columns"); main.rowconfigure(0, weight=1)
        left = ttk.Frame(main, style="Card.TFrame", padding=12); left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ttk.Frame(main, style="Card.TFrame", padding=12); right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(left, text=self.t("menu"), style="Header.TLabel").pack(anchor="w")
        scan = ttk.Frame(left); scan.pack(fill="x", pady=(6, 2))
        ttk.Label(scan, text="條碼 / Barcode").pack(side="left")
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(scan, textvariable=self.barcode_var, width=18)
        self.barcode_entry.pack(side="left", padx=6)
        self.barcode_entry.bind("<Return>", self.add_by_barcode)
        ttk.Button(scan, text="加入", command=self.add_by_barcode).pack(side="left")
        cats = ["全部"] + sorted(set(localized(x[0], self.lang) for x in self.menu))
        self.cat_var = tk.StringVar(value=self.current_category)
        ttk.Combobox(left, textvariable=self.cat_var, values=cats, state="readonly", width=15).pack(anchor="w", pady=8)
        self.cat_var.trace_add("write", lambda *_: self.render_menu())
        menu_area = ttk.Frame(left); menu_area.pack(fill="both", expand=True)
        self.menu_canvas = tk.Canvas(menu_area, highlightthickness=0, background="white")
        menu_scroll = ttk.Scrollbar(menu_area, orient="vertical", command=self.menu_canvas.yview)
        self.menu_canvas.configure(yscrollcommand=menu_scroll.set)
        menu_scroll.pack(side="right", fill="y"); self.menu_canvas.pack(side="left", fill="both", expand=True)
        self.menu_frame = ttk.Frame(self.menu_canvas); self.menu_window = self.menu_canvas.create_window((0, 0), window=self.menu_frame, anchor="nw")
        self.menu_frame.bind("<Configure>", lambda event: self.menu_canvas.configure(scrollregion=self.menu_canvas.bbox("all")))
        self.menu_canvas.bind("<Configure>", lambda event: self.menu_canvas.itemconfigure(self.menu_window, width=event.width))
        self.menu_canvas.bind_all("<MouseWheel>", lambda event: self.menu_canvas.yview_scroll(int(-event.delta / 120), "units"))
        self.render_menu()
        order_header = ttk.Frame(right); order_header.pack(fill="x")
        ttk.Label(order_header, text=self.t("cart"), style="Header.TLabel").pack(side="left")
        self.order_no_var = tk.StringVar(value=f"NO. {self.current_order_no}")
        ttk.Label(order_header, textvariable=self.order_no_var, font=(self.settings.get("system_font", "Segoe UI"), int(self.settings.get("system_font_size", 10)), "bold"), foreground="#b91c1c").pack(side="right", pady=5)
        columns = ("name", "qty", "price", "sum")
        self.tree = ttk.Treeview(right, columns=columns, show="headings", height=13)
        heads = [self.t("name"), self.t("qty"), self.t("price"), self.t("subtotal")]
        for c, h in zip(columns, heads): self.tree.heading(c, text=h); self.tree.column(c, width=105, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=8)
        btns = ttk.Frame(right); btns.pack(fill="x")
        ttk.Button(btns, text="＋", width=4, command=lambda: self.change_selected(1)).pack(side="left")
        ttk.Button(btns, text="－", width=4, command=lambda: self.change_selected(-1)).pack(side="left", padx=4)
        ttk.Button(btns, text=self.t("clear"), command=self.clear_cart).pack(side="right")
        pay = ttk.Frame(right); pay.pack(fill="x", pady=(10, 0))
        self.currency_var = tk.StringVar(value=self.settings.get("currency", "TWD"))
        ttk.Label(pay, text=self.t("currency")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(pay, textvariable=self.currency_var, values=list(self.settings["rates"].keys()), state="readonly", width=8).grid(row=0, column=1, padx=5)
        self.tip_var = tk.StringVar(value="0%")
        ttk.Label(pay, text=self.t("tip_rate")).grid(row=0, column=2, sticky="e")
        ttk.Combobox(pay, textvariable=self.tip_var, values=[f"{int(x*100)}%" for x in self.settings.get("tip_options", [0, .05, .1, .15])], state="readonly", width=7).grid(row=0, column=3, padx=5)
        self.tip_var.trace_add("write", lambda *_: self.update_totals())
        self.total_var = tk.StringVar(); self.detail_var = tk.StringVar()
        ttk.Label(right, textvariable=self.detail_var, justify="right").pack(anchor="e", pady=(10, 0))
        ttk.Label(right, textvariable=self.total_var, font=("Segoe UI", 18, "bold")).pack(anchor="e")
        ttk.Button(right, text=self.t("split"), command=self.split_bill).pack(side="left", pady=10)
        ttk.Button(right, text=self.t("print"), command=self.print_receipt).pack(side="left", padx=6, pady=10)
        ttk.Button(right, text=self.t("pay"), command=self.checkout).pack(side="right", pady=10)
        self.update_totals()

    def render_menu(self):
        for w in self.menu_frame.winfo_children(): w.destroy()
        cat = self.cat_var.get() if hasattr(self, "cat_var") else "全部"
        items = sorted([x for x in self.menu if cat == "全部" or localized(x[0], self.lang) == cat], key=lambda x: (localized(x[0], self.lang), localized(x[1], self.lang)))
        self.menu_images = []
        style = ttk.Style(self); style.configure("Menu.TButton", font=(self.settings.get("menu_font", "Segoe UI"), int(self.settings.get("menu_font_size", 10))))
        category_colors = ["#e8f1ff", "#fff1dc", "#e6f7ed", "#f1e8ff", "#e8f7f7", "#fff0f0", "#f5f0df"]
        categories = sorted(set(localized(x[0], self.lang) for x in self.menu))
        category_styles = {}
        for index, category in enumerate(categories):
            style_name = f"Menu{index}.TButton"; category_styles[category] = style_name
            color = category_colors[index % len(category_colors)]; style.configure(style_name, font=(self.settings.get("menu_font", "Segoe UI"), int(self.settings.get("menu_font_size", 10))), background=color, foreground="#202124", padding=7)
        for i, (group, raw_name, price, image_path, barcode) in enumerate(items):
            name = localized(raw_name, self.lang)
            image = None
            if image_path:
                full_path = image_path if os.path.isabs(image_path) else os.path.join(APP_DIR, image_path)
                try:
                    image = tk.PhotoImage(file=full_path)
                    image = image.subsample(max(1, image.width() // 100), max(1, image.height() // 70))
                    self.menu_images.append(image)
                except tk.TclError:
                    image = None
            b = ttk.Button(self.menu_frame, text=f"{name}\n${price:,.0f}", image=image, compound="top", style=category_styles.get(localized(group, self.lang), "Menu.TButton"), command=lambda n=name, p=price: self.add_item(n, p))
            b.grid(row=i//4, column=i%4, sticky="nsew", padx=5, pady=5, ipadx=10, ipady=12)
        for col in range(4): self.menu_frame.columnconfigure(col, weight=1)

    def add_item(self, name, price):
        self.cart[name] = self.cart.get(name, {"price": price, "qty": 0}); self.cart[name]["qty"] += 1; self.refresh_cart()
    def next_order_no(self):
        today = datetime.now().strftime("%Y%m%d"); numbers = []
        for order in self.orders:
            order_no = str(order.get("order_no", ""))
            if order_no.startswith(today + "-"):
                try: numbers.append(int(order_no.rsplit("-", 1)[1]))
                except ValueError: pass
        return f"{today}-{(max(numbers) + 1 if numbers else 0):04d}"
    def add_by_barcode(self, event=None):
        code = self.barcode_var.get().strip()
        for category, raw_name, price, image_path, barcode in self.menu:
            if barcode and barcode == code:
                self.add_item(localized(raw_name, self.lang), price)
                self.barcode_var.set(""); self.barcode_entry.focus_set(); return
        if code: messagebox.showwarning("Barcode", f"找不到條碼 / Barcode not found: {code}")
        self.barcode_var.set(""); self.barcode_entry.focus_set()
    def refresh_cart(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        for name, x in self.cart.items(): self.tree.insert("", "end", iid=name, values=(name, x["qty"], f"{x['price']:,}", f"{x['price']*x['qty']:,}"))
        self.update_totals()
        self.refresh_floating_order()
    def open_floating_order(self):
        if self.floating_order_win and self.floating_order_win.winfo_exists(): return
        win = self.floating_order_win = tk.Toplevel(self); win.title("目前訂單 / Current Order"); win.geometry("480x720"); win.resizable(False, False); win.protocol("WM_DELETE_WINDOW", self.close_floating_order)
        ttk.Label(win, text="目前訂單 / Current Order", style="Header.TLabel").pack(anchor="w", padx=14, pady=12)
        ttk.Label(win, text="菜單點餐 / Menu", font=(self.settings.get("system_font", "Segoe UI"), 11, "bold")).pack(anchor="w", padx=14)
        menu_area = ttk.Frame(win, height=225); menu_area.pack(fill="x", padx=14, pady=5); menu_area.pack_propagate(False)
        menu_canvas = tk.Canvas(menu_area, background="white", highlightthickness=0); menu_scroll = ttk.Scrollbar(menu_area, orient="vertical", command=menu_canvas.yview); menu_canvas.configure(yscrollcommand=menu_scroll.set); menu_scroll.pack(side="right", fill="y"); menu_canvas.pack(side="left", fill="both", expand=True)
        floating_menu = ttk.Frame(menu_canvas); menu_window = menu_canvas.create_window((0, 0), window=floating_menu, anchor="nw")
        floating_menu.bind("<Configure>", lambda event: menu_canvas.configure(scrollregion=menu_canvas.bbox("all"))); menu_canvas.bind("<Configure>", lambda event: menu_canvas.itemconfigure(menu_window, width=event.width))
        floating_items = sorted(self.menu, key=lambda x: (localized(x[0], self.lang), localized(x[1], self.lang)))
        for index, (category, raw_name, price, image_path, barcode) in enumerate(floating_items):
            name = localized(raw_name, self.lang); ttk.Button(floating_menu, text=f"{name}\n${price:,.0f}", style="Menu.TButton", command=lambda n=name, p=price: self.add_item(n, p)).grid(row=index//3, column=index%3, sticky="nsew", padx=3, pady=3, ipadx=4, ipady=5)
        for col in range(3): floating_menu.columnconfigure(col, weight=1)
        ttk.Separator(win).pack(fill="x", padx=14, pady=5)
        ttk.Label(win, text="訂單內容 / Order Items", font=(self.settings.get("system_font", "Segoe UI"), 11, "bold")).pack(anchor="w", padx=14)
        self.floating_order_list = tk.Listbox(win, font=(self.settings.get("system_font", "Segoe UI"), int(self.settings.get("system_font_size", 10))))
        self.floating_order_list.pack(fill="both", expand=True, padx=14, pady=5)
        self.floating_order_total = tk.StringVar(); ttk.Label(win, textvariable=self.floating_order_total, font=(self.settings.get("system_font", "Segoe UI"), 16, "bold")).pack(anchor="e", padx=14, pady=12)
        ttk.Button(win, text="送出訂單 / Send Order", command=self.submit_floating_order).pack(fill="x", padx=14, pady=(0, 14))
        self.refresh_floating_order()
    def close_floating_order(self):
        if self.floating_order_win and self.floating_order_win.winfo_exists(): self.floating_order_win.destroy()
        self.floating_order_win = None; self.settings["floating_order"] = False; save_json(SETTINGS_FILE, self.settings)
    def refresh_floating_order(self):
        if not self.floating_order_win or not self.floating_order_win.winfo_exists(): return
        self.floating_order_list.delete(0, "end")
        for name, item in self.cart.items(): self.floating_order_list.insert("end", f"{name}  x{item['qty']}  ${item['price']*item['qty']:,.2f}")
        self.floating_order_total.set(f"{self.t('total')}: {self.amounts()[3]:,.2f} TWD")
    def submit_floating_order(self):
        if not self.cart: return messagebox.showwarning("", self.t("empty"), parent=self.floating_order_win or self)
        self.print_receipt()
    def change_selected(self, delta):
        sel = self.tree.selection()
        if not sel: return
        name = sel[0]; self.cart[name]["qty"] += delta
        if self.cart[name]["qty"] <= 0: del self.cart[name]
        self.refresh_cart()
    def clear_cart(self): self.cart.clear(); self.refresh_cart()
    def amounts(self):
        sub = sum(x["price"]*x["qty"] for x in self.cart.values())
        tax = sub * float(self.settings.get("tax_rate", 0))
        tip = (sub + tax) * (int(self.tip_var.get().strip("%") or 0) / 100) if hasattr(self, "tip_var") else 0
        return sub, tax, tip, sub + tax + tip
    def update_totals(self):
        if not hasattr(self, "total_var"): return
        sub, tax, tip, total = self.amounts(); cur = self.currency_var.get() if hasattr(self, "currency_var") else "TWD"; rate = self.settings["rates"].get(cur, 1)
        self.detail_var.set(f"{self.t('subtotal')}: {sub:,.2f}  |  {self.t('tax')}: {tax:,.2f}  |  {self.t('tip')}: {tip:,.2f}")
        self.total_var.set(f"{self.t('total')}: {total*rate:,.2f} {cur}")
    def bind_shortcuts(self):
        self.bind("<F2>", lambda e: self.show_settings()); self.bind("<F4>", lambda e: self.clear_cart()); self.bind("<F9>", lambda e: self.checkout()); self.bind("<Control-p>", lambda e: self.print_receipt())
        self.bind("<Control-l>", lambda e: self.toggle_language())

    def toggle_language(self): self.lang = "en" if self.lang == "zh" else "zh"; self.settings["language"] = self.lang; save_json(SETTINGS_FILE, self.settings); self.build_ui()
    def show_guide(self):
        messagebox.showinfo(self.t("guide"), "點選餐點加入訂單，選擇小費與幣別後按 F9 結帳。\n\n快捷鍵：F2 設定、F4 清空、F9 結帳、Ctrl+P 收據、Ctrl+L 語言切換。\n可在設定中調整稅率、收據格式與介面顏色。" if self.lang == "zh" else "Click items to add. Choose tip/currency, then press F9 to checkout.\n\nShortcuts: F2 settings, F4 clear, F9 checkout, Ctrl+P receipt, Ctrl+L language.\nAdjust tax, receipt format and UI color in Settings.")

    def show_settings(self):
        win = tk.Toplevel(self); win.title(self.t("settings")); win.transient(self); win.grab_set(); win.geometry("800x820"); win.minsize(760, 700); win.resizable(True, True)
        try: win.state("zoomed")
        except tk.TclError: pass
        f = ttk.Frame(win, padding=18); f.pack(fill="both", expand=True)
        tax = tk.StringVar(value=str(float(self.settings.get("tax_rate", .05))*100)); width = tk.StringVar(value=str(self.settings.get("receipt_width", 38))); show_tax = tk.BooleanVar(value=self.settings.get("show_tax", True)); show_tip = tk.BooleanVar(value=self.settings.get("show_tip", True)); floating_order = tk.BooleanVar(value=self.settings.get("floating_order", False)); theme = tk.StringVar(value=self.settings.get("theme", "#f4f6f8")); password = tk.StringVar(value=self.settings.get("history_password", "1234")); system_font = tk.StringVar(value=self.settings.get("system_font", "Segoe UI")); system_font_size = tk.StringVar(value=str(self.settings.get("system_font_size", 10))); menu_font = tk.StringVar(value=self.settings.get("menu_font", "Segoe UI")); menu_font_size = tk.StringVar(value=str(self.settings.get("menu_font_size", 10)))
        tax_box = ttk.LabelFrame(f, text="稅務設定 / Tax", padding=12); tax_box.pack(fill="x", pady=(0, 12))
        ttk.Label(tax_box, text=f"{self.t('tax')} (%)").grid(row=0, column=0, sticky="w"); ttk.Entry(tax_box, textvariable=tax, width=14).grid(row=0, column=1, sticky="w", padx=12)
        receipt_box = ttk.LabelFrame(f, text="收據版面 / Receipt Layout", padding=12); receipt_box.pack(fill="x", pady=(0, 12))
        header = tk.Text(receipt_box, height=4, width=48); header.insert("1.0", self.settings.get("receipt_header", ""))
        ttk.Label(receipt_box, text="抬頭 / Header").grid(row=0, column=0, sticky="nw"); header.grid(row=0, column=1, rowspan=2, sticky="w", padx=12)
        ttk.Label(receipt_box, text="寬度 / Width").grid(row=2, column=0, sticky="w", pady=(10, 0)); ttk.Entry(receipt_box, textvariable=width, width=14).grid(row=2, column=1, sticky="w", padx=12, pady=(10, 0))
        ttk.Checkbutton(receipt_box, text="顯示稅額 / Show tax", variable=show_tax).grid(row=3, column=0, sticky="w", pady=(8, 0)); ttk.Checkbutton(receipt_box, text="顯示小費 / Show tip", variable=show_tip).grid(row=3, column=1, sticky="w", padx=12, pady=(8, 0))
        currency_box = ttk.LabelFrame(f, text="匯率設定 / Currency Rates（以 TWD=1 為基準）", padding=12); currency_box.pack(fill="x", pady=(0, 12))
        rates = {}; rate_frame = ttk.Frame(currency_box); rate_frame.pack(anchor="w")
        for i, cur in enumerate(self.settings["rates"]):
            rates[cur] = tk.StringVar(value=str(self.settings["rates"][cur])); ttk.Label(rate_frame, text=cur, width=8).grid(row=0, column=i, padx=4); ttk.Entry(rate_frame, textvariable=rates[cur], width=12).grid(row=1, column=i, padx=4)
        theme_box = ttk.LabelFrame(f, text="介面主題 / Theme", padding=12); theme_box.pack(fill="x", pady=(0, 12))
        ttk.Label(theme_box, text="色碼 / Color").pack(side="left"); ttk.Entry(theme_box, textvariable=theme, width=14).pack(side="left", padx=12); ttk.Button(theme_box, text="選擇顏色 / Pick", command=lambda: self.pick_color(theme)).pack(side="left")
        security_box = ttk.LabelFrame(f, text="安全性 / Security", padding=12); security_box.pack(fill="x", pady=(0, 12))
        ttk.Label(security_box, text="歷史訂單刪除密碼 / Delete password", width=38).grid(row=0, column=0, sticky="w"); ttk.Entry(security_box, textvariable=password, show="*", width=20).grid(row=0, column=1, sticky="w", padx=12)
        ttk.Checkbutton(security_box, text="啟用浮動訂單視窗 / Floating order window", variable=floating_order).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        font_list = sorted(set(tkfont.families(self)))
        system_box = ttk.LabelFrame(f, text="系統字型 / System Font（菜單以外）", padding=12); system_box.pack(fill="x", pady=(0, 12))
        ttk.Label(system_box, text="字型 / Font", width=14).grid(row=0, column=0, sticky="w"); ttk.Combobox(system_box, textvariable=system_font, values=font_list, width=24).grid(row=0, column=1, sticky="w", padx=8); ttk.Label(system_box, text="大小 / Size", width=12).grid(row=0, column=2, sticky="w", padx=(20, 0)); ttk.Entry(system_box, textvariable=system_font_size, width=8).grid(row=0, column=3, sticky="w", padx=8)
        font_box = ttk.LabelFrame(f, text="菜單字型 / Menu Font", padding=12); font_box.pack(fill="x", pady=(0, 12))
        ttk.Label(font_box, text="字型 / Font", width=14).grid(row=0, column=0, sticky="w"); ttk.Combobox(font_box, textvariable=menu_font, values=font_list, width=24).grid(row=0, column=1, sticky="w", padx=8); ttk.Label(font_box, text="大小 / Size", width=12).grid(row=0, column=2, sticky="w", padx=(20, 0)); ttk.Entry(font_box, textvariable=menu_font_size, width=8).grid(row=0, column=3, sticky="w", padx=8)
        def save():
            try:
                self.settings["tax_rate"] = float(tax.get()) / 100
                self.settings["receipt_header"] = header.get("1.0", "end").strip()
                self.settings["rates"] = {cur: float(v.get()) for cur, v in rates.items()}
                self.settings["theme"] = theme.get().strip() or "#f4f6f8"
                self.winfo_rgb(self.settings["theme"])
                self.settings["receipt_width"] = max(20, min(80, int(width.get())))
                self.settings["show_tax"] = show_tax.get(); self.settings["show_tip"] = show_tip.get()
                if not password.get(): raise ValueError("password")
                self.settings["history_password"] = password.get()
                self.settings["floating_order"] = floating_order.get()
                self.settings["system_font"] = system_font.get().strip() or "Segoe UI"; self.settings["system_font_size"] = max(8, min(32, int(system_font_size.get())))
                self.settings["menu_font"] = menu_font.get().strip() or "Segoe UI"; self.settings["menu_font_size"] = max(8, min(32, int(menu_font_size.get())))
                save_json(SETTINGS_FILE, self.settings); self.apply_theme(); win.destroy(); self.build_ui()
                if self.settings["floating_order"]: self.open_floating_order()
                elif self.floating_order_win and self.floating_order_win.winfo_exists(): self.floating_order_win.destroy(); self.floating_order_win = None
            except (ValueError, tk.TclError): messagebox.showerror("Error", "請輸入有效數字或有效色碼，例如 #f4f6f8")
        action = ttk.Frame(f); action.pack(fill="x", pady=(4, 0)); ttk.Button(action, text="取消 / Cancel", command=win.destroy).pack(side="right"); ttk.Button(action, text=self.t("save"), command=save).pack(side="right", padx=8)
    def pick_color(self, variable):
        chosen = colorchooser.askcolor(color=variable.get(), parent=self)[1]
        if chosen: variable.set(chosen)
    def split_bill(self):
        if not self.cart: return messagebox.showwarning("", self.t("empty"))
        n = simpledialog.askinteger(self.t("split"), "請輸入用餐人數 / Number of people", minvalue=2, maxvalue=30, parent=self)
        if n: messagebox.showinfo(self.t("split"), f"每位應付 / Per person: {self.amounts()[3]/n:,.2f} {self.currency_var.get()}\n（最後一位負責四捨五入差額）")
    def checkout(self):
        if not self.cart: return messagebox.showwarning("", self.t("empty"))
        sub, tax, tip, total = self.amounts(); cur = self.currency_var.get(); rate = self.settings["rates"].get(cur, 1); due = total * rate
        cash = simpledialog.askfloat(self.t("pay"), f"{self.t('cash')} ({cur})\n{self.t('total')}: {due:,.2f}", minvalue=0, parent=self)
        if cash is None: return
        if cash < due: return messagebox.showerror("", f"不足 / Insufficient: {due-cash:,.2f} {cur}")
        order = {"order_no": self.current_order_no, "time": datetime.now().isoformat(timespec="seconds"), "subtotal": sub, "tax": tax, "tip": tip, "total": total, "currency": cur, "rate": rate, "payment": "cash", "items": self.cart.copy()}
        self.orders.append(order); save_json(ORDERS_FILE, self.orders); self.print_receipt(order, cash); self.clear_cart(); messagebox.showinfo(self.t("success"), f"{self.t('change')}: {cash-due:,.2f} {cur}")
        self.current_order_no = self.next_order_no()
        if hasattr(self, "order_no_var"): self.order_no_var.set(f"NO. {self.current_order_no}")
    def receipt_text(self, order=None, cash=None):
        o = order or {"order_no": self.current_order_no, "subtotal": self.amounts()[0], "tax": self.amounts()[1], "tip": self.amounts()[2], "total": self.amounts()[3], "currency": self.currency_var.get(), "rate": self.settings["rates"].get(self.currency_var.get(), 1), "items": self.cart}
        cur = o["currency"]; receipt_width = int(self.settings.get("receipt_width", 38)); name_width = max(10, receipt_width - 16); lines = [self.settings.get("receipt_header", ""), f"訂單號碼 / ORDER NO.: {o.get('order_no', 'N/A')}", "-"*receipt_width, f"{fit_receipt_text('ITEM', name_width)} {'QTY':^5} {'AMT':^9}", "-"*receipt_width]
        for name, x in o["items"].items(): lines.append(f"{fit_receipt_text(name, name_width)} {x['qty']:>5} {x['price']*x['qty']:>9.2f}")
        lines.append("-"*receipt_width); lines.append(f"{self.t('subtotal')}: {o['subtotal']:,.2f} TWD")
        if self.settings.get("show_tax", True): lines.append(f"{self.t('tax')}: {o['tax']:,.2f} TWD")
        if self.settings.get("show_tip", True): lines.append(f"{self.t('tip')}: {o['tip']:,.2f} TWD")
        lines.append(f"{self.t('total')}: {o['total']*o['rate']:,.2f} {cur}")
        if cash is not None: lines.append(f"{self.t('change')}: {cash-o['total']*o['rate']:,.2f} {cur}")
        return "\n".join(lines) + "\n" + datetime.now().strftime("%Y-%m-%d %H:%M")
    def print_receipt(self, order=None, cash=None):
        if order is None and not self.cart: return messagebox.showwarning("", self.t("empty"))
        preview = tk.Toplevel(self); preview.title("收據預覽 / Receipt Preview"); preview.geometry("520x680"); preview.transient(self); preview.grab_set()
        ttk.Label(preview, text="收據預覽 / Receipt Preview", style="Header.TLabel").pack(anchor="w", padx=16, pady=12)
        text_box = tk.Text(preview, width=48, height=30, font=("Consolas", 11), wrap="none", bg="#ffffff")
        text_box.insert("1.0", self.receipt_text(order, cash)); text_box.tag_add("receipt_title", "1.0", "1.0 lineend"); text_box.tag_configure("receipt_title", font=("Consolas", 20, "bold")); text_box.tag_add("receipt_subtitle", "2.0", "2.0 lineend"); text_box.tag_configure("receipt_subtitle", font=("Consolas", 15))
        order_line = text_box.search("訂單號碼 / ORDER NO.", "1.0")
        if order_line:
            text_box.tag_add("order_number", order_line, f"{order_line} lineend"); text_box.tag_configure("order_number", font=("Consolas", 15, "bold"), foreground="#b91c1c")
        text_box.configure(state="disabled"); text_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        actions = ttk.Frame(preview); actions.pack(fill="x", padx=16, pady=(0, 16))
        def confirm_print():
            path = os.path.join(DATA_DIR, "receipt_latest.txt"); os.makedirs(DATA_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f: f.write(self.receipt_text(order, cash))
            preview.destroy(); messagebox.showinfo(self.t("print"), f"收據已輸出 / Receipt saved:\n{path}", parent=self)
        ttk.Button(actions, text="取消 / Cancel", command=preview.destroy).pack(side="right")
        ttk.Button(actions, text="確認輸出 / Print", command=confirm_print).pack(side="right", padx=8)
    def show_stats(self):
        win = tk.Toplevel(self); win.title(self.t("stats")); win.geometry("1120x760"); win.minsize(1000, 680)
        period = tk.StringVar(value="日 / Day")
        ttk.Label(win, text="業績統計 Dashboard", style="Header.TLabel").pack(anchor="w", padx=25, pady=(18, 4))
        filter_bar = ttk.Frame(win); filter_bar.pack(fill="x", padx=25, pady=(0, 12))
        ttk.Label(filter_bar, text="報表範圍 / Period").pack(side="left"); ttk.Combobox(filter_bar, textvariable=period, values=["日 / Day", "週 / Week", "月 / Month", "季 / Quarter", "年 / Year"], state="readonly", width=18).pack(side="left", padx=10)
        summary = tk.StringVar(); summary_cards = ttk.Frame(win); summary_cards.pack(fill="x", padx=20, pady=(0, 12))
        card_values = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        for i, (label, var) in enumerate(zip(["訂單數 / Orders", "營業額 / Sales", "小費總額 / Tips"], card_values)):
            card = ttk.LabelFrame(summary_cards, text=label, padding=12); card.grid(row=0, column=i, sticky="ew", padx=5); ttk.Label(card, textvariable=var, font=("Segoe UI", 18, "bold")).pack(anchor="w"); summary_cards.columnconfigure(i, weight=1)
        tables = ttk.Frame(win, height=430); tables.pack(fill="both", expand=True, padx=25); tables.pack_propagate(False)
        item_tree = None; cat_tree = None
        for column in range(3): tables.columnconfigure(column, weight=1, uniform="stats")
        tables.rowconfigure(0, weight=1)
        for column, (kind, first) in enumerate([("category", "種類 / Category"), ("item", "品項 / Item")]):
            box = ttk.Frame(tables, padding=6); box.grid(row=0, column=column, sticky="nsew", padx=5)
            tree = ttk.Treeview(box, columns=("category", "qty", "sales") if kind == "category" else ("name", "qty", "sales"), show="headings", height=8)
            if kind == "category": cat_tree = tree
            else: item_tree = tree
            tree.heading(tree["columns"][0], text=first); tree.heading("qty", text="數量 / Qty"); tree.heading("sales", text="銷售額 / Sales"); tree.column(tree["columns"][0], width=150); tree.column("qty", width=65, anchor="center"); tree.column("sales", width=100, anchor="e"); tree.pack(fill="both", expand=True)
        chart_box = ttk.LabelFrame(tables, text="種類銷售比例 / Category Share", padding=8); chart_box.grid(row=0, column=2, sticky="nsew", padx=5)
        chart = tk.Canvas(chart_box, width=300, height=390, bg="white", highlightthickness=0); chart.pack()
        def get_rows():
            now = datetime.now(); key = period.get().split(" ")[0]
            if key == "日": start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif key == "週": start = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
            elif key == "月": start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else: start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            rows = []
            for order in self.orders:
                try:
                    if datetime.fromisoformat(order["time"]) >= start: rows.append(order)
                except (KeyError, ValueError): pass
            return rows
        def refresh():
            rows = get_rows(); sales = sum(o.get("total", 0) for o in rows); tips = sum(o.get("tip", 0) for o in rows)
            summary.set(f"{self.t('completed')}: {len(rows)} | {self.t('sales')}: {sales:,.2f} TWD | {self.t('tip_total')}: {tips:,.2f} TWD")
            card_values[0].set(f"{len(rows):,}"); card_values[1].set(f"{sales:,.2f} TWD"); card_values[2].set(f"{tips:,.2f} TWD")
            item_data = {}; category_data = {}
            category_by_name = {}
            for category, raw_name, price, image, barcode in self.menu:
                category_by_name[localized(raw_name, self.lang)] = localized(category, self.lang)
                category_by_name[str(raw_name)] = localized(category, self.lang)
            for order in rows:
                for name, data in order.get("items", {}).items():
                    qty = data.get("qty", 0); amount = data.get("price", 0) * qty; category = category_by_name.get(name, "未分類 / Other")
                    item_data[name] = (item_data.get(name, (0, 0))[0] + qty, item_data.get(name, (0, 0))[1] + amount)
                    category_data[category] = (category_data.get(category, (0, 0))[0] + qty, category_data.get(category, (0, 0))[1] + amount)
            for tree in (item_tree, cat_tree):
                for item in tree.get_children(): tree.delete(item)
            for name, (qty, amount) in sorted(item_data.items(), key=lambda x: x[1][1], reverse=True): item_tree.insert("", "end", values=(name, qty, f"{amount:,.2f}"))
            for category, (qty, amount) in sorted(category_data.items(), key=lambda x: x[1][1], reverse=True): cat_tree.insert("", "end", values=(category, qty, f"{amount:,.2f}"))
            if not item_data: item_tree.insert("", "end", values=("尚無資料 / No data", "-", "-"))
            if not category_data: cat_tree.insert("", "end", values=("尚無資料 / No data", "-", "-"))
            chart.delete("all")
            total_category_sales = sum(value[1] for value in category_data.values())
            if not total_category_sales:
                chart.create_text(150, 170, text="尚無資料 / No data", font=("Segoe UI", 13), fill="#777777")
            else:
                colors = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316"]
                angle = 90
                for index, (category, (qty, amount)) in enumerate(sorted(category_data.items(), key=lambda x: x[1][1], reverse=True)):
                    extent = amount / total_category_sales * 360
                    color = colors[index % len(colors)]; chart.create_arc(25, 20, 255, 250, start=angle, extent=-extent, fill=color, outline="white", width=2)
                    percent = amount / total_category_sales * 100
                    y = 280 + index * 24; chart.create_rectangle(25, y, 39, y + 14, fill=color, outline=color); chart.create_text(47, y + 7, anchor="w", text=f"{category}: {percent:.1f}% ({amount:,.0f})", font=("Segoe UI", 9))
                    angle -= extent
        def export():
            rows = get_rows(); path = os.path.join(DATA_DIR, f"sales_report_{datetime.now():%Y%m%d_%H%M%S}.csv"); os.makedirs(DATA_DIR, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f); writer.writerow(["time", "subtotal_TWD", "tax_TWD", "tip_TWD", "total_TWD", "currency", "payment"])
                for o in rows: writer.writerow([o.get("time", ""), o.get("subtotal", 0), o.get("tax", 0), o.get("tip", 0), o.get("total", 0), o.get("currency", "TWD"), o.get("payment", "cash")])
            messagebox.showinfo(self.t("stats"), f"報表已匯出 / Report exported:\n{path}")
        period.trace_add("write", lambda *_: refresh()); refresh()
        buttons = ttk.Frame(win); buttons.pack(fill="x", padx=25)
        ttk.Button(buttons, text="匯出 CSV / Export CSV", command=export).pack(side="left")
        ttk.Button(buttons, text=self.t("close"), command=win.destroy).pack(side="right")

    def show_order_history(self):
        win = tk.Toplevel(self); win.title("歷史訂單 / Order History"); win.geometry("820x520"); win.transient(self)
        f = ttk.Frame(win, padding=14); f.pack(fill="both", expand=True)
        search = tk.StringVar(); period = tk.StringVar(value="全部 / All"); bar = ttk.Frame(f); bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="單號 / Order No.").pack(side="left"); entry = ttk.Entry(bar, textvariable=search, width=22); entry.pack(side="left", padx=8)
        ttk.Label(bar, text="期間 / Period").pack(side="left"); period_box = ttk.Combobox(bar, textvariable=period, values=["全部 / All", "日 / Day", "週 / Week", "月 / Month", "季 / Quarter", "年 / Year"], state="readonly", width=13); period_box.pack(side="left", padx=8)
        tree = ttk.Treeview(f, columns=("no", "time", "total", "currency", "payment"), show="headings", height=16)
        for col, title, width in [("no", "單號 / No.", 190), ("time", "時間 / Time", 155), ("total", "金額 / Total", 110), ("currency", "幣別", 80), ("payment", "付款 / Payment", 100)]: tree.heading(col, text=title); tree.column(col, width=width, anchor="center")
        tree.pack(fill="both", expand=True)
        def order_no(order, index): return order.get("order_no", f"OLD-{index+1:04d}")
        def start_time():
            now = datetime.now(); key = period.get().split(" ")[0]
            if key == "日": return now.replace(hour=0, minute=0, second=0, microsecond=0)
            if key == "週": return now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
            if key == "月": return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if key == "季": return now.replace(month=((now.month - 1)//3)*3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            if key == "年": return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return None
        def refresh(*_):
            query = search.get().strip().lower()
            since = start_time()
            for item in tree.get_children(): tree.delete(item)
            for i, order in enumerate(reversed(self.orders)):
                no = order_no(order, len(self.orders)-1-i)
                if query and query not in no.lower(): continue
                if since:
                    try:
                        if datetime.fromisoformat(order.get("time", "")) < since: continue
                    except ValueError: continue
                tree.insert("", "end", iid=str(len(self.orders)-1-i), values=(no, order.get("time", ""), f"{order.get('total', 0):,.2f}", order.get("currency", "TWD"), order.get("payment", "cash")))
        def detail(event=None):
            selection = tree.selection()
            if not selection: return
            order = self.orders[int(selection[0])]; lines = [f"{self.t('name')}: {x['qty']} x {name} = {x['price']*x['qty']:,.2f}" for name, x in order.get("items", {}).items()]
            messagebox.showinfo(f"Order {order_no(order, int(selection[0]))}", "\n".join(lines) + f"\n\n{self.t('total')}: {order.get('total', 0):,.2f} TWD", parent=win)
        search.trace_add("write", refresh); period.trace_add("write", refresh); tree.bind("<Double-1>", detail); ttk.Button(bar, text="查詢 / Search", command=refresh).pack(side="left")
        def delete_selected():
            selection = tree.selection()
            if not selection: return messagebox.showwarning("", "請先選擇訂單 / Select an order", parent=win)
            typed = simpledialog.askstring("Password", "請輸入刪除密碼 / Delete password", show="*", parent=win)
            if typed != self.settings.get("history_password", "1234"): return messagebox.showerror("", "密碼錯誤 / Incorrect password", parent=win)
            if not messagebox.askyesno("Confirm", "確定刪除這筆歷史訂單？\nDelete this historical order?", parent=win): return
            self.orders.pop(int(selection[0])); save_json(ORDERS_FILE, self.orders); refresh()
        ttk.Button(bar, text="刪除 / Delete", command=delete_selected).pack(side="right", padx=6)
        ttk.Button(bar, text="關閉 / Close", command=win.destroy).pack(side="right"); refresh(); entry.focus_set()

    def show_calculator(self):
        win = tk.Toplevel(self); win.title("計算機 / Calculator"); win.geometry("300x390"); win.resizable(False, False)
        value = tk.StringVar(value="")
        display = ttk.Entry(win, textvariable=value, justify="right", font=("Segoe UI", 20)); display.pack(fill="x", padx=12, pady=12, ipady=8)
        grid = ttk.Frame(win); grid.pack(fill="both", expand=True, padx=12, pady=4)
        keys = [["C", "⌫", "%", "÷"], ["7", "8", "9", "×"], ["4", "5", "6", "−"], ["1", "2", "3", "+"], ["0", ".", "(", ")"], ["＝", ""]]
        expression = {"÷": "/", "×": "*", "−": "-", "%": "/100"}
        def press(key):
            current = value.get()
            if key == "C": value.set("")
            elif key == "⌫": value.set(current[:-1])
            elif key == "＝":
                try:
                    if current and set(current) <= set("0123456789.+-*/() "):
                        value.set(str(round(eval(current, {"__builtins__": {}}, {}), 10)))
                except (SyntaxError, ZeroDivisionError, ValueError): value.set("Error")
            else: value.set(current + expression.get(key, key))
        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                if key: ttk.Button(grid, text=key, command=lambda k=key: press(k)).grid(row=r, column=c, sticky="nsew", padx=2, pady=2, ipadx=6, ipady=8)
        for i in range(4): grid.columnconfigure(i, weight=1)
        for i in range(len(keys)): grid.rowconfigure(i, weight=1)
        display.focus_set()

    def show_menu_editor(self):
        win = tk.Toplevel(self); win.title("菜單編輯 / Menu Editor"); win.geometry("780x560"); win.transient(self)
        frame = ttk.Frame(win, padding=12); frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=("category", "name", "price", "barcode", "image"), show="headings", height=15)
        for col, title, width in [("category", "分類 / Category", 120), ("name", "名稱 / Name", 190), ("price", "價格 / Price", 80), ("barcode", "條碼 / Barcode", 120), ("image", "圖片 / Image", 180)]:
            tree.heading(col, text=title); tree.column(col, width=width)
        tree.pack(fill="both", expand=True)
        def reload_rows():
            for item in tree.get_children(): tree.delete(item)
            for i, (category, name, price, image, barcode) in enumerate(self.menu):
                tree.insert("", "end", iid=str(i), values=(localized(category, self.lang), localized(name, self.lang), f"{price:g}", barcode, image))
        reload_rows()
        form = ttk.Frame(frame); form.pack(fill="x", pady=10)
        vars_ = [tk.StringVar() for _ in range(5)]
        labels = ["分類", "名稱", "價格", "條碼", "圖片路徑"]
        for i, (label, var) in enumerate(zip(labels, vars_)):
            ttk.Label(form, text=label).grid(row=0, column=i, sticky="w")
            ttk.Entry(form, textvariable=var, width=[14, 22, 10, 15, 22][i]).grid(row=1, column=i, padx=(0, 6), sticky="ew")
        selected = tk.StringVar()
        def load_selected(event=None):
            sel = tree.selection()
            if not sel: return
            selected.set(sel[0]); category, name, price, image, barcode = self.menu[int(sel[0])]
            vals = [localized(category, self.lang), localized(name, self.lang), str(price), barcode, image]
            for var, val in zip(vars_, vals): var.set(val)
        tree.bind("<<TreeviewSelect>>", load_selected)
        def save_menu():
            self.menu.sort(key=lambda x: (localized(x[0], self.lang), localized(x[1], self.lang)))
            new_menu = []
            for category, name, price, image, barcode in self.menu:
                if isinstance(category, dict): category = {**category, self.lang: localized(category, self.lang)}
                if isinstance(name, dict): name = {**name, self.lang: localized(name, self.lang)}
                new_menu.append((category, name, price, image, barcode))
            self.menu = new_menu
            payload = [{"category": c, "name": n, "price": p, "image": i, "barcode": b} for c, n, p, i, b in self.menu]
            save_json(MENU_FILE, payload); self.build_ui(); win.destroy()
        def add_row():
            try: price = float(vars_[2].get())
            except ValueError: return messagebox.showerror("Error", "價格必須是數字", parent=win)
            if not vars_[0].get().strip() or not vars_[1].get().strip(): return messagebox.showerror("Error", "分類與名稱不可為空", parent=win)
            self.menu.append((vars_[0].get().strip(), vars_[1].get().strip(), price, vars_[4].get().strip(), vars_[3].get().strip())); reload_rows()
            for var in vars_: var.set("")
        def update_row():
            if selected.get() == "": return
            try: price = float(vars_[2].get())
            except ValueError: return messagebox.showerror("Error", "價格必須是數字", parent=win)
            i = int(selected.get()); self.menu[i] = (vars_[0].get().strip(), vars_[1].get().strip(), price, vars_[4].get().strip(), vars_[3].get().strip()); reload_rows()
        def delete_row():
            if selected.get() != "": self.menu.pop(int(selected.get())); selected.set(""); reload_rows()
        actions = ttk.Frame(frame); actions.pack(fill="x")
        ttk.Button(actions, text="新增 / Add", command=add_row).pack(side="left")
        ttk.Button(actions, text="修改 / Update", command=update_row).pack(side="left", padx=6)
        ttk.Button(actions, text="刪除 / Delete", command=delete_row).pack(side="left")
        ttk.Button(actions, text="儲存 / Save", command=save_menu).pack(side="right")


if __name__ == "__main__":
    POSApp().mainloop()
