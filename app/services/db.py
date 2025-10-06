# db.py
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "feeder.db"

def init_db():
    """Initialize local database with schedules table."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            food TEXT DEFAULT 'default',
            cycle INTEGER DEFAULT 1,
            switch INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def save_schedules(schedules):
    """Replace local schedules with new ones from backend."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM schedules")  # wipe old schedules
    for s in schedules:
        cur.execute(
            "INSERT INTO schedules (time, food, cycle, switch) VALUES (?, ?, ?, ?)",
            (s.get("time"), s.get("food", "default"), s.get("cycle", 1), int(s.get("switch", True)))
        )
    conn.commit()
    conn.close()

def get_schedules():
    """Fetch all schedules from local DB."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT time, food, cycle, switch FROM schedules")
    rows = cur.fetchall()
    conn.close()
    schedules = []
    for r in rows:
        schedules.append({"time": r[0], "food": r[1], "cycle": r[2], "switch": bool(r[3])})
    return schedules