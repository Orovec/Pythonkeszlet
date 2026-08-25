import os
import sys
import subprocess
import urllib.request
import json
import tkinter as tk
from tkinter import messagebox

# --- BEÁLLÍTÁSOK ---
VERSION_URL = "https://raw.githubusercontent.com/Orovec/Pythonkeszlet/refs/heads/main/dist/version.json"
UPDATE_FILE_URL = "https://raw.githubusercontent.com/Orovec/Pythonkeszlet/refs/heads/main/output/keszletkezeles.exe"

LOCAL_VERSION_FILE = "version.json"
MAIN_APP_FILE = "keszletkezeles.exe"


def log_error(message):
    """Hibák rögzítése egy helyi log fájlba."""
    try:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except:
        pass


def check_for_updates():
    """Letölti a legújabb program verziót, ha van újabb vagy hiányzik."""
    try:
        local_version = "1.0.0"
        if os.path.exists(LOCAL_VERSION_FILE):
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                local_version = f.read().strip()

        req = urllib.request.Request(VERSION_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            raw_data = response.read().decode("utf-8").strip()

        # Megpróbáljuk kitalálni, hogy JSON-e vagy sima szöveg
        remote_version = raw_data
        try:
            data_json = json.loads(raw_data)
            if isinstance(data_json, dict):
                remote_version = str(data_json.get("version", data_json.get("verzio", raw_data))).strip()
        except json.JSONDecodeError:
            pass

        print(f"Helyi verzió: {local_version}, Távoli verzió: {remote_version}")

        if remote_version and (remote_version != local_version or not os.path.exists(MAIN_APP_FILE)):
            print("Frissítés letöltése...")
            req_file = urllib.request.Request(UPDATE_FILE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_file, timeout=15) as response:
                new_code = response.read()
                with open(MAIN_APP_FILE, "wb") as f:
                    f.write(new_code)

            with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(remote_version)
            print("Frissítés sikeresen befejeződött.")

    except Exception as e:
        log_error(f"Frissítési hiba (nem kritikus): {e}")
        print(f"Frissítési hiba: {e}")


def launch_app():
    """Elindítja a fő program .exe fájlját."""
    if not os.path.exists(MAIN_APP_FILE):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Kritikus Hiba",
            f"A '{MAIN_APP_FILE}' fájl nem található, és a letöltés sem sikerült."
        )
        sys.exit(1)

    try:
        os.startfile(MAIN_APP_FILE)
        sys.exit(0)

    except Exception as e:
        log_error(f"Indítási hiba: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Hiba", f"Nem sikerült elindítani a fő programot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_for_updates()
    launch_app()