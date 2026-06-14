import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "bookings.db"


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                patient_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                clinician TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clinic_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clinic_id TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                available INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.commit()
        seed_data(conn)


def seed_data(conn: sqlite3.Connection):
    from shared.auth import Role, hash_password

    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if users == 0:
        conn.executemany(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            [
                ("dr.smith", hash_password("clinician1"), Role.CLINICIAN.value, None),
                ("admin", hash_password("admin1"), Role.ADMIN.value, None),
                ("alice.p", hash_password("patient1"), Role.PATIENT.value, "P001"),
            ],
        )

    slots = conn.execute("SELECT COUNT(*) FROM clinic_slots").fetchone()[0]
    if slots == 0:
        slot_rows = []
        clinics = ["CLINIC-SYD", "CLINIC-MEL", "CLINIC-CBR", "CLINIC-REG1"]
        for day in range(1, 8):
            for hour in [9, 10, 11, 14, 15, 16]:
                for clinic in clinics:
                    slot_rows.append((clinic, f"2026-06-{day:02d}T{hour:02d}:00:00", 1))
        conn.executemany(
            "INSERT INTO clinic_slots (clinic_id, slot_time, available) VALUES (?, ?, ?)",
            slot_rows,
        )
    conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
