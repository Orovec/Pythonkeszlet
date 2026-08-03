"""
Készletnyilvántartó Rendszer
Fejlesztve CustomTkinter és Pandas alapokon.
Ez a szkript egy teljes körű, egyablakos (single-window) asztali alkalmazás,
amely CSV fájlokban tárolja a készletet, kiadásokat, naplókat és felhasználókat.
"""

import datetime
import os
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import pandas as pd

# --- Globális Beállítások ---
# A CustomTkinter megjelenésének és színvilágának beállítása
ctk.set_appearance_mode("System")  # Igazodik a rendszer témájához (világos/sötét)
ctk.set_default_color_theme("blue")  # Alapértelmezett kék színvilág

# Az adatbázis mappája, ahová a CSV fájlok mentésre kerülnek
DATABASE_PATH = r"C:\Users\Orovec Árpád\Desktop\keszletproba"

# Ha a mappa még nem létezik, automatikusan létrehozzuk
if not os.path.exists(DATABASE_PATH):
    os.makedirs(DATABASE_PATH)


def get_file_path(worksheet_name):
    """Visszaadja a megadott táblázat teljes fájlelérési útvonalát a db_data mappán belül."""
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
                self.start_main_app(username, role)  # Siker esetén indítja a fő alkalmazást
                return

        messagebox.showerror("Hiba", "Hibás felhasználónév vagy jelszó!")

    # --- Fő Alkalmazás Felületének Betöltése ---
    def start_main_app(self, username, role):
        """Sikeres bejelentkezés után átállítja az ablakot a fő programfelületre (fülek, funkciók)."""
        self.username = username
        self.role = role

        self.clear_window()
        self.geometry("1100x700")
        self.title(f"Készletnyilvántartás - Bejelentkezve: {self.username} ({self.role.upper()})")

        # Fő fülek konténere (Tabview)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Fülek létrehozása szerepkör alapján
        self.tab_keszlet = self.tabview.add("Készlet & Keresés")
        self.tab_kiadas = self.tabview.add("Kiadási Lista")

        if self.role == "admin":
            self.tab_naplo = self.tabview.add("Napló")
            self.tab_users = self.tabview.add("Felhasználó kezelés")

        # Fülek tartalmának felépítése
        self.build_keszlet_tab()
        self.build_kiadas_tab()
        if self.role == "admin":
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
        """Létrehozza a raktárkészlet kezelő felületét, a keresősávot, a vezérlőgombokat és a táblázatot."""
        control_frame = ctk.CTkFrame(self.tab_keszlet)
        control_frame.pack(fill="x", padx=10, pady=10)

        # Keresési mező
        self.search_entry = ctk.CTkEntry(control_frame, placeholder_text="Keresés (Név / Lot / Dátum)...", width=250)
        self.search_entry.pack(side="left", padx=5, pady=5)

        btn_search = ctk.CTkButton(control_frame, text="Keresés / Szűrés", command=self.refresh_keszlet_view)
        btn_search.pack(side="left", padx=5, pady=5)

        btn_reset = ctk.CTkButton(control_frame, text="Összes mutatása", command=self.reset_keszlet_search,
                                  fg_color="gray")
        btn_reset.pack(side="left", padx=5, pady=5)

        # Műveleti gombok a jobb oldalon
        btn_del = ctk.CTkButton(control_frame, text="Kijelölt törlése", command=self.delete_product, fg_color="red")
        btn_del.pack(side="right", padx=5, pady=5)

        btn_ship = ctk.CTkButton(control_frame, text="Kiválasztott kiadása", command=self.open_ship_window,
                                 fg_color="darkorange")
        btn_ship.pack(side="right", padx=5, pady=5)

        btn_add = ctk.CTkButton(control_frame, text="+ Új Cikk / Gyártás", command=self.open_add_product_window,
                                fg_color="green")
        btn_add.pack(side="right", padx=5, pady=5)

        # Adattáblázat kerete
        table_frame = ctk.CTkFrame(self.tab_keszlet)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("ID", "Termék neve", "Lot szám", "Gyártás ideje", "Lejárat", "Mennyiség", "Megjegyzés")
        self.keszlet_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.keszlet_tree.heading(col, text=col)
            self.keszlet_tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.keszlet_tree.yview)
        self.keszlet_tree.configure(yscrollcommand=scrollbar.set)

        self.keszlet_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.refresh_keszlet_view()

    def refresh_keszlet_view(self):
        """Frissíti a készlet táblázat tartalmát a CSV fájlból, figyelembe véve az esetleges keresési szűrést."""
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
            self.keszlet_tree.insert("", "end", values=(
                row.get("ID", ""),
                row.get("Termék neve", ""),
                row.get("Lot szám", ""),
                row.get("Gyártás ideje", ""),
                row.get("Lejárat", ""),
                row.get("Mennyiség", ""),
                row.get("Megjegyzés", "")
            ))

    def reset_keszlet_search(self):
        """Törli a keresőmezőt és visszaállítja a készlet teljes listáját."""
        self.search_entry.delete(0, "end")
        self.refresh_keszlet_view()

    def open_add_product_window(self):
        """Megnyit egy külön ablakot új termék vagy gyártási tétel rögzítéséhez."""
        win = ctk.CTkToplevel(self)
        win.title("Új termék / Gyártás rögzítése")
        win.geometry("400x500")

        ctk.CTkLabel(win, text="Termék neve:").pack(anchor="w", padx=20, pady=(10, 0))
        e_name = ctk.CTkEntry(win, width=350)
        e_name.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Lot szám:").pack(anchor="w", padx=20, pady=(10, 0))
        e_lot = ctk.CTkEntry(win, width=350)
        e_lot.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Gyártás ideje (ÉÉÉÉ-HH-NN):").pack(anchor="w", padx=20, pady=(10, 0))
        e_gyartas = ctk.CTkEntry(win, width=350)
        e_gyartas.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        e_gyartas.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Lejárati idő (ÉÉÉÉ-HH-NN):").pack(anchor="w", padx=20, pady=(10, 0))
        e_lejarat = ctk.CTkEntry(win, width=350)
        e_lejarat.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Mennyiség:").pack(anchor="w", padx=20, pady=(10, 0))
        e_mennyiseg = ctk.CTkEntry(win, width=350)
        e_mennyiseg.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Megjegyzés (Gyártás):").pack(anchor="w", padx=20, pady=(10, 0))
        e_megj = ctk.CTkEntry(win, width=350)
        e_megj.pack(padx=20, pady=5)

        def save_new():
            """Belső függvény: Ellenőrzi a mezőket, hozzáadja az új cikket a 'Keszlet.csv'-hez, majd frissít."""
            name = e_name.get().strip()
            lot = e_lot.get().strip()
            gyartas = e_gyartas.get().strip()
            lejarat = e_lejarat.get().strip()
            menny = e_mennyiseg.get().strip()
            megj = e_megj.get().strip()

            if not name or not lot or not menny:
                messagebox.showerror("Hiba", "A név, lot szám és mennyiség kitöltése kötelező!")
                return

            df = load_sheet_data("Keszlet")
            new_id = str(len(df) + 1)

            new_row = pd.DataFrame([{
                "ID": new_id,
                "Termék neve": name,
                "Lot szám": lot,
                "Gyártás ideje": gyartas,
                "Lejárat": lejarat,
                "Mennyiség": menny,
                "Megjegyzés": megj
            }])

            df = pd.concat([df, new_row], ignore_index=True)
            save_sheet_data("Keszlet", df)

            self.log_action(f"Új termék hozzáadva: {name} (Lot: {lot})")
            self.refresh_keszlet_view()
            win.destroy()
            messagebox.showinfo("Siker", "Cikk sikeresen hozzáadva!")

        ctk.CTkButton(win, text="Mentés", command=save_new, fg_color="green", width=200).pack(pady=20)

    def delete_product(self):
        """Törli a készlet táblázatban aktuálisan kijelölt terméket."""
        selected_item = self.keszlet_tree.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Kérlek válassz ki egy elemet a törléshez!")
            return

        item_values = self.keszlet_tree.item(selected_item, "values")
        item_id = item_values[0]
        item_name = item_values[1]

        if messagebox.askyesno("Megerősítés", f"Biztosan törölni akarod a következő cikket: {item_name}?"):
            df = load_sheet_data("Keszlet")
            df = df[df["ID"].astype(str) != str(item_id)]
            save_sheet_data("Keszlet", df)

            self.log_action(f"Termék törölve: {item_name} (ID: {item_id})")
            self.refresh_keszlet_view()

    def open_ship_window(self):
        """Megnyit egy ablakot a kiválasztott termék kiadásához / raktárból való levonásához."""
        selected_item = self.keszlet_tree.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Kérlek válassz ki egy elemet a készletből a kiadáshoz!")
            return

        item_values = self.keszlet_tree.item(selected_item, "values")
        item_id, name, lot, gyartas, lejarat, max_menny, _ = item_values

        win = ctk.CTkToplevel(self)
        win.title("Termék Kiszállítása / Kiadása")
        win.geometry("400x350")

        ctk.CTkLabel(win, text=f"Kiadás alatt: {name} (Lot: {lot})", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(win, text=f"Jelenlegi készlet: {max_menny}").pack(pady=5)

        ctk.CTkLabel(win, text="Kiadandó mennyiség:").pack(anchor="w", padx=20)
        e_menny = ctk.CTkEntry(win, width=350)
        e_menny.pack(padx=20, pady=5)

        ctk.CTkLabel(win, text="Megjegyzés (Kiadás):").pack(anchor="w", padx=20)
        e_megj = ctk.CTkEntry(win, width=350)
        e_megj.pack(padx=20, pady=5)

        def confirm_shipment():
            """Belső függvény: Levonja a kiadott mennyiséget a készletből, és beírja a 'Kiadasok'-ba."""
            kiad_menny = e_menny.get().strip()
            megj = e_megj.get().strip()

            if not kiad_menny:
                messagebox.showerror("Hiba", "Add meg a kiadandó mennyiséget!")
                return

            try:
                kiad_f = float(kiad_menny)
                max_f = float(max_menny)
            except ValueError:
                messagebox.showerror("Hiba", "Érvénytelen mennyiség!")
                return

            if kiad_f > max_f:
                messagebox.showerror("Hiba", "Nincs elegendő termék készleten!")
                return

            df_keszlet = load_sheet_data("Keszlet")
            idx = df_keszlet[df_keszlet["ID"].astype(str) == str(item_id)].index

            remaining = max_f - kiad_f
            if remaining == 0:
                df_keszlet = df_keszlet.drop(idx)
            else:
                df_keszlet.loc[idx, "Mennyiség"] = str(remaining)
            save_sheet_data("Keszlet", df_keszlet)

            # Kiadási adatok mentése a naplózott kiadásokhoz
            df_kiadas = load_sheet_data("Kiadasok")
            new_kiadas = pd.DataFrame([{
                "Idopont": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Termék neve": name,
                "Lot szám": lot,
                "Mennyiség": str(kiad_f),
                "Felhasználó": self.username,
                "Megjegyzés": megj
            }])
            df_kiadas = pd.concat([df_kiadas, new_kiadas], ignore_index=True)
            save_sheet_data("Kiadasok", df_kiadas)

            self.log_action(f"Kiadás: {name} (Lot: {lot}), Mennyiség: {kiad_f}")
            self.refresh_keszlet_view()
            if hasattr(self, "refresh_kiadas_view"):
                self.refresh_kiadas_view()

            win.destroy()
            messagebox.showinfo("Siker", "Kiadás sikeresen rögzítve!")

        ctk.CTkButton(win, text="Kiadás rögzítése", command=confirm_shipment, fg_color="darkorange", width=200).pack(
            pady=20)

    # --- 2. KIADÁSI LISTA FÜL ---
    def build_kiadas_tab(self):
        """Létrehozza a kiadott tételek történetét megjelenítő fület és dátum szerinti szűrőjét."""
        control_frame = ctk.CTkFrame(self.tab_kiadas)
        control_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(control_frame, text="Dátum szűrés (ÉÉÉÉ-HH-NN):").pack(side="left", padx=5)
        self.search_kiadas_entry = ctk.CTkEntry(control_frame, placeholder_text="pl. 2026-06-06", width=150)
        self.search_kiadas_entry.pack(side="left", padx=5)

        btn_search = ctk.CTkButton(control_frame, text="Szűrés", command=self.refresh_kiadas_view)
        btn_search.pack(side="left", padx=5)

        table_frame = ctk.CTkFrame(self.tab_kiadas)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Időpont", "Termék neve", "Lot szám", "Mennyiség", "Felhasználó", "Megjegyzés")
        self.kiadas_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.kiadas_tree.heading(col, text=col)
            self.kiadas_tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.kiadas_tree.yview)
        self.kiadas_tree.configure(yscrollcommand=scrollbar.set)

        self.kiadas_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.refresh_kiadas_view()

    def refresh_kiadas_view(self):
        """Betölti és frissíti a kiadási előzményeket a 'Kiadasok.csv' fájlból."""
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
            self.kiadas_tree.insert("", "end", values=(
                row.get("Idopont", ""),
                row.get("Termék neve", ""),
                row.get("Lot szám", ""),
                row.get("Mennyiség", ""),
                row.get("Felhasználó", ""),
                row.get("Megjegyzés", "")
            ))

    # --- 3. NAPLÓ FÜL (Csak Admin) ---
    def build_naplo_tab(self):
        """Létrehozza a rendszerszintű eseményeket (bejelentkezés, törlés, kiadás) listázó fület."""
        ctk.CTkLabel(self.tab_naplo, text="Rendszerszintű Műveletnapló (Csak admin szerkesztheti)",
                     font=("Arial", 14)).pack(pady=10)

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
        """Frissíti a műveletnapló táblázatát."""
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
        """Törli és kiüríti a teljes műveletnaplót (admin funkció)."""
        if messagebox.askyesno("Megerősítés", "Biztosan törölni szeretnéd a teljes naplót?"):
            empty_df = pd.DataFrame(columns=["Idopont", "Felhasználó", "Muvelet"])
            save_sheet_data("Naplo", empty_df)
            self.refresh_naplo_view()
            messagebox.showinfo("Siker", "Napló kiürítve.")

    # --- 4. FELHASZNÁLÓ KEZELÉS FÜL (Csak Admin) ---
    def build_users_tab(self):
        """Létrehozza a felhasználókezelő fület, ahol új user vagy admin fiókok hozhatók létre."""
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
        """Ellenőrzi és elmenti az új felhasználót a 'Felhasznalok.csv' fájlba."""
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
    app.mainloop()  # Ablak életciklusának indítása (eseménykezelő hurok)