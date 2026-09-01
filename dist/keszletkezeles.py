import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import pandas as pd
from sqlalchemy import create_engine
from tkcalendar import Calendar
import tempfile
import os
import webbrowser

# --- Globális Beállítások ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# A Neon adatbázis kapcsolati sztringje
DATABASE_URL = "postgresql://neondb_owner:npg_CQUsD4m6FedP@ep-bold-shape-b27rwpzu-pooler.c-6.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(DATABASE_URL)


def load_sheet_data(table_name):
    """Betölti egy adott nevű tábla tartalmát a Neon adatbázisból egy pandas DataFrame-be."""
    try:
        df = pd.read_sql(f'SELECT * "{table_name}"', engine)
        return df.astype(str)
    except Exception as e:
        try:
            df = pd.read_sql(f'SELECT * FROM "{table_name}"', engine)
            return df.astype(str)
        except:
            return pd.DataFrame()


def save_sheet_data(table_name, df):
    """Elmenti a pandas DataFrame adatait közvetlenül a Neon adatbázisba."""
    try:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
    except Exception as e:
        messagebox.showerror("Mentési hiba", f"Nem sikerült menteni az adatbázisba: {e}")


# --- Fő Alkalmazás Osztály ---
class KeszletApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Készletnyilvántartás - Bejelentkezés")
        self.geometry("400x350")
        self.resizable(False, False)

        self.init_users_db()
        self.build_login_screen()

    def init_users_db(self):
        df = load_sheet_data("Felhasznalok")
        if df.empty:
            df = pd.DataFrame([
                {"felhasznalo": "admin", "jelszo": "admin123", "szint": "admin"}
            ])
            save_sheet_data("Felhasznalok", df)

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def build_login_screen(self):
        self.clear_window()
        self.geometry("400x350")
        self.title("Készletnyilvántartás - Bejelentkezés")

        self.label_title = ctk.CTkLabel(self, text="Rendszer Bejelentkezés", font=("Arial", 20, "bold"))
        self.label_title.pack(pady=20)

        self.entry_user = ctk.CTkEntry(self, placeholder_text="Felhasználónév", width=250, height=40)
        self.entry_user.pack(pady=10)
        self.entry_user.focus()

        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Jelszó", show="*", width=250, height=40)
        self.entry_pass.pack(pady=10)

        self.btn_login = ctk.CTkButton(self, text="Belépés", command=self.verify_login, width=250, height=40)
        self.btn_login.pack(pady=20)

    def verify_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        df = load_sheet_data("Felhasznalok")
        if not df.empty and username in df["felhasznalo"].values:
            user_row = df[df["felhasznalo"] == username].iloc[0]
            if str(user_row["jelszo"]) == password:
                role = user_row["szint"]
                self.start_main_app(username, role)
                return

        messagebox.showerror("Hiba", "Hibás felhasználónév vagy jelszó!")

    def start_main_app(self, username, role):
        self.username = username
        self.role = role

        self.clear_window()
        self.geometry("1200x700")
        self.title(f"Készletnyilvántartás - Bejelentkezve: {self.username} ({self.role.upper()})")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_keszlet = self.tabview.add("Készlet & Keresés")
        self.tab_osszekeszi = self.tabview.add("Áru Összekészítés (Kimenő)")
        self.tab_kiadas = self.tabview.add("Előzmények (Kiadva)")
        self.tab_javaslatok = self.tabview.add("Fejlesztési javaslatok")

        if self.role in ["admin", "vezető"]:
            self.tab_admin_szallitas = self.tabview.add("Admin Kiszállítás")
            self.tab_naplo = self.tabview.add("Napló")
            self.tab_users = self.tabview.add("Felhasználó kezelés")

        self.build_keszlet_tab()
        self.build_osszekeszi_tab()
        self.build_kiadas_tab()
        self.build_javaslatok_tab()

        if self.role in ["admin", "vezető"]:
            self.build_admin_szallitas_tab()
            self.build_naplo_tab()
            self.build_users_tab()

        self.log_action("Bejelentkezés a rendszerbe")

    def log_action(self, action):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_log = pd.DataFrame([{"Idopont": timestamp, "Felhasznalo": self.username, "Muvelet": action}])

        df = load_sheet_data("Naplo")
        df = pd.concat([df, new_log], ignore_index=True)
        save_sheet_data("Naplo", df)

        if hasattr(self, "naplo_tree"):
            self.refresh_naplo_view()

    # --- 1. KÉSZLET & KERESÉS FÜL ---
    def build_keszlet_tab(self):
        control_frame = ctk.CTkFrame(self.tab_keszlet)
        control_frame.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(control_frame, placeholder_text="Keresés (Beszállító / Név / Lot)...", width=250)
        self.search_entry.pack(side="left", padx=5, pady=5)

        btn_search = ctk.CTkButton(control_frame, text="Keresés / Szűrés", command=self.refresh_keszlet_view)
        btn_search.pack(side="left", padx=5, pady=5)

        btn_reset = ctk.CTkButton(control_frame, text="Összes mutatása", command=self.reset_keszlet_search, fg_color="gray")
        btn_reset.pack(side="left", padx=5, pady=5)

        if self.role in ["admin", "vezető"]:
            btn_del = ctk.CTkButton(control_frame, text="Kijelölt törlése", command=self.delete_product, fg_color="red")
            btn_del.pack(side="right", padx=5, pady=5)

        btn_ship = ctk.CTkButton(control_frame, text="Kiválasztott kiadása", command=self.open_ship_window, fg_color="darkorange")
        btn_ship.pack(side="right", padx=5, pady=5)

        btn_add = ctk.CTkButton(control_frame, text="+ Új Cikk / Gyártás", command=self.open_add_product_window, fg_color="green")
        btn_add.pack(side="right", padx=5, pady=5)

        table_frame = ctk.CTkFrame(self.tab_keszlet)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("ID", "Beszállító (Brand)", "Termék neve", "Lot szám", "Gyártás ideje", "Lejárat", "Mennyiség", "Megjegyzés")
        self.keszlet_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.keszlet_tree.heading(col, text=col)
            self.keszlet_tree.column(col, width=110)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.keszlet_tree.yview)
        self.keszlet_tree.configure(yscrollcommand=scrollbar.set)

        self.keszlet_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.refresh_keszlet_view()

    def refresh_keszlet_view(self):
        for row in self.keszlet_tree.get_children():
            self.keszlet_tree.delete(row)

        df = load_sheet_data("Keszlet")
        if df.empty:
            return

        query = self.search_entry.get().strip().lower()
        if query:
            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(query)).any(axis=1)
            df = df[mask]

        for _, row in df.iterrows():
            qty = row.get("Mennyiség", "0")
            try:
                qty = str(int(float(qty)))
            except ValueError:
                pass

            self.keszlet_tree.insert("", "end", values=(
                row.get("ID", ""), row.get("Beszállító", ""), row.get("Termék neve", ""),
                row.get("Lot szám", ""), row.get("Gyártás ideje", ""), row.get("Lejárat", ""),
                qty, row.get("Megjegyzés", "")
            ))

    def reset_keszlet_search(self):
        self.search_entry.delete(0, "end")
        self.refresh_keszlet_view()

    def open_add_product_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Új termék / Gyártás rögzítése")
        win.geometry("400x600")
        win.grab_set()
        win.focus_set()

        df_existing = load_sheet_data("Keszlet")
        existing_brands = sorted(list(df_existing["Beszállító"].dropna().unique())) if not df_existing.empty and "Beszállító" in df_existing.columns else []
        existing_names = sorted(list(df_existing["Termék neve"].dropna().unique())) if not df_existing.empty and "Termék neve" in df_existing.columns else []

        ctk.CTkLabel(win, text="Beszállító (Brand):").pack(anchor="w", padx=20, pady=(10, 0))
        e_brand = ctk.CTkComboBox(win, values=existing_brands, width=350)
        e_brand.pack(padx=20, pady=5)
        e_brand.set(existing_brands[0] if existing_brands else "")

        ctk.CTkLabel(win, text="Termék neve:").pack(anchor="w", padx=20, pady=(10, 0))
        e_name = ctk.CTkComboBox(win, values=existing_names, width=350)
        e_name.pack(padx=20, pady=5)
        e_name.set(existing_names[0] if existing_names else "")

        ctk.CTkLabel(win, text="Lot szám:").pack(anchor="w", padx=20, pady=(10, 0))
        e_lot = ctk.CTkEntry(win, width=350)
        e_lot.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Gyártás ideje (ÉÉÉÉ-HH-NN):").pack(anchor="w", padx=20, pady=(10, 0))
        e_gyartas = ctk.CTkEntry(win, width=350)
        e_gyartas.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        e_gyartas.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Lejárati idő (ÉÉÉÉ-HH-NN):").pack(anchor="w", padx=20, pady=(10, 0))
        date_frame = ctk.CTkFrame(win, fg_color="transparent")
        date_frame.pack(padx=20, pady=5, fill="x")

        e_lejarat = ctk.CTkEntry(date_frame, width=240)
        e_lejarat.pack(side="left", padx=(0, 5))
        e_lejarat.insert(0, (datetime.date.today() + datetime.timedelta(days=365)).strftime("%Y-%m-%d"))

        def open_calendar():
            cal_win = ctk.CTkToplevel(win)
            cal_win.title("Válassz lejárati dátumot")
            cal_win.geometry("300x300")
            cal_win.grab_set()
            cal = Calendar(cal_win, selectmode='day', year=datetime.date.today().year,
                           month=datetime.date.today().month, day=datetime.date.today().day)
            cal.pack(pady=10, fill="both", expand=True)

            def set_date():
                e_lejarat.delete(0, "end")
                e_lejarat.insert(0, cal.selection_get().strftime("%Y-%m-%d"))
                cal_win.destroy()

            ctk.CTkButton(cal_win, text="Kiválasztás", command=set_date, fg_color="green").pack(pady=10)

        ctk.CTkButton(date_frame, text="📅 Naptár", width=100, command=open_calendar).pack(side="right")

        ctk.CTkLabel(win, text="Mennyiség (egész szám, min. 1):").pack(anchor="w", padx=20, pady=(10, 0))
        e_mennyiseg = ctk.CTkEntry(win, width=350)
        e_mennyiseg.insert(0, "1")
        e_mennyiseg.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Megjegyzés (Gyártás):").pack(anchor="w", padx=20, pady=(10, 0))
        e_megj = ctk.CTkEntry(win, width=350)
        e_megj.pack(padx=20, pady=5)

        def save_new():
            brand, name, lot, gyartas, lejarat, menny, megj = e_brand.get().strip(), e_name.get().strip(), e_lot.get().strip(), e_gyartas.get().strip(), e_lejarat.get().strip(), e_mennyiseg.get().strip(), e_megj.get().strip()

            if not brand or not name or not lot or not menny:
                messagebox.showerror("Hiba", "Minden kötelező mezőt ki kell tölteni!", parent=win)
                return

            try:
                menny_val = int(menny)
            except ValueError:
                messagebox.showerror("Hiba", "A mennyiség csak érvényes egész szám lehet!", parent=win)
                return

            if menny_val < 1:
                messagebox.showerror("Hiba", "A mennyiség nem lehet kisebb, mint 1!", parent=win)
                return

            df = load_sheet_data("Keszlet")
            if not df.empty and lot in df["Lot szám"].values:
                if messagebox.askyesno("Létező Lot szám", f"Már létezik termék ezzel a Lot számmal ({lot}). Hozzáadjuk?", parent=win):
                    idx = df[df["Lot szám"] == lot].index[0]
                    df.loc[idx, "Mennyiség"] = str(int(float(df.loc[idx, "Mennyiség"])) + menny_val)
                    save_sheet_data("Keszlet", df)
                    self.log_action(f"Meglévő Lot bővítve: {brand} - {name} (Lot: {lot}), +{menny_val}")
                    self.refresh_keszlet_view()
                    if hasattr(self, "refresh_admin_szallitas_view"):
                        self.refresh_admin_szallitas_view()
                    win.destroy()
                    messagebox.showinfo("Siker", "Mennyiség hozzáadva!", parent=self)
                    return
                else:
                    return

            new_row = pd.DataFrame([{
                "ID": str(len(df) + 1), "Beszállító": brand, "Termék neve": name, "Lot szám": lot,
                "Gyártás ideje": gyartas, "Lejárat": lejarat, "Mennyiség": str(menny_val), "Megjegyzés": megj
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_sheet_data("Keszlet", df)

            self.log_action(f"Új termék hozzáadva: {brand} - {name} (Lot: {lot})")
            self.refresh_keszlet_view()
            if hasattr(self, "refresh_admin_szallitas_view"):
                self.refresh_admin_szallitas_view()
            win.destroy()
            messagebox.showinfo("Siker", "Cikk sikeresen hozzáadva!", parent=self)

        ctk.CTkButton(win, text="Mentés", command=save_new, fg_color="green", width=200).pack(pady=20)

    def delete_product(self):
        if self.role not in ["admin", "vezető"]:
            messagebox.showerror("Jogosultság hiba", "Nincs jogosultságod!")
            return
        selected_item = self.keszlet_tree.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy elemet!")
            return
        item_values = self.keszlet_tree.item(selected_item, "values")
        if messagebox.askyesno("Megerősítés", f"Biztosan törlöd: {item_values[1]} - {item_values[2]}?"):
            df = load_sheet_data("Keszlet")
            df = df[df["ID"].astype(str) != str(item_values[0])]
            save_sheet_data("Keszlet", df)
            self.log_action(f"Termék törölve: {item_values[1]} - {item_values[2]}")
            self.refresh_keszlet_view()

    def open_ship_window(self):
        selected_item = self.keszlet_tree.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy elemet a készletből!")
            return

        item_id, brand, name, lot, gyartas, lejarat, max_menny, _ = self.keszlet_tree.item(selected_item, "values")

        win = ctk.CTkToplevel(self)
        win.title("Termék Kiszállítása")
        win.geometry("400x350")
        win.grab_set()
        win.focus_set()

        ctk.CTkLabel(win, text=f"Kiadás alatt:\n{brand} - {name}\n(Lot: {lot})", font=("Arial", 14, "bold"), justify="center").pack(pady=10)
        ctk.CTkLabel(win, text=f"Jelenlegi készlet: {max_menny}").pack(pady=5)

        ctk.CTkLabel(win, text="Kiadandó mennyiség:").pack(anchor="w", padx=20)
        e_menny = ctk.CTkEntry(win, width=350)
        e_menny.pack(padx=20, pady=5)
        e_menny.focus()

        ctk.CTkLabel(win, text="Megjegyzés:").pack(anchor="w", padx=20)
        e_megj = ctk.CTkEntry(win, width=350)
        e_megj.pack(padx=20, pady=5)

        def confirm_shipment():
            try:
                kiad_f, max_f = int(e_menny.get().strip()), int(max_menny)
            except ValueError:
                messagebox.showerror("Hiba", "Érvényes számot adj meg!", parent=win)
                return

            if 1 <= kiad_f <= max_f:
                df_keszlet = load_sheet_data("Keszlet")
                idx = df_keszlet[df_keszlet["ID"].astype(str) == str(item_id)].index
                remaining = max_f - kiad_f
                if remaining == 0:
                    df_keszlet = df_keszlet.drop(idx)
                else:
                    df_keszlet.loc[idx, "Mennyiség"] = str(remaining)
                save_sheet_data("Keszlet", df_keszlet)

                df_kiadas = load_sheet_data("Kiadasok")
                new_kiadas = pd.DataFrame([{
                    "Idopont": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Beszállító": brand, "Termék neve": name, "Lot szám": lot,
                    "Mennyiség": str(kiad_f), "Felhasználó": self.username, "Megjegyzés": e_megj.get().strip()
                }])
                save_sheet_data("Kiadasok", pd.concat([df_kiadas, new_kiadas], ignore_index=True))
                self.log_action(f"Kiadás: {brand} - {name} (Lot: {lot}), Mennyiség: {kiad_f}")
                self.refresh_keszlet_view()
                win.destroy()
                messagebox.showinfo("Siker", "Kiadás rögzítve!", parent=self)
            else:
                messagebox.showerror("Hiba", "Helytelen mennyiség!", parent=win)

        ctk.CTkButton(win, text="Kiadás rögzítése", command=confirm_shipment, fg_color="darkorange", width=200).pack(pady=20)

    # --- 2. ADMIN KISZÁLLÍTÁS FÜL ---
    def build_admin_szallitas_tab(self):
        ctk.CTkLabel(self.tab_admin_szallitas, text="Szállítmányok összeállítása (Csoportosított rendelések)", font=("Arial", 16, "bold")).pack(pady=5)

        shipment_group_frame = ctk.CTkFrame(self.tab_admin_szallitas)
        shipment_group_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(shipment_group_frame, text="Szállítmány azonosító:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        self.admin_shipment_name_entry = ctk.CTkEntry(shipment_group_frame, placeholder_text="SZALL-2026-001", width=170)
        self.admin_shipment_name_entry.pack(side="left", padx=5)
        self.admin_shipment_name_entry.insert(0, f"SZALL-{datetime.date.today().strftime('%Y%m%d')}-1")
        self.admin_shipment_name_entry.bind("<KeyRelease>", lambda e: self.refresh_current_shipment_view())

        ctk.CTkLabel(shipment_group_frame, text="Dátum:").pack(side="left", padx=(10, 2))
        self.admin_date_entry = ctk.CTkEntry(shipment_group_frame, width=90)
        self.admin_date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.admin_date_entry.pack(side="left", padx=2)

        ctk.CTkLabel(shipment_group_frame, text="Idősáv:").pack(side="left", padx=(10, 2))
        self.admin_timeslot_entry = ctk.CTkEntry(shipment_group_frame, placeholder_text="08:00-12:00", width=95)
        self.admin_timeslot_entry.pack(side="left", padx=2)

        split_container = ctk.CTkFrame(self.tab_admin_szallitas, fg_color="transparent")
        split_container.pack(fill="both", expand=True, padx=5, pady=5)

        left_pane = ctk.CTkFrame(split_container)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=0)

        ctk.CTkLabel(left_pane, text="1. Válassz terméket a készletből:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        columns = ("ID", "Beszállító", "Termék neve", "Lot", "Készlet")
        self.admin_keszlet_tree = ttk.Treeview(left_pane, columns=columns, show="headings", height=12)
        col_widths = {"ID": 40, "Beszállító": 100, "Termék neve": 120, "Lot": 80, "Készlet": 60}
        for col in columns:
            self.admin_keszlet_tree.heading(col, text=col)
            self.admin_keszlet_tree.column(col, width=col_widths.get(col, 90))

        scrollbar_left = ttk.Scrollbar(left_pane, orient="vertical", command=self.admin_keszlet_tree.yview)
        self.admin_keszlet_tree.configure(yscrollcommand=scrollbar_left.set)
        self.admin_keszlet_tree.pack(side="top", fill="both", expand=True, padx=5)
        scrollbar_left.pack(side="right", fill="y")

        add_control_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        add_control_frame.pack(fill="x", padx=5, pady=5)

        row_sub = ctk.CTkFrame(add_control_frame, fg_color="transparent")
        row_sub.pack(fill="x", pady=2)
        ctk.CTkLabel(row_sub, text="Mennyiség:").pack(side="left", padx=2)
        self.admin_qty_entry = ctk.CTkEntry(row_sub, width=60)
        self.admin_qty_entry.insert(0, "1")
        self.admin_qty_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row_sub, text="Megjegyzés:").pack(side="left", padx=(10, 2))
        self.admin_note_entry = ctk.CTkEntry(row_sub, width=170)
        self.admin_note_entry.pack(side="left", padx=2)

        btn_send_to_user = ctk.CTkButton(add_control_frame, text="Hozzáadás a szállítmányhoz ➔", command=self.send_order_to_user, fg_color="green", height=32)
        btn_send_to_user.pack(fill="x", padx=2, pady=5)

        right_pane = ctk.CTkFrame(split_container)
        right_pane.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=0)

        header_right_frame = ctk.CTkFrame(right_pane, fg_color="transparent")
        header_right_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_right_frame, text="2. Ebbe a szállítmányba kerültek:", font=("Arial", 12, "bold")).pack(side="left")

        btn_del_from_shipment = ctk.CTkButton(header_right_frame, text="Kijelölt törlése", command=self.delete_item_from_current_shipment, fg_color="red", width=110, height=24)
        btn_del_from_shipment.pack(side="right")

        right_columns = ("SorID", "Termék neve", "Lot", "Mennyiség", "Megjegyzés")
        self.current_shipment_tree = ttk.Treeview(right_pane, columns=right_columns, show="headings", height=15)
        right_col_widths = {"SorID": 40, "Termék neve": 140, "Lot": 80, "Mennyiség": 65, "Megjegyzés": 130}
        for col in right_columns:
            self.current_shipment_tree.heading(col, text=col)
            self.current_shipment_tree.column(col, width=right_col_widths.get(col, 90))

        scrollbar_right = ttk.Scrollbar(right_pane, orient="vertical", command=self.current_shipment_tree.yview)
        self.current_shipment_tree.configure(yscrollcommand=scrollbar_right.set)
        self.current_shipment_tree.pack(side="top", fill="both", expand=True, padx=5)
        scrollbar_right.pack(side="right", fill="y")

        self.refresh_admin_szallitas_view()

    def refresh_admin_szallitas_view(self):
        if not hasattr(self, "admin_keszlet_tree"):
            return
        for row in self.admin_keszlet_tree.get_children():
            self.admin_keszlet_tree.delete(row)
        df = load_sheet_data("Keszlet")
        if df.empty:
            return
        for _, row in df.iterrows():
            self.admin_keszlet_tree.insert("", "end", values=(
                row.get("ID", ""), row.get("Beszállító", ""), row.get("Termék neve", ""), row.get("Lot szám", ""),
                row.get("Mennyiség", "")))
        self.refresh_current_shipment_view()

    def refresh_current_shipment_view(self):
        if not hasattr(self, "current_shipment_tree"):
            return
        for row in self.current_shipment_tree.get_children():
            self.current_shipment_tree.delete(row)

        current_shipment_name = self.admin_shipment_name_entry.get().strip()
        if not current_shipment_name:
            return

        df_orders = load_sheet_data("Megrendelesek")
        if df_orders.empty or "Szallitmany_Nev" not in df_orders.columns:
            return

        filtered = df_orders[df_orders["Szallitmany_Nev"] == current_shipment_name]
        for idx, row in filtered.iterrows():
            self.current_shipment_tree.insert("", "end", values=(
                str(idx), row.get("Termék neve", ""), row.get("Lot szám", ""),
                row.get("Mennyiség", ""), row.get("Megjegyzés", "")
            ))

    def send_order_to_user(self):
        selected = self.admin_keszlet_tree.selection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy tételt a bal oldali készletből!", parent=self.tab_admin_szallitas)
            return

        item_id, brand, name, lot, max_qty = self.admin_keszlet_tree.item(selected, "values")
        shipment_name = self.admin_shipment_name_entry.get().strip()
        qty_str = self.admin_qty_entry.get().strip()
        pickup_date = self.admin_date_entry.get().strip()
        timeslot = self.admin_timeslot_entry.get().strip()

        if not shipment_name or not qty_str or not pickup_date or not timeslot:
            messagebox.showerror("Hiba", "Minden mezőt (Szállítmány azonosító, Mennyiség, Dátum, Idősáv) ki kell tölteni!", parent=self.tab_admin_szallitas)
            return

        try:
            qty_val, max_val = int(qty_str), int(max_qty)
        except ValueError:
            messagebox.showerror("Hiba", "A mennyiség csak egész szám lehet!", parent=self.tab_admin_szallitas)
            return

        if 1 <= qty_val <= max_val:
            df_orders = load_sheet_data("Megrendelesek")
            new_order = pd.DataFrame([{
                "ID": item_id, "Szallitmany_Nev": shipment_name, "Beszállító": brand, "Termék neve": name, "Lot szám": lot,
                "Mennyiség": str(qty_val), "Felvetel_Datum": pickup_date, "Idosav": timeslot,
                "Megjegyzés": self.admin_note_entry.get().strip(), "Allapot": "Függőben (Összekészítés alatt)"
            }])
            save_sheet_data("Megrendelesek", pd.concat([df_orders, new_order], ignore_index=True))
            self.log_action(f"Szállítmányba ({shipment_name}) tételt helyezve: {brand} - {name} (Mennyiség: {qty_val})")

            self.admin_note_entry.delete(0, "end")
            self.refresh_current_shipment_view()
            self.refresh_osszekeszi_view()
        else:
            messagebox.showerror("Hiba", "Helytelen mennyiség!", parent=self.tab_admin_szallitas)

    def delete_item_from_current_shipment(self):
        selected = self.current_shipment_tree.selection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy tételt a jobb oldali listából a törléshez!", parent=self.tab_admin_szallitas)
            return

        vals = self.current_shipment_tree.item(selected, "values")
        df_orders = load_sheet_data("Megrendelesek")
        if df_orders.empty:
            return

        current_shipment_name = self.admin_shipment_name_entry.get().strip()
        filtered_idx = df_orders[
            (df_orders["Szallitmany_Nev"] == current_shipment_name) &
            (df_orders["Termék neve"] == vals[1]) &
            (df_orders["Lot szám"] == vals[2]) &
            (df_orders["Mennyiség"] == vals[3])
        ].index

        if not filtered_idx.empty:
            df_orders = df_orders.drop(filtered_idx[0])
            save_sheet_data("Megrendelesek", df_orders)
            self.log_action(f"Tétel eltávolítva a szállítmányból: {current_shipment_name} -> {vals[1]}")
            self.refresh_current_shipment_view()
            self.refresh_osszekeszi_view()

    # --- 3. ÁRU ÖSSZEKÉSZÍTÉS FÜL ---
    def build_osszekeszi_tab(self):
        ctk.CTkLabel(self.tab_osszekeszi, text="Kimenő áruk összekészítése (Szállítmányok szerinti csoportosítás)", font=("Arial", 16, "bold")).pack(pady=10)

        table_frame = ctk.CTkFrame(self.tab_osszekeszi)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Kijelölve", "Szállítmány Neve", "Beszállító", "Termék neve", "Lot szám", "Mennyiség", "Felvétel Napja", "Idősáv", "Megjegyzés", "Állapot")
        self.osszekeszi_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        self.osszekeszi_tree.tag_configure("checked", background="#d4edda")

        column_widths = {"Kijelölve": 80, "Szállítmány Neve": 130, "Beszállító": 110, "Termék neve": 130, "Lot szám": 90, "Mennyiség": 80, "Felvétel Napja": 100, "Idősáv": 100, "Megjegyzés": 130, "Állapot": 130}
        for col in columns:
            self.osszekeszi_tree.heading(col, text=col)
            self.osszekeszi_tree.column(col, width=column_widths.get(col, 110))

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.osszekeszi_tree.yview)
        self.osszekeszi_tree.configure(yscrollcommand=scrollbar.set)
        self.osszekeszi_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.osszekeszi_tree.bind("<Button-1>", self.on_osszekeszi_click)

        btn_frame = ctk.CTkFrame(self.tab_osszekeszi)
        btn_frame.pack(fill="x", padx=10, pady=10)

        btn_select_all = ctk.CTkButton(btn_frame, text="Minden kijelölése", command=self.select_all_orders, fg_color="royalblue", width=140)
        btn_select_all.pack(side="left", padx=5)

        btn_deselect_all = ctk.CTkButton(btn_frame, text="Kijelölések törlése", command=self.deselect_all_orders, fg_color="gray", width=140)
        btn_deselect_all.pack(side="left", padx=5)

        btn_complete = ctk.CTkButton(btn_frame, text="Kijelöltek Összekészítése és Szállítólevél készítése", command=self.prepare_delivery_preview, fg_color="green", width=310)
        btn_complete.pack(side="left", padx=5)

        if self.role in ["admin", "vezető"]:
            btn_del_order = ctk.CTkButton(btn_frame, text="Kijelölt törlése", command=self.delete_order_admin, fg_color="red", width=130)
            btn_del_order.pack(side="left", padx=5)

        btn_refresh = ctk.CTkButton(btn_frame, text="Lista Frissítése", command=self.refresh_osszekeszi_view, fg_color="gray", width=120)
        btn_refresh.pack(side="right", padx=5)

        self.refresh_osszekeszi_view()

    def on_osszekeszi_click(self, event):
        region = self.osszekeszi_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.osszekeszi_tree.identify_column(event.x)
            if column == "#1":
                item = self.osszekeszi_tree.identify_row(event.y)
                if item:
                    vals = list(self.osszekeszi_tree.item(item, "values"))
                    if vals:
                        current_tags = list(self.osszekeszi_tree.item(item, "tags"))
                        if vals[0] == "☐":
                            vals[0] = "☑"
                            if "checked" not in current_tags:
                                current_tags.append("checked")
                        else:
                            vals[0] = "☐"
                            if "checked" in current_tags:
                                current_tags.remove("checked")
                        self.osszekeszi_tree.item(item, values=vals, tags=current_tags)

    def select_all_orders(self):
        for item in self.osszekeszi_tree.get_children():
            vals = list(self.osszekeszi_tree.item(item, "values"))
            if vals:
                vals[0] = "☑"
                self.osszekeszi_tree.item(item, values=vals, tags=("checked",))

    def deselect_all_orders(self):
        for item in self.osszekeszi_tree.get_children():
            vals = list(self.osszekeszi_tree.item(item, "values"))
            if vals:
                vals[0] = "☐"
                self.osszekeszi_tree.item(item, values=vals, tags=())

    def refresh_osszekeszi_view(self):
        if not hasattr(self, "osszekeszi_tree"):
            return
        for row in self.osszekeszi_tree.get_children():
            self.osszekeszi_tree.delete(row)

        df = load_sheet_data("Megrendelesek")
        if df.empty:
            return

        if "Szallitmany_Nev" not in df.columns:
            df["Szallitmany_Nev"] = "Egyedi Szállítás"

        for _, row in df.iterrows():
            self.osszekeszi_tree.insert("", "end", values=(
                "☐", row.get("Szallitmany_Nev", ""), row.get("Beszállító", ""), row.get("Termék neve", ""),
                row.get("Lot szám", ""), row.get("Mennyiség", ""), row.get("Felvetel_Datum", ""),
                row.get("Idosav", ""), row.get("Megjegyzés", ""), row.get("Allapot", "")
            ))

    def prepare_delivery_preview(self):
        all_items = self.osszekeszi_tree.get_children()
        checked_items = []

        for item in all_items:
            vals = self.osszekeszi_tree.item(item, "values")
            if vals and vals[0] == "☑":
                checked_items.append(vals)

        if not checked_items:
            messagebox.showwarning("Figyelmeztetés", "Nincs kijelölve egyetlen tétel sem!", parent=self.tab_osszekeszi)
            return

        processed_records = []
        for item_vals in checked_items:
            _, shipment_name, brand, name, lot, qty_str, pickup_date, timeslot, note, status = item_vals
            processed_records.append((shipment_name, brand, name, lot, qty_str, pickup_date, timeslot, note))

        self.open_delivery_note_preview(processed_records)

    def open_delivery_note_preview(self, items_list):
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("Szállítólevél - Előnézet és Nyomtatás")
        preview_win.geometry("650x800")
        preview_win.grab_set()

        default_shipment_name = items_list[0][0] if items_list else "Szállítmány"

        ctk.CTkLabel(preview_win, text="SZÁLLÍTÓLEVÉL", font=("Arial", 22, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(preview_win, text=f"Kiállítás dátuma: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                     font=("Arial", 11)).pack(pady=(0, 10))

        input_frame = ctk.CTkFrame(preview_win)
        input_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(input_frame, text="Szállítmány / Csoport Neve:").pack(anchor="w", padx=10, pady=(5, 0))
        e_szallitmany = ctk.CTkEntry(input_frame, width=570)
        e_szallitmany.pack(padx=10, pady=5)
        e_szallitmany.insert(0, default_shipment_name)

        if self.role != "admin":
            e_szallitmany.configure(state="disabled")

        ctk.CTkLabel(input_frame, text="Vevő / Cég neve (hova szállítjuk):").pack(anchor="w", padx=10, pady=(5, 0))
        e_vevo = ctk.CTkEntry(input_frame, width=570)
        e_vevo.pack(padx=10, pady=5)
        e_vevo.insert(0, "Novotic Kft.")
        # ... (a többi kód változatlan)
        # ------------------------------------------------------

        ctk.CTkLabel(input_frame, text="Vevő / Cég neve (hova szállítjuk):").pack(anchor="w", padx=10, pady=(5, 0))
        e_vevo = ctk.CTkEntry(input_frame, width=570)
        e_vevo.pack(padx=10, pady=5)
        e_vevo.insert(0, "Novotic Kft.")

        ctk.CTkLabel(input_frame, text="Beszállító (mint cégnév):").pack(anchor="w", padx=10, pady=(5, 0))
        e_beszallito = ctk.CTkEntry(input_frame, width=570)
        e_beszallito.pack(padx=10, pady=5)
        default_besz = items_list[0][1] if items_list else "Novotic Kft."
        e_beszallito.insert(0, default_besz)

        content_frame = ctk.CTkFrame(preview_win, fg_color="white", corner_radius=6)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        text_box = ctk.CTkTextbox(content_frame, font=("Courier", 11), text_color="black", fg_color="white")
        text_box.pack(fill="both", expand=True, padx=10, pady=10)

        def update_text_content(*args):
            szall_nev = e_szallitmany.get().strip()
            vevo = e_vevo.get().strip()
            beszallito_ceg = e_beszallito.get().strip()

            items_str = ""
            for idx, itm in enumerate(items_list, 1):
                shipment_name, brand, name, lot, qty, pickup_date, timeslot, note = itm
                items_str += (
                    f" {idx}. Termék: {name}\n"
                    f"    Beszállító: {brand} | Lot: {lot}\n"
                    f"    Mennyiség:  {qty} db\n"
                    f"    Idősáv:     {pickup_date} ({timeslot})\n"
                    f"    Megjegyzés: {note if note else '-'}\n"
                    f"    --------------------------------------------\n"
                )

            doc_text = (
                f"====================================================\n"
                f"                   SZÁLLÍTÓLEVÉL                    \n"
                f"====================================================\n"
                f"Szállítmány azonosító: {szall_nev}\n"
                f"Kiállítás ideje: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"Kezelő / Kiállító: {self.username}\n\n"
                f"PARTNER ADATOK:\n"
                f" - Vevő / Cég:        {vevo}\n"
                f" - Beszállító (Cég):  {beszallito_ceg}\n\n"
                f"CSOPORTOSÍTOTT TÉTELEK LISTÁJA:\n"
                f"--------------------------------------------\n"
                f"{items_str}\n"
                f"Az áru átvétele a fenti adatok szerint\n"
                f"rendben megtörtént.\n\n"
                f"............................        ................\n"
                f"       Átadó aláírása                 Átvevő aláírása\n"
                f"===================================================="
            )
            text_box.delete("1.0", "end")
            text_box.insert("1.0", doc_text)

        e_szallitmany.bind("<KeyRelease>", update_text_content)
        e_vevo.bind("<KeyRelease>", update_text_content)
        e_beszallito.bind("<KeyRelease>", update_text_content)
        update_text_content()

        btn_frame = ctk.CTkFrame(preview_win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        def print_and_finalize():
            try:
                df_orders = load_sheet_data("Megrendelesek")
                df_keszlet = load_sheet_data("Keszlet")
                df_kiadas = load_sheet_data("Kiadasok")

                for itm in items_list:
                    shipment_name, brand, name, lot, qty_str, pickup_date, timeslot, note = itm
                    ordered_qty = int(float(qty_str))

                    matched_rows = df_orders[
                        (df_orders["Szallitmany_Nev"] == shipment_name) &
                        (df_orders["Beszállító"] == brand) &
                        (df_orders["Termék neve"] == name) &
                        (df_orders["Lot szám"] == lot) &
                        (df_orders["Mennyiség"] == qty_str)
                        ]

                    if not matched_rows.empty:
                        row_idx = matched_rows.index[0]
                        item_id = str(df_orders.loc[row_idx, "ID"])
                        df_orders = df_orders.drop(row_idx)

                        keszlet_matched = df_keszlet[df_keszlet["ID"].astype(str) == item_id]
                        if keszlet_matched.empty:
                            keszlet_matched = df_keszlet[df_keszlet["Lot szám"] == lot]

                        if not keszlet_matched.empty:
                            k_idx = keszlet_matched.index[0]
                            current_qty = int(float(df_keszlet.loc[k_idx, "Mennyiség"]))
                            remaining = current_qty - ordered_qty
                            if remaining <= 0:
                                df_keszlet = df_keszlet.drop(k_idx)
                            else:
                                df_keszlet.loc[k_idx, "Mennyiség"] = str(remaining)

                        new_kiadas = pd.DataFrame([{
                            "Idopont": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Beszállító": brand, "Termék neve": name, "Lot szám": lot,
                            "Mennyiség": qty_str, "Felhasználó": self.username,
                            "Megjegyzés": f"Szállítmány: {shipment_name} ({pickup_date})"
                        }])
                        df_kiadas = pd.concat([df_kiadas, new_kiadas], ignore_index=True)

                        self.log_action(
                            f"Szállítmány összekészítve & kiadva [{shipment_name}]: {brand} - {name}, Mennyiség: {qty_str}")

                save_sheet_data("Megrendelesek", df_orders)
                save_sheet_data("Keszlet", df_keszlet)
                save_sheet_data("Kiadasok", df_kiadas)

                self.refresh_osszekeszi_view()
                self.refresh_keszlet_view()
                if hasattr(self, "refresh_kiadas_view"):
                    self.refresh_kiadas_view()
                if hasattr(self, "refresh_admin_szallitas_view"):
                    self.refresh_admin_szallitas_view()

                html_content = f"""
                        <!DOCTYPE html>
                        <html lang="hu">
                        <head>
                            <meta charset="UTF-8">
                            <title>Szállítólevél</title>
                            <style>
                                body {{ font-family: monospace; white-space: pre-wrap; margin: 20px; font-size: 14px; }}
                            </style>
                        </head>
                        <body onload="window.print();">
        {text_box.get("1.0", "end")}
                        </body>
                        </html>
                        """

                # --- ITT VAN AZ ÚJ MENTÉSI LOGIKA ---
                import re
                save_dir = os.path.join(os.getcwd(), "szallitolevelek")
                os.makedirs(save_dir, exist_ok=True)

                current_date_str = datetime.date.today().strftime("%Y-%m-%d")
                safe_shipment_name = re.sub(r'[\/*?:"<>|]', "", default_shipment_name)
                file_name = f"{current_date_str}_{safe_shipment_name}.html"
                file_path = os.path.join(save_dir, file_name)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                # ------------------------------------

                temp_path = os.path.join(tempfile.gettempdir(), "szallitolevelek.html")
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                webbrowser.open(f"file:///{temp_path}")

                messagebox.showinfo("Nyomtatás",
                                    f"A szállítólevél mentve ide:\n{file_path}\nés a nyomtatási ablak megnyitva!",
                                    parent=preview_win)
                preview_win.destroy()

            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba történt a mentés vagy nyomtatás közben: {e}", parent=preview_win)

        btn_print = ctk.CTkButton(btn_frame, text="🖨️ Nyomtatás és Véglegesítés", command=print_and_finalize, fg_color="green", width=220, height=40)
        btn_print.pack(side="left", padx=10)

        btn_close = ctk.CTkButton(btn_frame, text="Mégse / Bezárás", command=preview_win.destroy, fg_color="gray", width=150, height=40)
        btn_close.pack(side="right", padx=10)

    def delete_order_admin(self):
        if self.role not in ["admin", "vezető"]:
            return
        selected = self.osszekeszi_tree.selection()
        if not selected:
            return
        item_values = self.osszekeszi_tree.item(selected, "values")
        if messagebox.askyesno("Törlés", "Biztosan törlöd ezt a megrendelést az összekészítési listáról?"):
            df = load_sheet_data("Megrendelesek")
            df = df[~((df["Szallitmany_Nev"] == item_values[1]) & (df["Beszállító"] == item_values[2]) & (df["Termék neve"] == item_values[3]) & (df["Lot szám"] == item_values[4]) & (df["Mennyiség"] == item_values[5]))]
            save_sheet_data("Megrendelesek", df)
            self.log_action(f"Megrendelés törölve az összekészítésből: {item_values[1]} -> {item_values[3]}")
            self.refresh_osszekeszi_view()

    # --- 4. KIADÁSOK / ELŐZMÉNYEK FÜL ---
    def build_kiadas_tab(self):
        ctk.CTkLabel(self.tab_kiadas, text="Korábbi kiadások / Kiszállítások előzményei", font=("Arial", 16, "bold")).pack(pady=10)

        table_frame = ctk.CTkFrame(self.tab_kiadas)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Időpont", "Beszállító", "Termék neve", "Lot szám", "Mennyiség", "Felhasználó", "Megjegyzés")
        self.kiadas_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.kiadas_tree.heading(col, text=col)
            self.kiadas_tree.column(col, width=130)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.kiadas_tree.yview)
        self.kiadas_tree.configure(yscrollcommand=scrollbar.set)
        self.kiadas_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        btn_refresh = ctk.CTkButton(self.tab_kiadas, text="Előzmények Frissítése", command=self.refresh_kiadas_view, fg_color="gray", width=200)
        btn_refresh.pack(pady=10)

        self.refresh_kiadas_view()

    def refresh_kiadas_view(self):
        if not hasattr(self, "kiadas_tree"):
            return
        for row in self.kiadas_tree.get_children():
            self.kiadas_tree.delete(row)

        df = load_sheet_data("Kiadasok")
        if df.empty:
            return

        for _, row in df.iterrows():
            self.kiadas_tree.insert("", "end", values=(
                row.get("Idopont", ""), row.get("Beszállító", ""), row.get("Termék neve", ""),
                row.get("Lot szám", ""), row.get("Mennyiség", ""), row.get("Felhasználó", ""), row.get("Megjegyzés", "")
            ))

    # --- 5. FEJLESZTÉSI JAVASLATOK FÜL ---
    def build_javaslatok_tab(self):
        ctk.CTkLabel(self.tab_javaslatok, text="Fejlesztési javaslatok beküldése és kezelése", font=("Arial", 16, "bold")).pack(pady=10)

        input_frame = ctk.CTkFrame(self.tab_javaslatok)
        input_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(input_frame, text="Új fejlesztési javaslat írása:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(5, 0))

        self.javaslat_textbox = ctk.CTkTextbox(input_frame, height=80, width=570)
        self.javaslat_textbox.pack(padx=10, pady=5, fill="x")

        def submit_suggestion():
            text = self.javaslat_textbox.get("1.0", "end").strip()
            if not text:
                messagebox.showwarning("Figyelmeztetés", "A javaslat mező nem lehet üres!", parent=self.tab_javaslatok)
                return

            df = load_sheet_data("FejlesztesiJavaslatok")
            new_id = str(len(df) + 1) if not df.empty else "1"
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            new_row = pd.DataFrame([{
                "ID": new_id, "Felhasznalo": self.username, "Javaslat": text, "Idopont": timestamp
            }])
            save_sheet_data("FejlesztesiJavaslatok", pd.concat([df, new_row], ignore_index=True))
            self.log_action(f"Fejlesztési javaslat beküldve: {text[:30]}...")
            self.javaslat_textbox.delete("1.0", "end")
            messagebox.showinfo("Siker", "Fejlesztési javaslat sikeresen elküldve!", parent=self.tab_javaslatok)
            if self.role == "admin" and hasattr(self, "refresh_javaslatok_view"):
                self.refresh_javaslatok_view()

        ctk.CTkButton(input_frame, text="Javaslat elküldése", command=submit_suggestion, fg_color="green", width=200).pack(anchor="w", padx=10, pady=(0, 10))

        if self.role == "admin":
            admin_frame = ctk.CTkFrame(self.tab_javaslatok)
            admin_frame.pack(fill="both", expand=True, padx=10, pady=10)

            ctk.CTkLabel(admin_frame, text="Adminisztrátori Javaslat Kezelő (Összes beküldött javaslat):", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)

            table_frame = ctk.CTkFrame(admin_frame)
            table_frame.pack(fill="both", expand=True, padx=5, pady=5)

            columns = ("ID", "Felhasználó", "Időpont", "Javaslat")
            self.javaslat_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
            for col in columns:
                self.javaslat_tree.heading(col, text=col)
                self.javaslat_tree.column(col, width=120 if col != "Javaslat" else 400)

            scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.javaslat_tree.yview)
            self.javaslat_tree.configure(yscrollcommand=scrollbar.set)
            self.javaslat_tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            btn_action_frame = ctk.CTkFrame(admin_frame, fg_color="transparent")
            btn_action_frame.pack(fill="x", padx=5, pady=5)

            def edit_suggestion():
                selected = self.javaslat_tree.selection()
                if not selected:
                    messagebox.showwarning("Figyelmeztetés", "Válassz ki egy javaslatot a szerkesztéshez!", parent=self.tab_javaslatok)
                    return
                vals = self.javaslat_tree.item(selected, "values")
                item_id, user_name, tijd, current_text = vals

                edit_win = ctk.CTkToplevel(self)
                edit_win.title("Javaslat Szerkesztése")
                edit_win.geometry("400x250")
                edit_win.grab_set()

                ctk.CTkLabel(edit_win, text=f"Javaslat szerkesztése ({user_name}):").pack(anchor="w", padx=20, pady=(15, 5))
                e_box = ctk.CTkTextbox(edit_win, height=100, width=360)
                e_box.pack(padx=20, pady=5)
                e_box.insert("1.0", current_text)

                def save_edited():
                    new_txt = e_box.get("1.0", "end").strip()
                    if not new_txt:
                        messagebox.showerror("Hiba", "A szöveg nem lehet üres!", parent=edit_win)
                        return
                    df = load_sheet_data("FejlesztesiJavaslatok")
                    idx = df[df["ID"].astype(str) == str(item_id)].index
                    if not idx.empty:
                        df.loc[idx, "Javaslat"] = new_txt
                        save_sheet_data("FejlesztesiJavaslatok", df)
                        self.log_action(f"Fejlesztési javaslat szerkesztve (ID: {item_id})")
                        self.refresh_javaslatok_view()
                        edit_win.destroy()
                        messagebox.showinfo("Siker", "Javaslat módosítva!", parent=self.tab_javaslatok)

                ctk.CTkButton(edit_win, text="Mentés", command=save_edited, fg_color="green", width=150).pack(pady=10)

            def delete_suggestion():
                selected = self.javaslat_tree.selection()
                if not selected:
                    messagebox.showwarning("Figyelmeztetés", "Válassz ki egy javaslatot a törléshez!", parent=self.tab_javaslatok)
                    return
                vals = self.javaslat_tree.item(selected, "values")
                item_id = vals[0]

                if messagebox.askyesno("Törlés", "Biztosan törlöd ezt a fejlesztési javaslatot?"):
                    df = load_sheet_data("FejlesztesiJavaslatok")
                    df = df[df["ID"].astype(str) != str(item_id)]
                    save_sheet_data("FejlesztesiJavaslatok", df)
                    self.log_action(f"Fejlesztési javaslat törölve (ID: {item_id})")
                    self.refresh_javaslatok_view()

            btn_edit = ctk.CTkButton(btn_action_frame, text="Kijelölt szerkesztése", command=edit_suggestion, fg_color="darkorange", width=180)
            btn_edit.pack(side="left", padx=5)

            btn_del = ctk.CTkButton(btn_action_frame, text="Kijelölt törlése", command=delete_suggestion, fg_color="red", width=150)
            btn_del.pack(side="left", padx=5)

            self.refresh_javaslatok_view()

    def refresh_javaslatok_view(self):
        if not hasattr(self, "javaslat_tree"):
            return
        for row in self.javaslat_tree.get_children():
            self.javaslat_tree.delete(row)
        df = load_sheet_data("FejlesztesiJavaslatok")
        if df.empty:
            return
        for _, row in df.iterrows():
            self.javaslat_tree.insert("", "end", values=(
                row.get("ID", ""), row.get("Felhasznalo", ""), row.get("Idopont", ""), row.get("Javaslat", "")
            ))

    # --- 6. NAPLÓ FÜL ---
    def build_naplo_tab(self):
        ctk.CTkLabel(self.tab_naplo, text="Rendszerszintű eseménynapló", font=("Arial", 16, "bold")).pack(pady=10)
        table_frame = ctk.CTkFrame(self.tab_naplo)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Időpont", "Felhasználó", "Művelet")
        self.naplo_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.naplo_tree.heading(col, text=col)
            self.naplo_tree.column(col, width=250)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.naplo_tree.yview)
        self.naplo_tree.configure(yscrollcommand=scrollbar.set)
        self.naplo_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.refresh_naplo_view()

    def refresh_naplo_view(self):
        if not hasattr(self, "naplo_tree"):
            return
        for row in self.naplo_tree.get_children():
            self.naplo_tree.delete(row)
        df = load_sheet_data("Naplo")
        if df.empty:
            return
        for _, row in df.iterrows():
            self.naplo_tree.insert("", "end", values=(row.get("Idopont", ""), row.get("Felhasználó", ""), row.get("Muvelet", "")))

    # --- 7. FELHASZNÁLÓ KEZELÉS FÜL ---
    def build_users_tab(self):
        ctk.CTkLabel(self.tab_users, text="Rendszerfelhasználók kezelése", font=("Arial", 16, "bold")).pack(pady=10)

        form_frame = ctk.CTkFrame(self.tab_users)
        form_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Felhasználónév:").pack(side="left", padx=5)
        self.new_user_entry = ctk.CTkEntry(form_frame, width=150)
        self.new_user_entry.pack(side="left", padx=5)

        ctk.CTkLabel(form_frame, text="Jelszó:").pack(side="left", padx=5)
        self.new_pass_entry = ctk.CTkEntry(form_frame, width=150, show="*")
        self.new_pass_entry.pack(side="left", padx=5)

        ctk.CTkLabel(form_frame, text="Szint:").pack(side="left", padx=5)
        self.new_role_combo = ctk.CTkComboBox(form_frame, values=["user", "vezető", "admin"], width=100)
        self.new_role_combo.pack(side="left", padx=5)
        self.new_role_combo.set("user")

        btn_add_user = ctk.CTkButton(form_frame, text="Új felhasználó hozzáadása", command=self.add_user, fg_color="green")
        btn_add_user.pack(side="left", padx=10)

        table_frame = ctk.CTkFrame(self.tab_users)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Felhasználónév", "Jelszó", "Szint")
        self.users_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=200)

        self.users_tree.pack(side="left", fill="both", expand=True)

        btn_del_user = ctk.CTkButton(self.tab_users, text="Kiválasztott felhasználó törlése", command=self.delete_user, fg_color="red")
        btn_del_user.pack(pady=10)

        self.refresh_users_view()

    def refresh_users_view(self):
        if not hasattr(self, "users_tree"):
            return
        for row in self.users_tree.get_children():
            self.users_tree.delete(row)
        df = load_sheet_data("Felhasznalok")
        if df.empty:
            return
        for _, row in df.iterrows():
            self.users_tree.insert("", "end", values=(row.get("felhasznalo", ""), row.get("jelszo", ""), row.get("szint", "")))

    def add_user(self):
        u = self.new_user_entry.get().strip()
        p = self.new_pass_entry.get().strip()
        s = self.new_role_combo.get().strip()

        if not u or not p:
            messagebox.showerror("Hiba", "Add meg a felhasználónevet és jelszót!", parent=self.tab_users)
            return

        df = load_sheet_data("Felhasznalok")
        if not df.empty and u in df["felhasznalo"].values:
            messagebox.showerror("Hiba", "Már létezik ilyen felhasználó!", parent=self.tab_users)
            return

        new_row = pd.DataFrame([{"felhasznalo": u, "jelszo": p, "szint": s}])
        save_sheet_data("Felhasznalok", pd.concat([df, new_row], ignore_index=True))
        self.log_action(f"Új felhasználó létrehozva: {u} ({s})")
        self.refresh_users_view()
        self.new_user_entry.delete(0, "end")
        self.new_pass_entry.delete(0, "end")
        messagebox.showinfo("Siker", "Felhasználó létrehozva!", parent=self.tab_users)

    def delete_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy felhasználót!", parent=self.tab_users)
            return
        u_name = self.users_tree.item(selected, "values")[0]
        if u_name == "admin":
            messagebox.showerror("Hiba", "Az alapértelmezett admin felhasználó nem törölhető!", parent=self.tab_users)
            return

        if messagebox.askyesno("Törlés", "Biztosan törlöd a következő felhasználót: " + u_name + "?"):
            df = load_sheet_data("Felhasznalok")
            df = df[df["felhasznalo"] != u_name]
            save_sheet_data("Felhasznalok", df)
            self.log_action(f"Felhasználó törölve: {u_name}")
            self.refresh_users_view()


if __name__ == "__main__":
    app = KeszletApp()
    app.mainloop()