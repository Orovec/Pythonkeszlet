import os
import sys
import subprocess
import urllib.request
import json
import tkinter as tk
from tkinter import messagebox

# --- BEÁLLÍTÁSOk ---
VERSION_URL = "https://raw.githubusercontent.com/Orovec/Pythonkeszlet/refs/heads/main/dist/version.json"
UPDATE_FILE_URL = "https://raw.githubusercontent.com/Orovec/Pythonkeszlet/refs/heads/main/dist/keszletkezeles.py"

LOCAL_VERSION_FILE = "version.json"
MAIN_APP_FILE = "keszletkezeles.py"

# Ide gyűjtsd a fő programod külső függőségeit!
REQUIRED_PACKAGES = ["sqlalchemy"]


def log_error(message):
    """Hibák rögzítése egy helyi log fájlba."""
    try:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except:
        pass


def ensure_dependencies():
    """Ellenőrzi a csomagokat, és ha hiányzik valami, automatikusan telepíti."""
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            try:
                # Háttérben telepíti a hiányzó csomagot pip-pel
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            except Exception as e:
                log_error(f"Nem sikerült telepíteni a(z) {package} csomagot: {e}")


def check_for_updates():
    """Megpróbálja frissíteni a fő programot, vagy letölti, ha még nincs meg."""
    try:
        local_version = "1.0.0"
        if os.path.exists(LOCAL_VERSION_FILE):
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                local_version = f.read().strip()

        req = urllib.request.Request(VERSION_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            remote_version = response.read().decode("utf-8").strip()

        if remote_version and (remote_version != local_version or not os.path.exists(MAIN_APP_FILE)):
            req_file = urllib.request.Request(UPDATE_FILE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_file, timeout=5) as response:
                new_code = response.read()
                with open(MAIN_APP_FILE, "wb") as f:
                    f.write(new_code)

            with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(remote_version)
    except Exception as e:
        log_error(f"Frissítési hiba (nem kritikus): {e}")


def launch_app():
    """Elindítja a fő programot."""
    if not os.path.exists(MAIN_APP_FILE):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Kritikus Hiba",
            f"A '{MAIN_APP_FILE}' fájl nem található, és a letöltés sem sikerült."
        )
        sys.exit(1)

    try:
        if os.name == 'nt':
            os.startfile(MAIN_APP_FILE)
        else:
            subprocess.Popen([sys.executable, MAIN_APP_FILE])

        sys.exit(0)

    except Exception as e:
        log_error(f"Indítási hiba: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Hiba", f"Nem sikerült elindítani a fő programot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ensure_dependencies()  # 1. Először ellenőrzi és telepíti a hiányzó csomagokat
    check_for_updates()  # 2. Utána frissíti a kódot, ha van újabb
    launch_app()  # 3. Végül elindítja az alkalmazást