import datetime
import os
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import pandas as pd
from tkcalendar import Calendar  # Szükséges a naptár ablakhoz (pip install tkcalendar)

# --- Globális Beállítások ---
ctk.set_appearance_mode("System")  # Igazodik a rendszer témájához (világos/sötét)
ctk.set_default_color_theme("blue")  # Alapértelmezett kék színvilág

# Az adatbázis mappája, ahová a CSV fájlok mentésre kerülnek
DATABASE_PATH = r"C:\Users\Orovec Árpád\Desktop\keszletproba"

# Ha a mappa még nem létezik, automatikusan létrehozzuk
if not os.path.exists(DATABASE_PATH):
    os.makedirs(DATABASE_PATH)


def get_file_path(worksheet_name):
    """Visszaadja a megadott táblázat teljes fájlelérési útvonalát a db_data mappán belül asdasd a."""
    return os.path.join(DATABASE_PATH, f"{worksheet_name}.csv")


def load_sheet_data(worksheet_name):
    """
    Betölti egy adott nevű CSV fájl tartalmát egy pandas DataFrame-be.
    Ha a fájl még nem létezik, egy üres DataFrame-et ad vissza.
    """
    filepath = get_file_path(worksheet_name)
    if os.path.exists(filepath):
        try:
            return pd.read_csv(filepath, dtype=str)  # Minden adatot stringként olvasunk az elírások elkerülésére
        except Exception as e:
            print(f"Hiba olvasás közben ({worksheet_name}): {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def save_sheet_data(worksheet_name, df):
    """Elmenti a pandas DataFrame adatait a megadott nevű CSV fájlba utf-8-sig kódolással."""
    filepath = get_file_path(worksheet_name)
    try:
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
    except Exception as e:
        messagebox.showerror("Mentési hiba", f"Nem sikerült menteni a fájlt: {e}")


# --- Fő Alkalmazás Osztály ---
class KeszletApp(ctk.CTk):
    def __init__(self):
        """Konstruktor: Létrehozza a főablakot, előkészíti a felhasználói adatbázist és betölti a bejelentkezést."""
        super().__init__()
        self.title("Készletnyilvántartás - Bejelentkezés")
        self.geometry("400x350")
        self.resizable(False, False)

        self.init_users_db()  # Alapértelmezett admin felhasználó létrehozása, ha nem létezik
        self.build_login_screen()  # Bejelentkezési felület megjelenítése

    def init_users_db(self):
        """Létrehozza az alapértelmezett admin fiókot a 'Felhasznalok.csv'-ben, ha az teljesen üres."""
        df = load_sheet_data("Felhasznalok")
        if df.empty:
            df = pd.DataFrame([
                {"felhasznalo": "admin", "jelszo": "admin123", "szint": "admin"}
            ])
            save_sheet_data("Felhasznalok", df)

    def clear_window(self):
        """Törli az ablakban lévő összes aktuális elemet (widgetet), hogy új nézetet lehessen betölteni."""
        for widget in self.winfo_children():
            widget.destroy()

    # --- Bejelentkezési Felület ---
    def build_login_screen(self):
        """Felépíti a bejelentkezési képernyőt (felhasználónév, jelszó mezők és belépés gomb)."""
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
        """Ellenőrzi a megadott felhasználónevet és jelszót a 'Felhasznalok' adatbázisból."""
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

    # --- Fő Alkalmazás Felületének Betöltése ---
    def start_main_app(self, username, role):
        """Sikeres bejelentkezés után átállítja az ablakot a fő programfelületre (fülek, funkciók)."""
        self.username = username
        self.role = role

        self.clear_window()
        self.geometry("1200x700")
        self.title(f"Készletnyilvántartás - Bejelentkezve: {self.username} ({self.role.upper()})")

        # Fő fülek konténere (Tabview)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Fülek létrehozása szerepkör alapján
        self.tab_keszlet = self.tabview.add("Készlet & Keresés")
        self.tab_osszekeszi = self.tabview.add("Áru Összekészítés (Kimenő)")
        self.tab_kiadas = self.tabview.add("Előzmények (Kiadva)")

        if self.role == "admin":
            self.tab_admin_szallitas = self.tabview.add("Admin Kiszállítás")
            self.tab_naplo = self.tabview.add("Napló")
            self.tab_users = self.tabview.add("Felhasználó kezelés")

        # Fülek tartalmának felépítése
        self.build_keszlet_tab()
        self.build_osszekeszi_tab()
        self.build_kiadas_tab()

        if self.role == "admin":
            self.build_admin_szallitas_tab()
            self.build_naplo_tab()
            self.build_users_tab()

        self.log_action("Bejelentkezés a rendszerbe")

    def log_action(self, action):
        """Rendszerszintű eseményeket rögzít a 'Naplo.csv' fájlban időbélyeggel és felhasználónévvel."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_log = pd.DataFrame([{"Idopont": timestamp, "Felhasznalo": self.username, "Muvelet": action}])

        df = load_sheet_data("Naplo")
        df = pd.concat([df, new_log], ignore_index=True)
        save_sheet_data("Naplo", df)

        if hasattr(self, "naplo_tree"):
            self.refresh_naplo_view()

    # --- 1. KÉSZLET & KERESÉS FÜL ---
    def build_keszlet_tab(self):
        """Létrehozza a raktárkészlet kezelő felületét."""
        control_frame = ctk.CTkFrame(self.tab_keszlet)
        control_frame.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(control_frame, placeholder_text="Keresés (Beszállító / Név / Lot)...",
                                         width=250)
        self.search_entry.pack(side="left", padx=5, pady=5)

        btn_search = ctk.CTkButton(control_frame, text="Keresés / Szűrés", command=self.refresh_keszlet_view)
        btn_search.pack(side="left", padx=5, pady=5)

        btn_reset = ctk.CTkButton(control_frame, text="Összes mutatása", command=self.reset_keszlet_search,
                                  fg_color="gray")
        btn_reset.pack(side="left", padx=5, pady=5)

        # Csak az admin törölhet cikket
        if self.role == "admin":
            btn_del = ctk.CTkButton(control_frame, text="Kijelölt törlése", command=self.delete_product, fg_color="red")
            btn_del.pack(side="right", padx=5, pady=5)

        btn_ship = ctk.CTkButton(control_frame, text="Kiválasztott kiadása", command=self.open_ship_window,
                                 fg_color="darkorange")
        btn_ship.pack(side="right", padx=5, pady=5)

        btn_add = ctk.CTkButton(control_frame, text="+ Új Cikk / Gyártás", command=self.open_add_product_window,
                                fg_color="green")
        btn_add.pack(side="right", padx=5, pady=5)

        table_frame = ctk.CTkFrame(self.tab_keszlet)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
        "ID", "Beszállító (Brand)", "Termék neve", "Lot szám", "Gyártás ideje", "Lejárat", "Mennyiség", "Megjegyzés")
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
        """Frissíti a készlet táblázat tartalmát a CSV fájlból."""
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
                row.get("ID", ""),
                row.get("Beszállító", ""),
                row.get("Termék neve", ""),
                row.get("Lot szám", ""),
                row.get("Gyártás ideje", ""),
                row.get("Lejárat", ""),
                qty,
                row.get("Megjegyzés", "")
            ))

    def reset_keszlet_search(self):
        self.search_entry.delete(0, "end")
        self.refresh_keszlet_view()

    def open_add_product_window(self):
        """Új cikk / gyártás rögzítése."""
        win = ctk.CTkToplevel(self)
        win.title("Új termék / Gyártás rögzítése")
        win.geometry("400x600")
        win.grab_set()
        win.focus_set()

        df_existing = load_sheet_data("Keszlet")
        existing_brands = sorted(list(df_existing[
                                          "Beszállító"].dropna().unique())) if not df_existing.empty and "Beszállító" in df_existing.columns else []
        existing_names = sorted(list(df_existing["Termék neve"].dropna().unique())) if not df_existing.empty else []

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
                selected_date = cal.selection_get().strftime("%Y-%m-%d")
                e_lejarat.delete(0, "end")
                e_lejarat.insert(0, selected_date)
                cal_win.destroy()

            ctk.CTkButton(cal_win, text="Kiválasztás", command=set_date, fg_color="green").pack(pady=10)

        btn_cal = ctk.CTkButton(date_frame, text="📅 Naptár", width=100, command=open_calendar)
        btn_cal.pack(side="right")

        ctk.CTkLabel(win, text="Mennyiség (egész szám, min. 1):").pack(anchor="w", padx=20, pady=(10, 0))
        e_mennyiseg = ctk.CTkEntry(win, width=350)
        e_mennyiseg.insert(0, "1")
        e_mennyiseg.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Megjegyzés (Gyártás):").pack(anchor="w", padx=20, pady=(10, 0))
        e_megj = ctk.CTkEntry(win, width=350)
        e_megj.pack(padx=20, pady=5)

        def save_new():
            brand = e_brand.get().strip()
            name = e_name.get().strip()
            lot = e_lot.get().strip()
            gyartas = e_gyartas.get().strip()
            lejarat = e_lejarat.get().strip()
            menny = e_mennyiseg.get().strip()
            megj = e_megj.get().strip()

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
                if messagebox.askyesno("Létező Lot szám",
                                       f"Már létezik termék ezzel a Lot számmal ({lot}). Hozzáadjuk a mennyiséget a meglévőhöz?",
                                       parent=win):
                    idx = df[df["Lot szám"] == lot].index[0]
                    current_qty = int(float(df.loc[idx, "Mennyiség"]))
                    new_total_qty = current_qty + menny_val
                    df.loc[idx, "Mennyiség"] = str(new_total_qty)

                    if megj:
                        old_megj = str(df.loc[idx, "Megjegyzés"])
                        df.loc[idx, "Megjegyzés"] = f"{old_megj} | {megj}" if old_megj and old_megj != "nan" else megj

                    save_sheet_data("Keszlet", df)
                    self.log_action(f"Meglévő Lot bővítve: {brand} - {name} (Lot: {lot}), +{menny_val}")
                    self.refresh_keszlet_view()
                    if hasattr(self, "refresh_admin_szallitas_view"):
                        self.refresh_admin_szallitas_view()
                    win.destroy()
                    messagebox.showinfo("Siker", "A mennyiség sikeresen hozzáadva a meglévő Lot-hoz!", parent=self)
                    return
                else:
                    return

            new_id = str(len(df) + 1)
            new_row = pd.DataFrame([{
                "ID": new_id,
                "Beszállító": brand,
                "Termék neve": name,
                "Lot szám": lot,
                "Gyártás ideje": gyartas,
                "Lejárat": lejarat,
                "Mennyiség": str(menny_val),
                "Megjegyzés": megj
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
        # Csak admin hajthatja végre
        if self.role != "admin":
            messagebox.showerror("Jogosultság hiba", "Ehhez a művelethez nincs jogosultságod!")
            return

        selected_item = self.keszlet_tree.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Kérlek válassz ki egy elemet a törléshez!")
            return

        item_values = self.keszlet_tree.item(selected_item, "values")
        item_id = item_values[0]
        item_brand = item_values[1]
        item_name = item_values[2]

        if messagebox.askyesno("Megerősítés",
                               f"Biztosan törölni akarod a következő cikket: {item_brand} - {item_name}?"):
            df = load_sheet_data("Keszlet")
            df = df[df["ID"].astype(str) != str(item_id)]
            save_sheet_data("Keszlet", df)

            self.log_action(f"Termék törölve: {item_brand} - {item_name} (ID: {item_id})")
            self.refresh_keszlet_view()
            if hasattr(self, "refresh_admin_szallitas_view"):
                self.refresh_admin_szallitas_view()

    def open_ship_window(self):
        """Közvetlen kiadás ablak."""
        selected_item = self.keszlet_tree.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Kérlek válassz ki egy elemet a készletből a kiadáshoz!")
            return

        item_values = self.keszlet_tree.item(selected_item, "values")
        item_id, brand, name, lot, gyartas, lejarat, max_menny, _ = item_values

        win = ctk.CTkToplevel(self)
        win.title("Termék Kiszállítása / Kiadása")
        win.geometry("400x350")
        win.grab_set()
        win.focus_set()

        ctk.CTkLabel(win, text=f"Kiadás alatt:\n{brand} - {name}\n(Lot: {lot})", font=("Arial", 14, "bold"),
                     justify="center").pack(pady=10)
        ctk.CTkLabel(win, text=f"Jelenlegi készlet: {max_menny}").pack(pady=5)

        ctk.CTkLabel(win, text="Kiadandó mennyiség (egész szám):").pack(anchor="w", padx=20)
        e_menny = ctk.CTkEntry(win, width=350)
        e_menny.pack(padx=20, pady=5)
        e_menny.focus()

        ctk.CTkLabel(win, text="Megjegyzés (Kiadás):").pack(anchor="w", padx=20)
        e_megj = ctk.CTkEntry(win, width=350)
        e_megj.pack(padx=20, pady=5)

        def confirm_shipment():
            kiad_menny = e_menny.get().strip()
            megj = e_megj.get().strip()

            if not kiad_menny:
                messagebox.showerror("Hiba", "Add meg a kiadandó mennyiséget!", parent=win)
                return

            try:
                kiad_f = int(kiad_menny)
                max_f = int(max_menny)
            except ValueError:
                messagebox.showerror("Hiba", "Csak érvényes egész szám adható meg!", parent=win)
                return

            if kiad_f < 1:
                messagebox.showerror("Hiba", "A kiadandó mennyiség legalább 1 kell legyen!", parent=win)
                return

            if kiad_f > max_f:
                messagebox.showerror("Hiba", "Nincs elegendő termék készleten!", parent=win)
                return

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
                "Beszállító": brand,
                "Termék neve": name,
                "Lot szám": lot,
                "Mennyiség": str(kiad_f),
                "Felhasználó": self.username,
                "Megjegyzés": megj
            }])
            df_kiadas = pd.concat([df_kiadas, new_kiadas], ignore_index=True)
            save_sheet_data("Kiadasok", df_kiadas)

            self.log_action(f"Kiadás: {brand} - {name} (Lot: {lot}), Mennyiség: {kiad_f}")
            self.refresh_keszlet_view()
            if hasattr(self, "refresh_admin_szallitas_view"):
                self.refresh_admin_szallitas_view()
            if hasattr(self, "refresh_kiadas_view"):
                self.refresh_kiadas_view()

            win.destroy()
            messagebox.showinfo("Siker", "Kiadás sikeresen rögzítve!", parent=self)

        ctk.CTkButton(win, text="Kiadás rögzítése", command=confirm_shipment, fg_color="darkorange", width=200).pack(
            pady=20)

    # --- 2. ADMIN KISZÁLLÍTÁS FÜL ---
    def build_admin_szallitas_tab(self):
        """Admin felület, ahol kiválasztható a készletből, hogy mit kell kiszállítani/összekészíteni időponttal és idősávval."""
        ctk.CTkLabel(self.tab_admin_szallitas, text="Rendelés / Kiszállítás összeállítása a raktárosoknak",
                     font=("Arial", 16, "bold")).pack(pady=10)

        top_frame = ctk.CTkFrame(self.tab_admin_szallitas)
        top_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("ID", "Beszállító", "Termék neve", "Lot szám", "Elérhető készlet", "Lejárat")
        self.admin_keszlet_tree = ttk.Treeview(top_frame, columns=columns, show="headings", height=8)

        for col in columns:
            self.admin_keszlet_tree.heading(col, text=col)
            self.admin_keszlet_tree.column(col, width=130)

        scrollbar = ttk.Scrollbar(top_frame, orient="vertical", command=self.admin_keszlet_tree.yview)
        self.admin_keszlet_tree.configure(yscrollcommand=scrollbar.set)
        self.admin_keszlet_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Frissítés gomb sáv az admin tabon
        refresh_frame = ctk.CTkFrame(self.tab_admin_szallitas, fg_color="transparent")
        refresh_frame.pack(fill="x", padx=10, pady=5)

        btn_refresh_admin = ctk.CTkButton(refresh_frame, text="🔄 Adatbázis / Lista Frissítése",
                                          command=self.refresh_admin_szallitas_view, fg_color="gray", width=200)
        btn_refresh_admin.pack(side="left", padx=5)

        # Paraméterező sáv (Mennyiség, Dátum, Idősáv, Megjegyzés)
        action_frame = ctk.CTkFrame(self.tab_admin_szallitas)
        action_frame.pack(fill="x", padx=10, pady=5)

        # 1. Sor: Mennyiség és Megjegyzés
        row1_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        row1_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(row1_frame, text="Mennyiség:").pack(side="left", padx=5)
        self.admin_qty_entry = ctk.CTkEntry(row1_frame, width=80)
        self.admin_qty_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row1_frame, text="Megjegyzés:").pack(side="left", padx=5)
        self.admin_note_entry = ctk.CTkEntry(row1_frame, width=250)
        self.admin_note_entry.pack(side="left", padx=5)

        # 2. Sor: Felvétel dátuma + Óra tól-ig
        row2_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        row2_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(row2_frame, text="Felvétel napja:").pack(side="left", padx=5)
        self.admin_date_entry = ctk.CTkEntry(row2_frame, width=120)
        self.admin_date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.admin_date_entry.pack(side="left", padx=5)

        def open_admin_calendar():
            cal_win = ctk.CTkToplevel(self)
            cal_win.title("Felvétel dátumának kiválasztása")
            cal_win.geometry("300x300")
            cal_win.grab_set()

            cal = Calendar(cal_win, selectmode='day', year=datetime.date.today().year,
                           month=datetime.date.today().month, day=datetime.date.today().day)
            cal.pack(pady=10, fill="both", expand=True)

            def set_admin_date():
                selected_date = cal.selection_get().strftime("%Y-%m-%d")
                self.admin_date_entry.delete(0, "end")
                self.admin_date_entry.insert(0, selected_date)
                cal_win.destroy()

            ctk.CTkButton(cal_win, text="Kiválasztás", command=set_admin_date, fg_color="green").pack(pady=10)

        btn_admin_cal = ctk.CTkButton(row2_frame, text="📅 Naptár", width=90, command=open_admin_calendar)
        btn_admin_cal.pack(side="left", padx=5)

        ctk.CTkLabel(row2_frame, text="Idősáv (tól-ig óra):").pack(side="left", padx=(15, 5))
        self.admin_timeslot_entry = ctk.CTkEntry(row2_frame, placeholder_text="pl. 08:00 - 12:00", width=140)
        self.admin_timeslot_entry.pack(side="left", padx=5)

        btn_send_to_user = ctk.CTkButton(row2_frame, text="Küldés Összekészítésre (Usernek)",
                                         command=self.send_order_to_user, fg_color="green")
        btn_send_to_user.pack(side="right", padx=5)

        self.refresh_admin_szallitas_view()

    def refresh_admin_szallitas_view(self):
        """Újratölti a készletet a CSV fájlból az Admin Kiszállítás fülön."""
        if not hasattr(self, "admin_keszlet_tree"):
            return
        for row in self.admin_keszlet_tree.get_children():
            self.admin_keszlet_tree.delete(row)

        df = load_sheet_data("Keszlet")
        if df.empty:
            return

        for _, row in df.iterrows():
            qty = row.get("Mennyiség", "0")
            try:
                qty = str(int(float(qty)))
            except ValueError:
                pass

            self.admin_keszlet_tree.insert("", "end", values=(
                row.get("ID", ""),
                row.get("Beszállító", ""),
                row.get("Termék neve", ""),
                row.get("Lot szám", ""),
                qty,
                row.get("Lejárat", "")
            ))

    def send_order_to_user(self):
        """Átküldi a tételt az összekészítési listára időponttal és idősávval együtt."""
        selected = self.admin_keszlet_tree.selection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy tételt a készletből!",
                                   parent=self.tab_admin_szallitas)
            return

        item_values = self.admin_keszlet_tree.item(selected, "values")
        item_id, brand, name, lot, max_qty, lejarat = item_values

        qty_str = self.admin_qty_entry.get().strip()
        note = self.admin_note_entry.get().strip()
        pickup_date = self.admin_date_entry.get().strip()
        timeslot = self.admin_timeslot_entry.get().strip()

        if not qty_str:
            messagebox.showerror("Hiba", "Add meg a mennyiséget!", parent=self.tab_admin_szallitas)
            return

        if not pickup_date or not timeslot:
            messagebox.showerror("Hiba", "Add meg a felvétel napját és az idősávot is!",
                                 parent=self.tab_admin_szallitas)
            return

        try:
            qty_val = int(qty_str)
            max_val = int(max_qty)
        except ValueError:
            messagebox.showerror("Hiba", "A mennyiség csak egész szám lehet!", parent=self.tab_admin_szallitas)
            return

        if qty_val < 1:
            messagebox.showerror("Hiba", "A mennyiség legalább 1 kell legyen!", parent=self.tab_admin_szallitas)
            return

        if qty_val > max_val:
            messagebox.showerror("Hiba", "Nincs elegendő készleten ebből a mennyiségből!",
                                 parent=self.tab_admin_szallitas)
            return

        df_orders = load_sheet_data("Megrendelesek")
        new_order = pd.DataFrame([{
            "ID": item_id,
            "Beszállító": brand,
            "Termék neve": name,
            "Lot szám": lot,
            "Mennyiség": str(qty_val),
            "Felvetel_Datum": pickup_date,
            "Idosav": timeslot,
            "Megjegyzés": note,
            "Allapot": "Függőben (Összekészítés alatt)"
        }])
        df_orders = pd.concat([df_orders, new_order], ignore_index=True)
        save_sheet_data("Megrendelesek", df_orders)

        self.log_action(
            f"Kiszállítás küldve összekészítésre: {brand} - {name} (Lot: {lot}), Mennyiség: {qty_val}, Időpont: {pickup_date} {timeslot}")
        messagebox.showinfo("Siker",
                            "A tétel sikeresen elküldve a felhasználói összekészítési listára időponttal együtt!",
                            parent=self.tab_admin_szallitas)

        self.admin_qty_entry.delete(0, "end")
        self.admin_note_entry.delete(0, "end")
        self.admin_timeslot_entry.delete(0, "end")

        if hasattr(self, "refresh_osszekeszi_view"):
            self.refresh_osszekeszi_view()

    # --- 3. ÁRU ÖSSZEKÉSZÍTÉS FÜL ---
    def build_osszekeszi_tab(self):
        """A user felület, ahol láthatja az admin által kiírt kimenő árukat a felvételi idővel együtt, és lezárhatja."""
        ctk.CTkLabel(self.tab_osszekeszi, text="Kimenő áruk összekészítése (Raktári feladatok)",
                     font=("Arial", 16, "bold")).pack(pady=10)

        table_frame = ctk.CTkFrame(self.tab_osszekeszi)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
        "Beszállító", "Termék neve", "Lot szám", "Mennyiség", "Felvétel Napja", "Idősáv", "Megjegyzés", "Állapot")
        self.osszekeszi_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.osszekeszi_tree.heading(col, text=col)
            self.osszekeszi_tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.osszekeszi_tree.yview)
        self.osszekeszi_tree.configure(yscrollcommand=scrollbar.set)
        self.osszekeszi_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_frame = ctk.CTkFrame(self.tab_osszekeszi)
        btn_frame.pack(fill="x", padx=10, pady=10)

        btn_complete = ctk.CTkButton(btn_frame,
                                     text="Kiválasztott Összekészítve & Kiszállítva (Lezárás - Készletből levonás)",
                                     command=self.complete_order, fg_color="green", width=400)
        btn_complete.pack(side="left", padx=5)

        # Sima user NE tudjon törölni a megrendelésekből, csak az admin (vagy lezárni a gombbal)
        if self.role == "admin":
            btn_del_order = ctk.CTkButton(btn_frame, text="Megrendelés törlése", command=self.delete_order_admin,
                                          fg_color="red", width=160)
            btn_del_order.pack(side="left", padx=5)

        btn_refresh = ctk.CTkButton(btn_frame, text="Lista Frissítése", command=self.refresh_osszekeszi_view,
                                    fg_color="gray", width=150)
        btn_refresh.pack(side="right", padx=5)

        self.refresh_osszekeszi_view()

    def refresh_osszekeszi_view(self):
        if not hasattr(self, "osszekeszi_tree"):
            return
        for row in self.osszekeszi_tree.get_children():
            self.osszekeszi_tree.delete(row)

        df = load_sheet_data("Megrendelesek")
        if df.empty:
            return

        for _, row in df.iterrows():
            self.osszekeszi_tree.insert("", "end", values=(
                row.get("Beszállító", ""),
                row.get("Termék neve", ""),
                row.get("Lot szám", ""),
                row.get("Mennyiség", ""),
                row.get("Felvetel_Datum", "-"),
                row.get("Idosav", "-"),
                row.get("Megjegyzés", ""),
                row.get("Allapot", "")
            ))

    def complete_order(self):
        """Itt történik a lezárás: Ekkor vonódik le a mennyiség a készletből és kerül át a kiadásokba."""
        selected = self.osszekeszi_tree.selection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy elemet az összekészítési listából!",
                                   parent=self.tab_osszekeszi)
            return

        item_values = self.osszekeszi_tree.item(selected, "values")
        brand, name, lot, qty_str, p_date, p_slot, note, status = item_values

        if messagebox.askyesno("Megerősítés",
                               f"Biztosan véglegesíted az összekészítést? Ez a mennyiség ({qty_str} db) most fog levonódni a készletből: {brand} - {name} (Lot: {lot})"):
            qty_to_ship = int(qty_str)

            # 1. Készletből tényleges levonás Lot alapján
            df_keszlet = load_sheet_data("Keszlet")
            if not df_keszlet.empty and lot in df_keszlet["Lot szám"].values:
                idx = df_keszlet[df_keszlet["Lot szám"] == lot].index[0]
                current_qty = int(float(df_keszlet.loc[idx, "Mennyiség"]))

                remaining = current_qty - qty_to_ship
                if remaining <= 0:
                    df_keszlet = df_keszlet.drop(idx)
                else:
                    df_keszlet.loc[idx, "Mennyiség"] = str(remaining)
                save_sheet_data("Keszlet", df_keszlet)
            else:
                messagebox.showerror("Hiba", "A megadott Lot számú termék már nem található a készletben!",
                                     parent=self.tab_osszekeszi)
                return

            # 2. Kiadások naplózása az előzményekhez (beleírva a felvételi időt is a megjegyzésbe)
            full_note = f"Felvétel: {p_date} ({p_slot})"
            if note and note != "nan":
                full_note += f" | {note}"

            df_kiadas = load_sheet_data("Kiadasok")
            new_kiadas = pd.DataFrame([{
                "Idopont": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Beszállító": brand,
                "Termék neve": name,
                "Lot szám": lot,
                "Mennyiség": str(qty_to_ship),
                "Felhasználó": self.username,
                "Megjegyzés": full_note
            }])
            df_kiadas = pd.concat([df_kiadas, new_kiadas], ignore_index=True)
            save_sheet_data("Kiadasok", df_kiadas)

            # 3. Teljesített rendelés törlése a Megrendelések listából
            df_orders = load_sheet_data("Megrendelesek")
            df_orders = df_orders[~((df_orders["Lot szám"] == lot) & (df_orders["Mennyiség"] == str(qty_to_ship)) & (
                        df_orders["Termék neve"] == name))]
            save_sheet_data("Megrendelesek", df_orders)

            self.log_action(f"Áru összekészítve és készletből levonva: {brand} - {name} (Lot: {lot}), {qty_to_ship} db")

            # Minden nézet frissítése
            self.refresh_osszekeszi_view()
            self.refresh_keszlet_view()
            if hasattr(self, "refresh_admin_szallitas_view"):
                self.refresh_admin_szallitas_view()
            if hasattr(self, "refresh_kiadas_view"):
                self.refresh_kiadas_view()

            messagebox.showinfo("Siker", "A tétel sikeresen lezárva, és a készletből levonásra került!",
                                parent=self.tab_osszekeszi)

    def delete_order_admin(self):
        """Csak az admin törölheti a megrendelést anélkül, hogy az készletlevonást vonna maga után (pl. ha téves volt a kiírás)."""
        if self.role != "admin":
            messagebox.showerror("Jogosultság hiba", "Ehhez a művelethez nincs jogosultságod!")
            return

        selected = self.osszekeszi_tree.selection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy elemet a törléshez!")
            return

        item_values = self.osszekeszi_tree.item(selected, "values")
        brand, name, lot, qty_str, _, _, _, _ = item_values

        if messagebox.askyesno("Megerősítés",
                               f"Biztosan törlöd ezt a megrendelési tételt (készletlevonás nélkül)?\n{brand} - {name} (Lot: {lot})"):
            df_orders = load_sheet_data("Megrendelesek")
            df_orders = df_orders[~((df_orders["Lot szám"] == lot) & (df_orders["Mennyiség"] == str(qty_str)) & (
                        df_orders["Termék neve"] == name))]
            save_sheet_data("Megrendelesek", df_orders)

            self.log_action(f"Megrendelés törölve admin által: {brand} - {name} (Lot: {lot})")
            self.refresh_osszekeszi_view()
            messagebox.showinfo("Siker", "Megrendelés törölve.", parent=self.tab_osszekeszi)

    # --- 4. KIADÁSI LISTA (Előzmények) ---
    def build_kiadas_tab(self):
        control_frame = ctk.CTkFrame(self.tab_kiadas)
        control_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(control_frame, text="Dátum szűrés (ÉÉÉÉ-HH-NN):").pack(side="left", padx=5)
        self.search_kiadas_entry = ctk.CTkEntry(control_frame, placeholder_text="pl. 2026-06-06", width=150)
        self.search_kiadas_entry.pack(side="left", padx=5)

        btn_search = ctk.CTkButton(control_frame, text="Szűrés", command=self.refresh_kiadas_view)
        btn_search.pack(side="left", padx=5)

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

        self.refresh_kiadas_view()

    def refresh_kiadas_view(self):
        if not hasattr(self, "kiadas_tree"):
            return
        for row in self.kiadas_tree.get_children():
            self.kiadas_tree.delete(row)

        df = load_sheet_data("Kiadasok")
        if df.empty:
            return

        filter_date = self.search_kiadas_entry.get().strip()
        if filter_date:
            df = df[df["Idopont"].str.contains(filter_date)]

        for _, row in df.iterrows():
            qty = row.get("Mennyiség", "0")
            try:
                qty = str(int(float(qty)))
            except ValueError:
                pass

            self.kiadas_tree.insert("", "end", values=(
                row.get("Idopont", ""),
                row.get("Beszállító", ""),
                row.get("Termék neve", ""),
                row.get("Lot szám", ""),
                qty,
                row.get("Felhasználó", ""),
                row.get("Megjegyzés", "")
            ))

    # --- 5. NAPLÓ FÜL (Csak Admin) ---
    def build_naplo_tab(self):
        ctk.CTkLabel(self.tab_naplo, text="Rendszerszintű Műveletnapló", font=("Arial", 14)).pack(pady=10)

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

        btn_frame = ctk.CTkFrame(self.tab_naplo)
        btn_frame.pack(fill="x", padx=10, pady=10)

        btn_clear_log = ctk.CTkButton(btn_frame, text="Napló ürítése", command=self.clear_naplo, fg_color="red")
        btn_clear_log.pack(side="left", padx=5)

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
            self.naplo_tree.insert("", "end", values=(
                row.get("Idopont", ""),
                row.get("Felhasználó", ""),
                row.get("Muvelet", "")
            ))

    def clear_naplo(self):
        if messagebox.askyesno("Megerősítés", "Biztosan törölni szeretnéd a teljes naplót?"):
            empty_df = pd.DataFrame(columns=["Idopont", "Felhasználó", "Muvelet"])
            save_sheet_data("Naplo", empty_df)
            self.refresh_naplo_view()
            messagebox.showinfo("Siker", "Napló kiürítve.")

    # --- 6. FELHASZNÁLÓ KEZELÉS FÜL (Csak Admin) ---
    def build_users_tab(self):
        ctk.CTkLabel(self.tab_users, text="Új felhasználó hozzáadása", font=("Arial", 14, "bold")).pack(pady=10)

        form_frame = ctk.CTkFrame(self.tab_users)
        form_frame.pack(padx=10, pady=5, fill="x")

        ctk.CTkLabel(form_frame, text="Felhasználónév:").pack(anchor="w", padx=10)
        self.u_name_entry = ctk.CTkEntry(form_frame, width=300)
        self.u_name_entry.pack(padx=10, pady=5, anchor="w")

        ctk.CTkLabel(form_frame, text="Jelszó:").pack(anchor="w", padx=10)
        self.u_pass_entry = ctk.CTkEntry(form_frame, width=300, show="*")
        self.u_pass_entry.pack(padx=10, pady=5, anchor="w")

        ctk.CTkLabel(form_frame, text="Jogosultság szint:").pack(anchor="w", padx=10)
        self.u_role_menu = ctk.CTkOptionMenu(form_frame, values=["user", "admin"], width=300)
        self.u_role_menu.pack(padx=10, pady=5, anchor="w")

        btn_add_user = ctk.CTkButton(form_frame, text="Felhasználó létrehozása", command=self.add_new_user,
                                     fg_color="green")
        btn_add_user.pack(padx=10, pady=15, anchor="w")

    def add_new_user(self):
        uname = self.u_name_entry.get().strip()
        upass = self.u_pass_entry.get().strip()
        urole = self.u_role_menu.get().strip()

        if not uname or not upass:
            messagebox.showerror("Hiba", "Minden mezőt ki kell tölteni!")
            return

        df = load_sheet_data("Felhasznalok")
        if not df.empty and uname in df["felhasznalo"].values:
            messagebox.showerror("Hiba", "Ilyen nevű felhasználó már létezik!")
            return

        new_user = pd.DataFrame([{"felhasznalo": uname, "jelszo": upass, "szint": urole}])
        df = pd.concat([df, new_user], ignore_index=True)
        save_sheet_data("Felhasznalok", df)

        self.log_action(f"Új felhasználó létrehozva: {uname} ({urole})")
        messagebox.showinfo("Siker", f"'{uname}' nevű felhasználó sikeresen létrehozva!")
        self.u_name_entry.delete(0, "end")
        self.u_pass_entry.delete(0, "end")


# --- Program Indítása ---
if __name__ == "__main__":
    app = KeszletApp()
    app.mainloop()