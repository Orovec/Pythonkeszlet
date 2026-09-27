import pandas as pd
from sqlalchemy import create_engine
from tkinter import messagebox

class DatabaseManager:
    def __init__(self, database_url: str):
        """Inicionálja az adatbázis kapcsolatot a megadott URL alapján."""
        self.database_url = database_url
        try:
            self.engine = create_engine(self.database_url)
        except Exception as e:
            messagebox.showerror("Adatbázis Hiba", f"Nem sikerült kapcsolódni az adatbázishoz: {e}")
            self.engine = None

    def load_sheet_data(self, table_name: str) -> pd.DataFrame:
        """Betölti egy adott nevű tábla tartalmát az adatbázisból egy pandas DataFrame-be."""
        if not self.engine:
            return pd.DataFrame()
        try:
            df = pd.read_sql(f'SELECT * "{table_name}"', self.engine)
            return df.astype(str)
        except Exception:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', self.engine)
                return df.astype(str)
            except Exception:
                return pd.DataFrame()

    def save_sheet_data(self, table_name: str, df: pd.DataFrame):
        """Elmenti a pandas DataFrame adatait közvetlenül az adatbázisba."""
        if not self.engine:
            messagebox.showerror("Mentési hiba", "Nincs adatbázis kapcsolat!")
            return
        try:
            df.to_sql(table_name, self.engine, if_exists="replace", index=False)
        except Exception as e:
            messagebox.showerror("Mentési hiba", f"Nem sikerült menteni az adatbázisba: {e}")