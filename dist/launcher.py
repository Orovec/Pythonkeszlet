import os
import sys
import subprocess
import urllib.request
import json
import tkinter as tk
from tkinter import messagebox

# --- BEÁLLÍTÁSOK ---
# Tipp: Ha a GitHub repód nyilvános, vedd ki a '?token=...' részt a végéről, különben lejár!
VERSION_URL = "https://raw.githubusercontent.com/Orovec/Pythonkeszlet/refs/heads/main/dist/version.json"
UPDATE_FILE_URL = "https://raw.githubusercontent.com/Orovec/Pythonkeszlet/refs/heads/main/dist/keszletkezeles.py"

LOCAL_VERSION_FILE = "version.json"
MAIN_APP_FILE = "keszletkezeles.py"  # JAVÍTVA: Nem a launcher.py-t írjuk felül, hanem a fő programot!


def log_error(message):
    """Hibák rögzítése egy helyi log fájlba."""
    try:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except:
        pass


def check_for_updates():
    """Megpróbálja frissíteni a fő programot, de hiba esetén sem áll meg."""
    try:
        local_version = "1.0.0"
        if os.path.exists(LOCAL_VERSION_FILE):
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                local_version = f.read().strip()

        req = urllib.request.Request(VERSION_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            remote_version = data.get("version")

        if remote_version and remote_version != local_version:
            print(f"Új verzió elérhető: {remote_version}. Letöltés...")
            # Új programfájl letöltése
            req_file = urllib.request.Request(UPDATE_FILE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_file, timeout=5) as response:
                new_code = response.read()
                with open(MAIN_APP_FILE, "wb") as f:
                    f.write(new_code)

            # Verziófájl frissítése helyben
            with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(remote_version)
    except Exception as e:
        log_error(f"Frissítési hiba (nem kritikus): {e}")


def launch_app():
    """Elindítja a fő programot a megfelelő Python környezettel."""
    if not os.path.exists(MAIN_APP_FILE):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Kritikus Hiba",
            f"A '{MAIN_APP_FILE}' fájl nem található, és a letöltés sem sikerült (nincs internet?)."
        )
        sys.exit(1)

    try:
        # Windows alatt a pythonw.exe megakadályozza a felesleges háttér-konzolt
        python_executable = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(python_executable):
            python_executable = sys.executable

        # Indítás háttérfolyamatként
        subprocess.Popen([python_executable, MAIN_APP_FILE])
    except Exception as e:
        log_error(f"Indítási hiba: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Hiba", f"Nem sikerült elindítani a fő programot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_for_updates()
    launch_app()