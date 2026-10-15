"""Raklapkísérő ablak – raklapokra osztás és raklaponkénti nyomtatás.

A főprogramból a RaklapKiseroWindow(parent, shipment_name, items) osztály hívható.
Az items az Admin Kiszállítás fül jobb oldali listájára már felvett tételek listája.
"""
import datetime
import html
import os
import re
import tempfile
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk


class RaklapKiseroWindow(ctk.CTkToplevel):
    """A szállítmány tételeit felosztja raklapokra és raklaplistákat nyomtat."""

    def __init__(self, parent, shipment_name, items):
        super().__init__(parent)
        self.parent = parent
        self.shipment_name = shipment_name or "Névtelen szállítmány"
        self.items = [dict(item) for item in (items or [])]
        self.pallet_count = 0
        self.quantity_entries = []
        self.saved_allocations = None
        self.print_buttons_frame = None

        self.title(f"Raklapkísérő – {self.shipment_name}")
        self.geometry("1120x680")
        self.minsize(780, 470)
        self.transient(parent)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text=f"Raklapkísérő – {self.shipment_name}",
            font=("Arial", 18, "bold")
        ).pack(padx=12, pady=(12, 4), anchor="w")
        ctk.CTkLabel(
            self,
            text="Add meg a raklapok számát, majd írd be, hogy az egyes tételekből melyik raklapra mennyi kerüljön. "
                 "Egy tétel több raklapra is szétosztható. A soronkénti összmennyiségnek egyeznie kell a szállítmányban szereplő mennyiséggel.",
            wraplength=1060, justify="left"
        ).pack(padx=12, pady=(0, 10), anchor="w")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(controls, text="Raklapok száma:").pack(side="left", padx=(0, 6))
        self.pallet_count_entry = ctk.CTkEntry(controls, width=75)
        self.pallet_count_entry.insert(0, "1")
        self.pallet_count_entry.pack(side="left", padx=4)
        ctk.CTkButton(
            controls, text="Raklapok létrehozása", command=self._create_pallet_columns
        ).pack(side="left", padx=8)

        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=12, pady=8)
        self.table_canvas = tk.Canvas(self.table_frame, highlightthickness=0)
        self.x_scroll = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.table_canvas.xview)
        self.y_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.table_canvas.yview)
        self.table_canvas.configure(xscrollcommand=self.x_scroll.set, yscrollcommand=self.y_scroll.set)
        self.x_scroll.pack(side="bottom", fill="x")
        self.y_scroll.pack(side="right", fill="y")
        self.table_canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = ctk.CTkFrame(self.table_canvas)
        self.table_canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", lambda _e: self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all")))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkButton(footer, text="Ellenőrzés és mentés", command=self._validate_and_save,
                      fg_color="green").pack(side="left", padx=(0, 8))
        ctk.CTkButton(footer, text="Bezárás", command=self.destroy,
                      fg_color="gray").pack(side="right")

        self.print_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.print_buttons_frame.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(self.print_buttons_frame, text="Mentés után itt jelennek meg a raklaponkénti nyomtatási gombok.").pack(anchor="w")

        if self.items:
            self._create_pallet_columns()
        else:
            ctk.CTkLabel(self.grid_frame, text="Ehhez a szállítmányhoz még nincs hozzáadott tétel.").grid(
                row=0, column=0, padx=12, pady=12, sticky="w")

    def _create_pallet_columns(self):
        try:
            count = int(self.pallet_count_entry.get().strip())
            if count < 1 or count > 50:
                raise ValueError
        except ValueError:
            messagebox.showerror("Hibás adat", "A raklapok száma 1 és 50 közötti egész szám legyen.", parent=self)
            return
        if not self.items:
            messagebox.showwarning("Nincs tétel", "Előbb adj hozzá tételeket a szállítmányhoz.", parent=self)
            return

        self.pallet_count = count
        self.quantity_entries = []
        self.saved_allocations = None
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        for widget in self.print_buttons_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.print_buttons_frame, text="A kiosztás módosult. Ellenőrzés és mentés után nyomtathatsz.").pack(anchor="w")

        headers = ["Beszállító", "Termék neve", "Cikkszám", "Lot szám", "Összesen"]
        for col, heading in enumerate(headers):
            ctk.CTkLabel(self.grid_frame, text=heading, font=("Arial", 11, "bold"),
                         width=115).grid(row=0, column=col, padx=3, pady=5, sticky="ew")
        for pallet_idx in range(count):
            ctk.CTkLabel(self.grid_frame, text=f"{pallet_idx + 1}. raklap",
                         font=("Arial", 11, "bold"), width=85).grid(
                row=0, column=len(headers) + pallet_idx, padx=3, pady=5, sticky="ew")

        for row_idx, item in enumerate(self.items, start=1):
            values = [item.get("Beszállító", ""), item.get("Termék neve", ""),
                      item.get("Cikkszám", ""), item.get("Lot szám", ""), item.get("Mennyiség", "0")]
            for col_idx, value in enumerate(values):
                ctk.CTkLabel(self.grid_frame, text=str(value or ""), width=115,
                             anchor="w").grid(row=row_idx, column=col_idx, padx=3, pady=4, sticky="ew")
            entries = []
            for _pallet_idx in range(count):
                entry = ctk.CTkEntry(self.grid_frame, width=85, placeholder_text="0")
                entry.insert(0, "0")
                entry.grid(row=row_idx, column=len(headers) + _pallet_idx, padx=3, pady=4)
                entries.append(entry)
            self.quantity_entries.append(entries)

        self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all"))

    def _validate_and_save(self):
        if not self.quantity_entries or not self.pallet_count:
            messagebox.showwarning("Hiányzó adatok", "Előbb hozd létre a raklapokat.", parent=self)
            return
        allocations = []
        errors = []
        for row_idx, (item, entries) in enumerate(zip(self.items, self.quantity_entries), start=1):
            try:
                requested = int(float(str(item.get("Mennyiség", "0")).replace(",", ".")))
                quantities = [int(entry.get().strip() or "0") for entry in entries]
                if requested < 0 or any(q < 0 for q in quantities):
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(f"{item.get('Termék neve', 'Tétel')} – csak nemnegatív egész mennyiség adható meg.")
                continue
            total = sum(quantities)
            if total != requested:
                errors.append(
                    f"{item.get('Termék neve', 'Tétel')} (sor {row_idx}): "
                    f"összesen {requested} db, a raklapokra kiosztva {total} db."
                )
            allocations.append({
                "termek": item.get("Termék neve", ""),
                "cikkszam": item.get("Cikkszám", ""),
                "beszallito": item.get("Beszállító", ""),
                "lot": item.get("Lot szám", ""),
                "osszesen": requested,
                "raklap_mennyisegek": quantities,
            })
        if errors:
            messagebox.showerror("Ellenőrzési hiba", "A mennyiségek nem egyeznek:\n\n" + "\n".join(errors), parent=self)
            return

        self.saved_allocations = allocations
        self.parent.raklapkisero_adatok = {
            "szallitmany": self.shipment_name,
            "raklapok_szama": self.pallet_count,
            "tetel_kiosztas": allocations,
        }
        for widget in self.print_buttons_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.print_buttons_frame, text="Nyomtasd ki a kívánt raklap listáját:",
                     font=("Arial", 12, "bold")).pack(side="left", padx=(0, 8))
        for pallet_idx in range(self.pallet_count):
            ctk.CTkButton(
                self.print_buttons_frame,
                text=f"{pallet_idx + 1}. raklap nyomtatása",
                command=lambda idx=pallet_idx: self._print_pallet(idx),
                width=145
            ).pack(side="left", padx=3, pady=4)
        messagebox.showinfo("Mentve", "A raklapokra osztás ellenőrizve és elmentve erre a munkamenetre. Most raklaponként nyomtathatsz.", parent=self)

    def _print_pallet(self, pallet_idx):
        if self.saved_allocations is None:
            messagebox.showwarning("Nincs mentett kiosztás", "Előbb kattints az Ellenőrzés és mentés gombra.", parent=self)
            return
        pallet_name = f"{pallet_idx + 1}. raklap"
        rows = []
        for item in self.saved_allocations:
            quantities = item.get("raklap_mennyisegek", [])
            qty = quantities[pallet_idx] if pallet_idx < len(quantities) else 0
            if qty > 0:
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(item.get('termek', '') or ''))}</td>"
                    f"<td>{html.escape(str(item.get('lot', '') or ''))}</td>"
                    f"<td>{html.escape(str(item.get('cikkszam', '') or ''))}</td>"
                    f"<td class=\"qty\">{qty}</td>"
                    "</tr>"
                )
        if not rows:
            messagebox.showwarning("Üres raklap", f"A(z) {pallet_name} nem tartalmaz kiosztott tételt.", parent=self)
            return

        safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', self.shipment_name).strip('_') or 'szallitmany'
        date_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        html_content = f"""<!doctype html>
<html lang="hu"><head><meta charset="utf-8"><title>{html.escape(self.shipment_name)} - {pallet_name}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
h1 {{ font-size: 22px; margin-bottom: 6px; }}
p {{ margin: 5px 0 18px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #333; padding: 9px; text-align: left; }}
th {{ background: #eee; }} .qty {{ text-align: right; width: 90px; }}
@media print {{ button {{ display: none; }} body {{ margin: 10mm; }} }}
</style></head><body>
<h1>Raklapkísérő – {html.escape(self.shipment_name)}</h1>
<p><strong>{html.escape(pallet_name)}</strong> &nbsp; | &nbsp; Nyomtatva: {date_text}</p>
<table><thead><tr><th>Termék neve</th><th>Lot</th><th>Cikkszám</th><th>Mennyiség</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p style="margin-top:28px">Összekészítette: ____________________ &nbsp;&nbsp; Ellenőrizte: ____________________</p>
<button onclick="window.print()">Nyomtatás</button>
<script>window.onload = function() {{ window.print(); }};</script>
</body></html>"""
        out_dir = os.path.join(os.getcwd(), "raklapkisero")
        os.makedirs(out_dir, exist_ok=True)
        file_path = os.path.join(out_dir, f"{safe_name}_{pallet_idx + 1}_raklap.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        temp_path = os.path.join(tempfile.gettempdir(), f"raklapkisero_{safe_name}_{pallet_idx + 1}.html")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        webbrowser.open("file:///" + temp_path.replace(os.sep, "/"))
        messagebox.showinfo("Raklaplista", f"A(z) {pallet_name} listája megnyílt nyomtatáshoz.\nMentett fájl:\n{file_path}", parent=self)
