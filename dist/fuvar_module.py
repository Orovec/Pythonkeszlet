import datetime
import os
import re
import sqlite3
import json
import urllib.parse
import urllib.request
import webbrowser
import tempfile

from tkinter import messagebox, ttk
import customtkinter as ctk

# ============================================================
# TÉRKÉP MODUL
# ============================================================

try:
    import tkintermapview

    HAS_MAP = True
except ImportError:
    HAS_MAP = False


class FuvarManager:
    """
    Fuvar szervezés és útvonaltervezés.

    A térkép:
    - OpenStreetMap alapú
    - közvetlenül a Tkinter ablakban jelenik meg
    - mindig Szegedről indul
    - a megállókat számozott jelölőkkel mutatja
    - megpróbálja az útvonalat is kirajzolni
    """

    # ========================================================
    # ALAPBEÁLLÍTÁSOK
    # ========================================================

    START_CITY = "Szeged, Hungary"

    # Szeged hozzávetőleges koordinátája
    START_LAT = 46.2530
    START_LON = 20.1414

    def __init__(self, app_instance):
        self.app = app_instance

        # Ideiglenes megállók
        self.temp_fuvar_stops = []

        # Térképes objektumok
        self.map_widget = None
        self.map_markers = []
        self.map_route = None

        # Geokódolt címek gyorsítótára
        self.geocode_cache = {}

        # Adatbázis
        self.init_database()

    # ========================================================
    # ADATBÁZIS
    # ========================================================

    def init_database(self):
        """Létrehozza a fuvar partnerek táblát."""

        try:
            self.db_path = getattr(
                self.app,
                "db_path",
                "raktár.db"
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fuvar_partnerek (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nev TEXT UNIQUE NOT NULL,
                    cim TEXT,
                    elerhetoseg TEXT
                )
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            print(
                f"Adatbázis init hiba "
                f"(fuvar_partnerek): {e}"
            )

    def get_saved_partners(self):
        """Lekérdezi az elmentett partnereket."""

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT nev, cim, elerhetoseg
                FROM fuvar_partnerek
                ORDER BY nev ASC
            """)

            rows = cursor.fetchall()

            conn.close()

            return rows

        except Exception as e:
            print(
                f"Partner lekérdezési hiba: {e}"
            )

            return []

    def save_partner_to_db(
        self,
        nev,
        cim,
        elerh
    ):
        """Elmenti vagy frissíti a partnert."""

        if not nev:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO fuvar_partnerek
                (nev, cim, elerhetoseg)
                VALUES (?, ?, ?)

                ON CONFLICT(nev) DO UPDATE SET
                    cim = excluded.cim,
                    elerhetoseg = excluded.elerhetoseg
            """, (
                nev,
                cim,
                elerh
            ))

            conn.commit()
            conn.close()

            self.update_partner_dropdown()

        except Exception as e:
            print(
                f"Partner mentési hiba: {e}"
            )

    def update_partner_dropdown(self):
        """Frissíti a partner legördülő listát."""

        if hasattr(
            self,
            "fuvar_partner_cb"
        ):
            partners = self.get_saved_partners()

            partner_names = [
                p[0]
                for p in partners
            ]

            self.fuvar_partner_cb.configure(
                values=partner_names
            )

    def on_partner_selected(self, choice):
        """Partner kiválasztásakor kitölti az adatokat."""

        partners = self.get_saved_partners()

        for partner in partners:

            if partner[0] == choice:

                self.fuvar_cim_entry.delete(
                    0,
                    "end"
                )

                if partner[1]:
                    self.fuvar_cim_entry.insert(
                        0,
                        partner[1]
                    )

                self.fuvar_elerhetoseg_entry.delete(
                    0,
                    "end"
                )

                if partner[2]:
                    self.fuvar_elerhetoseg_entry.insert(
                        0,
                        partner[2]
                    )

                break

    # ========================================================
    # FUVAR FÜL FELÉPÍTÉSE
    # ========================================================

    def build_fuvar_szervezes_tab(
        self,
        parent_tab
    ):
        """Felépíti a Fuvar szervezés fület."""

        # ----------------------------------------------------
        # CÍM
        # ----------------------------------------------------

        ctk.CTkLabel(
            parent_tab,
            text=(
                "Komplex Fuvar Szervezés "
                "& Útvonaltervezés"
            ),
            font=("Arial", 16, "bold")
        ).pack(
            pady=5
        )

        # ----------------------------------------------------
        # FELSŐ BEÁLLÍTÁSOK
        # ----------------------------------------------------

        top_conf = ctk.CTkFrame(
            parent_tab
        )

        top_conf.pack(
            fill="x",
            padx=10,
            pady=5
        )

        ctk.CTkLabel(
            top_conf,
            text="Fuvar / Kanyar Neve:"
        ).pack(
            side="left",
            padx=5
        )

        self.fuvar_nev_entry = ctk.CTkEntry(
            top_conf,
            width=160
        )

        self.fuvar_nev_entry.insert(
            0,
            (
                f"FUVAR-"
                f"{datetime.date.today().strftime('%Y%m%d')}"
                f"-1"
            )
        )

        self.fuvar_nev_entry.pack(
            side="left",
            padx=5
        )

        ctk.CTkLabel(
            top_conf,
            text="Indulási Nap:"
        ).pack(
            side="left",
            padx=(15, 5)
        )

        self.fuvar_datum_entry = ctk.CTkEntry(
            top_conf,
            width=100
        )

        self.fuvar_datum_entry.insert(
            0,
            datetime.date.today().strftime(
                "%Y-%m-%d"
            )
        )

        self.fuvar_datum_entry.pack(
            side="left",
            padx=5
        )

        # ----------------------------------------------------
        # FŐ ELRENDEZÉS
        # ----------------------------------------------------

        main_split = ctk.CTkFrame(
            parent_tab,
            fg_color="transparent"
        )

        main_split.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        # ====================================================
        # BAL OLDAL
        # ====================================================

        left_box = ctk.CTkFrame(
            main_split
        )

        left_box.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 5)
        )

        ctk.CTkLabel(
            left_box,
            text=(
                "1. Megállók, Címek "
                "és Szállítandó Tételek"
            ),
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=5
        )

        # ----------------------------------------------------
        # MEGÁLLÓ BEVITEL
        # ----------------------------------------------------

        stop_input_frame = ctk.CTkFrame(
            left_box
        )

        stop_input_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        # CÍM

        r1 = ctk.CTkFrame(
            stop_input_frame,
            fg_color="transparent"
        )

        r1.pack(
            fill="x",
            pady=2
        )

        ctk.CTkLabel(
            r1,
            text="Cím / Úticél:",
            width=90
        ).pack(
            side="left",
            padx=2
        )

        self.fuvar_cim_entry = ctk.CTkEntry(
            r1,
            placeholder_text=(
                "pl. Budapest, Fő u. 1."
            ),
            width=280
        )

        self.fuvar_cim_entry.pack(
            side="left",
            padx=2
        )

        # PARTNER

        r2 = ctk.CTkFrame(
            stop_input_frame,
            fg_color="transparent"
        )

        r2.pack(
            fill="x",
            pady=2
        )

        ctk.CTkLabel(
            r2,
            text="Partner Név:",
            width=90
        ).pack(
            side="left",
            padx=2
        )

        saved_names = [
            p[0]
            for p in self.get_saved_partners()
        ]

        self.fuvar_partner_cb = ctk.CTkComboBox(
            r2,
            values=saved_names,
            command=self.on_partner_selected,
            width=150
        )

        self.fuvar_partner_cb.pack(
            side="left",
            padx=2
        )

        self.fuvar_partner_cb.set("")

        ctk.CTkLabel(
            r2,
            text="Elérhetőség:"
        ).pack(
            side="left",
            padx=(5, 2)
        )

        self.fuvar_elerhetoseg_entry = ctk.CTkEntry(
            r2,
            placeholder_text="Telefonszám",
            width=120
        )

        self.fuvar_elerhetoseg_entry.pack(
            side="left",
            padx=2
        )

        # TÉTELEK

        r3 = ctk.CTkFrame(
            stop_input_frame,
            fg_color="transparent"
        )

        r3.pack(
            fill="x",
            pady=2
        )

        ctk.CTkLabel(
            r3,
            text="Mit visz / hoz:",
            width=90
        ).pack(
            side="left",
            padx=2
        )

        self.fuvar_tetelek_entry = ctk.CTkEntry(
            r3,
            placeholder_text="pl. 2x raklap áru",
            width=280
        )

        self.fuvar_tetelek_entry.pack(
            side="left",
            padx=2
        )

        # MEGJEGYZÉS

        r4 = ctk.CTkFrame(
            stop_input_frame,
            fg_color="transparent"
        )

        r4.pack(
            fill="x",
            pady=2
        )

        ctk.CTkLabel(
            r4,
            text="Megjegyzés:",
            width=90
        ).pack(
            side="left",
            padx=2
        )

        self.fuvar_megj_entry = ctk.CTkEntry(
            r4,
            placeholder_text=(
                "Sofőrnek szóló infó"
            ),
            width=280
        )

        self.fuvar_megj_entry.pack(
            side="left",
            padx=2
        )

        # HOZZÁADÁS

        btn_add_stop = ctk.CTkButton(
            stop_input_frame,
            text=(
                "+ Megálló Hozzáadása "
                "& Partner Mentése"
            ),
            command=self.add_fuvar_stop,
            fg_color="green"
        )

        btn_add_stop.pack(
            fill="x",
            padx=5,
            pady=5
        )

        # ====================================================
        # MEGÁLLÓK LISTÁJA
        # ====================================================

        list_frame = ctk.CTkFrame(
            left_box
        )

        list_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        stops_cols = (
            "Sorrend",
            "Cím",
            "Partner",
            "Elérhetőség",
            "Tételek (Visz/Hoz)",
            "Megjegyzés"
        )

        self.fuvar_tree = ttk.Treeview(
            list_frame,
            columns=stops_cols,
            show="headings",
            height=8
        )

        col_w = {
            "Sorrend": 60,
            "Cím": 150,
            "Partner": 100,
            "Elérhetőség": 90,
            "Tételek (Visz/Hoz)": 150,
            "Megjegyzés": 120
        }

        for col in stops_cols:

            self.fuvar_tree.heading(
                col,
                text=col
            )

            self.fuvar_tree.column(
                col,
                width=col_w.get(
                    col,
                    100
                )
            )

        stops_scroll = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.fuvar_tree.yview
        )

        self.fuvar_tree.configure(
            yscrollcommand=stops_scroll.set
        )

        self.fuvar_tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        stops_scroll.pack(
            side="right",
            fill="y"
        )

        # ====================================================
        # SORREND GOMBOK
        # ====================================================

        order_btn_frame = ctk.CTkFrame(
            left_box,
            fg_color="transparent"
        )

        order_btn_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        ctk.CTkButton(
            order_btn_frame,
            text="⬆ Feljebb",
            command=lambda:
                self.move_fuvar_stop(-1),
            width=90,
            fg_color="darkorange"
        ).pack(
            side="left",
            padx=2
        )

        ctk.CTkButton(
            order_btn_frame,
            text="⬇ Lejjebb",
            command=lambda:
                self.move_fuvar_stop(1),
            width=90,
            fg_color="darkorange"
        ).pack(
            side="left",
            padx=2
        )

        ctk.CTkButton(
            order_btn_frame,
            text="Kijelölt törlése",
            command=self.delete_fuvar_stop,
            width=110,
            fg_color="red"
        ).pack(
            side="left",
            padx=10
        )

        ctk.CTkButton(
            order_btn_frame,
            text="Mindent töröl",
            command=self.clear_fuvar_stops,
            width=100,
            fg_color="gray"
        ).pack(
            side="right",
            padx=2
        )

        # ====================================================
        # JOBB OLDAL – TÉRKÉP
        # ====================================================

        right_box = ctk.CTkFrame(
            main_split
        )

        right_box.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(5, 0)
        )

        ctk.CTkLabel(
            right_box,
            text=(
                "2. Útvonal térkép "
                "& Sofőr összegző"
            ),
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=5
        )

        # ----------------------------------------------------
        # TÉRKÉP
        # ----------------------------------------------------

        map_container = ctk.CTkFrame(
            right_box
        )

        map_container.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        if HAS_MAP:

            self.map_widget = (
                tkintermapview.TkinterMapView(
                    map_container,
                    corner_radius=0
                )
            )

            self.map_widget.pack(
                fill="both",
                expand=True
            )

            # FONTOS:
            # A térkép mindig Szegedre áll be.

            self.map_widget.set_position(
                self.START_LAT,
                self.START_LON
            )

            self.map_widget.set_zoom(
                11
            )

            # Szeged indulási pont
            self.map_widget.set_marker(
                self.START_LAT,
                self.START_LON,
                text="🚚 INDULÁS - SZEGED"
            )

        else:

            fallback_lbl = ctk.CTkLabel(
                map_container,
                text=(
                    "A térkép modul nincs telepítve.\n\n"
                    "Nyiss egy Parancssort és futtasd:\n\n"
                    "pip install tkintermapview"
                ),
                text_color="orange"
            )

            fallback_lbl.pack(
                expand=True
            )

        # ----------------------------------------------------
        # SOFŐR ELŐNÉZET
        # ----------------------------------------------------

        ctk.CTkLabel(
            right_box,
            text=(
                "Sofőr utasítás / "
                "Összegző előnézet:"
            ),
            font=("Arial", 11, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=(5, 0)
        )

        self.sofor_text_box = ctk.CTkTextbox(
            right_box,
            font=("Courier", 11),
            height=130
        )

        self.sofor_text_box.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        # ----------------------------------------------------
        # NYOMTATÁS / MENTÉS
        # ----------------------------------------------------

        btn_print_sofor = ctk.CTkButton(
            right_box,
            text=(
                "🖨️ Sofőr Utasítás "
                "Nyomtatása / Mentése"
            ),
            command=self.print_sofor_summary,
            fg_color="green",
            height=40
        )

        btn_print_sofor.pack(
            fill="x",
            padx=10,
            pady=5
        )

        # Kezdő nézet
        self.refresh_fuvar_view()

    # ========================================================
    # ÚJ MEGÁLLÓ
    # ========================================================

    def add_fuvar_stop(self):
        """Új megállót ad a fuvarhoz."""

        cim = self.fuvar_cim_entry.get().strip()
        partner = self.fuvar_partner_cb.get().strip()
        elerh = (
            self.fuvar_elerhetoseg_entry
            .get()
            .strip()
        )
        tetelek = (
            self.fuvar_tetelek_entry
            .get()
            .strip()
        )
        megj = (
            self.fuvar_megj_entry
            .get()
            .strip()
        )

        if not cim or not tetelek:

            messagebox.showwarning(
                "Figyelmeztetés",
                (
                    "A Cím és a Tételek "
                    "megadása kötelező!"
                )
            )

            return

        # Partner mentése
        if partner:

            self.save_partner_to_db(
                partner,
                cim,
                elerh
            )

        sorrend = (
            len(self.temp_fuvar_stops) + 1
        )

        self.temp_fuvar_stops.append({

            "Sorrend": str(sorrend),

            "Cím": cim,

            "Partner": partner,

            "Elérhetőség": elerh,

            "Tételek (Visz/Hoz)": tetelek,

            "Megjegyzés": megj

        })

        # Mezők törlése

        self.fuvar_cim_entry.delete(
            0,
            "end"
        )

        self.fuvar_partner_cb.set("")

        self.fuvar_elerhetoseg_entry.delete(
            0,
            "end"
        )

        self.fuvar_tetelek_entry.delete(
            0,
            "end"
        )

        self.fuvar_megj_entry.delete(
            0,
            "end"
        )

        # Nézet frissítése
        self.refresh_fuvar_view()

    # ========================================================
    # NÉZET FRISSÍTÉSE
    # ========================================================

    def refresh_fuvar_view(self):
        """
        Frissíti:
        - a táblázatot
        - a sofőr összegzőt
        - a térképet
        """

        if not hasattr(
            self,
            "fuvar_tree"
        ):
            return

        # ----------------------------------------------------
        # TÁBLÁZAT TÖRLÉSE
        # ----------------------------------------------------

        for row in self.fuvar_tree.get_children():

            self.fuvar_tree.delete(
                row
            )

        # ----------------------------------------------------
        # SOFŐR SZÖVEG
        # ----------------------------------------------------

        sofor_preview = ""

        fuvar_nev = (
            self.fuvar_nev_entry
            .get()
            .strip()
        )

        fuvar_datum = (
            self.fuvar_datum_entry
            .get()
            .strip()
        )

        sofor_preview += (
            "========================================\n"
        )

        sofor_preview += (
            "        SOFŐR ÚTVONAL ÉS FUVAR LAP      \n"
        )

        sofor_preview += (
            "========================================\n"
        )

        sofor_preview += (
            f"Fuvar Kanyar: {fuvar_nev}\n"
        )

        sofor_preview += (
            f"Indulási Nap: {fuvar_datum}\n"
        )

        sofor_preview += (
            f"Indulás:      {self.START_CITY}\n"
        )

        sofor_preview += (
            f"Rögzítette:   "
            f"{getattr(self.app, 'username', 'Admin')}\n"
        )

        sofor_preview += (
            "----------------------------------------\n\n"
        )

        # ----------------------------------------------------
        # CÍMEK
        # ----------------------------------------------------

        cimek = []

        for idx, stop in enumerate(
            self.temp_fuvar_stops,
            1
        ):

            stop["Sorrend"] = str(idx)

            # Táblázat

            self.fuvar_tree.insert(
                "",
                "end",
                values=(

                    stop["Sorrend"],

                    stop["Cím"],

                    stop["Partner"],

                    stop["Elérhetőség"],

                    stop["Tételek (Visz/Hoz)"],

                    stop["Megjegyzés"]

                )
            )

            if stop["Cím"]:

                cimek.append(
                    stop["Cím"]
                )

            # Sofőr szöveg

            sofor_preview += (
                f"Megálló #{idx}: "
                f"{stop['Cím']}\n"
            )

            if stop["Partner"]:

                sofor_preview += (
                    f" - Partner:     "
                    f"{stop['Partner']} "
                    f"({stop['Elérhetőség']})\n"
                )

            sofor_preview += (
                f" - Fuvar tétel: "
                f"{stop['Tételek (Visz/Hoz)']}\n"
            )

            if stop["Megjegyzés"]:

                sofor_preview += (
                    f" - Megjegyzés:  "
                    f"{stop['Megjegyzés']}\n"
                )

            sofor_preview += (
                "----------------------------------------\n"
            )

        # ----------------------------------------------------
        # SOFŐR TEXTBOX
        # ----------------------------------------------------

        if hasattr(
            self,
            "sofor_text_box"
        ):

            self.sofor_text_box.delete(
                "1.0",
                "end"
            )

            self.sofor_text_box.insert(
                "1.0",
                sofor_preview
            )

        # ----------------------------------------------------
        # TÉRKÉP
        # ----------------------------------------------------

        self.update_embedded_map(
            cimek
        )

    # ========================================================
    # GEOKÓDOLÁS
    # ========================================================

    def geocode_address(self, address):
        """
        Cím -> GPS koordináta.

        Az OpenStreetMap Nominatim szolgáltatását használja.
        """

        if not address:
            return None

        # Cache
        if address in self.geocode_cache:

            return self.geocode_cache[
                address
            ]

        try:

            encoded_address = (
                urllib.parse.quote(
                    address
                )
            )

            url = (
                "https://nominatim.openstreetmap.org/"
                "search?"
                f"q={encoded_address}"
                "&format=json"
                "&limit=1"
                "&countrycodes=hu"
            )

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent":
                        "FuvarManager/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=10
            ) as response:

                data = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

            if not data:

                print(
                    f"Nem található cím: {address}"
                )

                return None

            lat = float(
                data[0]["lat"]
            )

            lon = float(
                data[0]["lon"]
            )

            result = (
                lat,
                lon
            )

            self.geocode_cache[
                address
            ] = result

            return result

        except Exception as e:

            print(
                f"Geokódolási hiba "
                f"({address}): {e}"
            )

            return None

    # ========================================================
    # ÚTVONAL LEKÉRÉSE
    # ========================================================

    def get_road_route(
        self,
        coordinates
    ):
        """
        OSRM segítségével megpróbál valódi
        közúti útvonalat kérni.

        coordinates:
            [(lat, lon), (lat, lon), ...]
        """

        if len(coordinates) < 2:
            return None

        try:

            # OSRM lon,lat formátumot használ

            coord_string = ";".join(
                f"{lon},{lat}"
                for lat, lon in coordinates
            )

            url = (
                "https://router.project-osrm.org/"
                f"route/v1/driving/{coord_string}"
                "?overview=full"
                "&geometries=geojson"
            )

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent":
                        "FuvarManager/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=20
            ) as response:

                data = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

            if data.get("code") != "Ok":

                print(
                    "OSRM útvonal hiba:",
                    data.get("code")
                )

                return None

            geometry = (
                data["routes"][0]["geometry"]
            )

            route_coordinates = []

            for lon, lat in geometry["coordinates"]:

                route_coordinates.append(
                    (lat, lon)
                )

            return route_coordinates

        except Exception as e:

            print(
                f"Útvonaltervezési hiba: {e}"
            )

            return None

    # ========================================================
    # TÉRKÉP FRISSÍTÉSE
    # ========================================================

    def update_embedded_map(
        self,
        cimek
    ):
        """
        Frissíti a beépített térképet.

        FONTOS:
        A térkép mindig Szegedről indul.
        """

        if not HAS_MAP:

            return

        if self.map_widget is None:

            return

        # ----------------------------------------------------
        # RÉGI MARKEREK TÖRLÉSE
        # ----------------------------------------------------

        for marker in self.map_markers:

            try:
                marker.delete()

            except Exception:
                pass

        self.map_markers = []

        # Régi útvonal törlése

        if self.map_route is not None:

            try:
                self.map_route.delete()

            except Exception:
                pass

            self.map_route = None

        # ----------------------------------------------------
        # SZEGED INDULÁSI PONT
        # ----------------------------------------------------

        start_marker = (
            self.map_widget.set_marker(
                self.START_LAT,
                self.START_LON,
                text="🚚 INDULÁS - SZEGED"
            )
        )

        self.map_markers.append(
            start_marker
        )

        # ----------------------------------------------------
        # HA NINCS MEGÁLLÓ
        # ----------------------------------------------------

        if not cimek:

            self.map_widget.set_position(
                self.START_LAT,
                self.START_LON
            )

            self.map_widget.set_zoom(
                11
            )

            return

        # ----------------------------------------------------
        # CÍMEK GEOKÓDOLÁSA
        # ----------------------------------------------------

        coordinates = [

            (
                self.START_LAT,
                self.START_LON
            )

        ]

        # Először töröljük a korábbi geokódolási
        # hibaüzeneteket a konzolból nem szükséges.

        for idx, address in enumerate(
            cimek,
            1
        ):

            print(
                f"Geokódolás "
                f"{idx}/{len(cimek)}: "
                f"{address}"
            )

            result = (
                self.geocode_address(
                    address
                )
            )

            if result is None:

                print(
                    f"⚠ Nem sikerült megtalálni: "
                    f"{address}"
                )

                continue

            lat, lon = result

            coordinates.append(
                (lat, lon)
            )

            # ------------------------------------------------
            # MARKER
            # ------------------------------------------------

            marker = (
                self.map_widget.set_marker(
                    lat,
                    lon,
                    text=(
                        f"#{idx} "
                        f"{address}"
                    )
                )
            )

            self.map_markers.append(
                marker
            )

        # ----------------------------------------------------
        # NINCS TALÁLT CÍM
        # ----------------------------------------------------

        if len(coordinates) == 1:

            self.map_widget.set_position(
                self.START_LAT,
                self.START_LON
            )

            self.map_widget.set_zoom(
                11
            )

            return

        # ----------------------------------------------------
        # ÚTVONAL
        # ----------------------------------------------------

        route = self.get_road_route(
            coordinates
        )

        if route:

            try:

                self.map_route = (
                    self.map_widget.set_path(
                        route,
                        color="#1565C0",
                        width=5
                    )
                )

            except Exception as e:

                print(
                    f"Útvonal rajzolási hiba: "
                    f"{e}"
                )

        else:

            # Ha az OSRM nem érhető el,
            # legalább egyenes vonallal
            # összekötjük a pontokat.

            try:

                self.map_route = (
                    self.map_widget.set_path(
                        coordinates,
                        color="#888888",
                        width=3
                    )
                )

            except Exception as e:

                print(
                    f"Vonal rajzolási hiba: "
                    f"{e}"
                )

        # ----------------------------------------------------
        # TÉRKÉP RÁNAGYÍTÁSA AZ ÚTVONALRA
        # ----------------------------------------------------

        try:

            lats = [
                point[0]
                for point in coordinates
            ]

            lons = [
                point[1]
                for point in coordinates
            ]

            min_lat = min(lats)
            max_lat = max(lats)

            min_lon = min(lons)
            max_lon = max(lons)

            center_lat = (
                min_lat + max_lat
            ) / 2

            center_lon = (
                min_lon + max_lon
            ) / 2

            self.map_widget.set_position(
                center_lat,
                center_lon
            )

            # Nagyjából megfelelő zoom
            # távolságtól függően.

            lat_diff = (
                max_lat - min_lat
            )

            lon_diff = (
                max_lon - min_lon
            )

            max_diff = max(
                lat_diff,
                lon_diff
            )

            if max_diff > 5:
                zoom = 6

            elif max_diff > 2:
                zoom = 7

            elif max_diff > 1:
                zoom = 8

            elif max_diff > 0.5:
                zoom = 9

            elif max_diff > 0.2:
                zoom = 10

            elif max_diff > 0.1:
                zoom = 11

            else:
                zoom = 12

            self.map_widget.set_zoom(
                zoom
            )

        except Exception as e:

            print(
                f"Térkép pozicionálási hiba: "
                f"{e}"
            )

    # ========================================================
    # MEGÁLLÓ FELJEBB / LEJJEBB
    # ========================================================

    def move_fuvar_stop(
        self,
        direction
    ):
        """Megálló áthelyezése."""

        selected = (
            self.fuvar_tree.selection()
        )

        if not selected:

            messagebox.showwarning(
                "Figyelmeztetés",
                (
                    "Válassz ki egy megállót "
                    "a módosításhoz!"
                )
            )

            return

        idx = self.fuvar_tree.index(
            selected[0]
        )

        new_idx = idx + direction

        if (
            0
            <= new_idx
            < len(self.temp_fuvar_stops)
        ):

            item = (
                self.temp_fuvar_stops.pop(
                    idx
                )
            )

            self.temp_fuvar_stops.insert(
                new_idx,
                item
            )

            self.refresh_fuvar_view()

            children = (
                self.fuvar_tree.get_children()
            )

            if (
                children
                and new_idx < len(children)
            ):

                self.fuvar_tree.selection_set(
                    children[new_idx]
                )

    # ========================================================
    # MEGÁLLÓ TÖRLÉSE
    # ========================================================

    def delete_fuvar_stop(self):
        """Kijelölt megálló törlése."""

        selected = (
            self.fuvar_tree.selection()
        )

        if not selected:

            messagebox.showwarning(
                "Figyelmeztetés",
                (
                    "Válassz ki egy törlendő "
                    "megállót!"
                )
            )

            return

        idx = self.fuvar_tree.index(
            selected[0]
        )

        if (
            0
            <= idx
            < len(self.temp_fuvar_stops)
        ):

            self.temp_fuvar_stops.pop(
                idx
            )

        self.refresh_fuvar_view()

    # ========================================================
    # ÖSSZES MEGÁLLÓ TÖRLÉSE
    # ========================================================

    def clear_fuvar_stops(self):
        """Az összes megálló törlése."""

        answer = messagebox.askyesno(
            "Törlés",
            (
                "Biztosan törlöd az összes "
                "megállót ebből a fuvarból?"
            )
        )

        if answer:

            self.temp_fuvar_stops = []

            self.refresh_fuvar_view()

    # ========================================================
    # SOFŐR ÖSSZEGZŐ MENTÉSE
    # ========================================================

    def print_sofor_summary(self):
        """
        Elmenti a sofőr összegzőt HTML fájlba,
        majd megnyitja a böngészőben.
        """

        if not self.temp_fuvar_stops:

            messagebox.showwarning(
                "Figyelmeztetés",
                (
                    "Nincs mit kinyomtatni, "
                    "a fuvar üres!"
                )
            )

            return

        text_content = (
            self.sofor_text_box
            .get(
                "1.0",
                "end"
            )
        )

        fuvar_nev = (
            self.fuvar_nev_entry
            .get()
            .strip()
        )

        try:

            # ------------------------------------------------
            # MENTÉSI KÖNYVTÁR
            # ------------------------------------------------

            save_dir = os.path.join(
                os.getcwd(),
                "sofor_lapok"
            )

            os.makedirs(
                save_dir,
                exist_ok=True
            )

            # ------------------------------------------------
            # BIZTONSÁGOS FÁJLNÉV
            # ------------------------------------------------

            safe_name = re.sub(
                r'[\\/*?:"<>|]',
                "",
                fuvar_nev
            )

            if not safe_name:

                safe_name = "fuvar"

            file_path = os.path.join(
                save_dir,
                (
                    f"{datetime.date.today().strftime('%Y-%m-%d')}"
                    f"_{safe_name}.html"
                )
            )

            # ------------------------------------------------
            # HTML
            # ------------------------------------------------

            html_output = f"""
<!DOCTYPE html>
<html lang="hu">

<head>

<meta charset="UTF-8">

<title>
{fuvar_nev}
</title>

<style>

body {{
    font-family: "Courier New", monospace;
    white-space: pre-wrap;
    padding: 30px;
    font-size: 14px;
}}

h1 {{
    font-family: Arial, sans-serif;
}}

</style>

</head>

<body>

{self.escape_html(text_content)}

</body>

</html>
"""

            # ------------------------------------------------
            # MENTÉS
            # ------------------------------------------------

            with open(
                file_path,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    html_output
                )

            # ------------------------------------------------
            # IDEIGLENES FÁJL
            # ------------------------------------------------

            temp_path = os.path.join(
                os.environ.get(
                    "TEMP",
                    tempfile.gettempdir()
                    if "tempfile" in globals()
                    else os.getcwd()
                ),
                "sofor_lap.html"
            )

            with open(
                temp_path,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    html_output
                )

            # ------------------------------------------------
            # BÖNGÉSZŐ
            # ------------------------------------------------

            webbrowser.open(
                "file:///"
                + temp_path.replace(
                    "\\",
                    "/"
                )
            )

            # ------------------------------------------------
            # NAPLÓ
            # ------------------------------------------------

            if hasattr(
                self.app,
                "log_action"
            ):

                self.app.log_action(
                    (
                        "Sofőr utasítás "
                        "kinyomtatva / mentve: "
                        f"{fuvar_nev}"
                    )
                )

            messagebox.showinfo(
                "Siker",
                (
                    "A sofőr utasítás mentve ide:\n\n"
                    f"{file_path}\n\n"
                    "A nyomtatási előnézet "
                    "megnyitva a böngészőben."
                )
            )

        except Exception as e:

            messagebox.showerror(
                "Hiba",
                (
                    "Nem sikerült elmenteni "
                    f"a sofőr lapot:\n\n{e}"
                )
            )

    # ========================================================
    # HTML ESCAPE
    # ========================================================

    @staticmethod
    def escape_html(text):
        """HTML speciális karakterek kezelése."""

        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
