import os
import sys
import subprocess
import urllib.request
import json
import tkinter as tk
from tkinter import messagebox

# --- BEÁLLÍTÁSOK ---
# Itt kell megadni a távoli szerver vagy GitHub Raw linkeket, ahová majd feltöltöd a frissítéseket
VERSION_URL = "https://raw.githubusercontent.com/FELHASZNALONEV/REPOSITORY/main/version.json"
UPDATE_FILE_URL = "https://raw.githubusercontent.com/FELHASZNALONEV/REPOSITORY/main/main.py"

LOCAL_VERSION_FILE = "version.txt"
MAIN_APP_FILE = "main.py"


def resource_path(relative_path):
    """Biztosítja a helyes elérési utat, ha PyInstallerrel csomagoljuk."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath("elsoverz")
    return os.path.join(base_path, relative_path)


def check_for_updates():
    """Ellenőrzi, hogy van-e újabb verzió a szerveren."""
    try:
        # Helyi verzió olvasása
        local_version = "1.0.0"
        if os.path.exists(LOCAL_VERSION_FILE):
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                local_version = f.read().strip()

        # Távoli verzió lekérdezése
        req = urllib.request.Request(VERSION_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            remote_version = data.get("version")
            changelog = data.get("changelog", "Frissítés érhető el.")

        # Verziók összehasonlítása egyszerű sztringként vagy verziószámként
        if remote_version and remote_version != local_version:
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Frissítés elérhető",
                                   "Új verzió érhető el ({remote_version}).\nÚjdonságok: {changelog}\n\nSzeretnéd letölteni és frissíteni most?"):
                download_update(remote_version)
            root.destroy()

    except Exception as e:
        # Ha nincs internet vagy hiba van, némán továbbengedjük, hogy offline is működjön a meglévő kóddal
        print(comm=f"Nem sikerült ellenőrizni a frissítést: {e}")


def download_update(new_version):
    """Letölti az új main.py-t és frissíti a verziószámot."""
    try:
        root = tk.Tk()
        root.withdraw()

        # Új main.py letöltése
        req = urllib.request.Request(UPDATE_FILE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            new_code = response.read()
            with open(MAIN_APP_FILE, "wb") as f:
                f.write(new_code)

        # Helyi verziófájl frissítése
        with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(new_version)

        messagebox.showinfo("Siker", "A program sikeresen frissült a legújabb verzióra!")
        root.destroy()
    except Exception as e:
        messagebox.showerror("Hiba", f"Nem sikerült letölteni a frissítést: {e}")


def launch_app():
    """Elindítja a fő programot (main.py)."""
    if not os.path.exists(MAIN_APP_FILE):
        # Ha valamiért nincs meg a main.py, megpróbáljuk letölteni kényszerítve
        try:
            req = urllib.request.Request(UPDATE_FILE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with open(MAIN_APP_FILE, "wb") as f:
                    f.write(response.read())
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Kritikus Hiba", f"Nem található a fő programfájl és letölteni sem sikerült: {e}")
            sys.exit(1)

    # Futtatja a Python interpreterrel a main.py-t
    python_executable = sys.executable
    # Ha ablakos alkalmazást akarunk konzol nélkül, használhatjuk a pythonw-t vagy subprocess-t
    subprocess.Popen([python_executable, MAIN_APP_FILE])


if __name__ == "__main__":
    check_for_updates()
    launch_app()