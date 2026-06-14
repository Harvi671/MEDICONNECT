import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "patients.db"


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                medicare_number TEXT NOT NULL,
                conditions TEXT,
                clinic_id TEXT NOT NULL
            )
        """)
        conn.commit()
        seed_patients(conn)


def seed_patients(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if existing > 0:
        return

    patients = [
        ("P001", "Alice Nguyen", "1985-03-12", "2950123456", "Type 2 Diabetes", "CLINIC-SYD"),
        ("P002", "James O'Brien", "1972-08-25", "2950987654", "Hypertension", "CLINIC-MEL"),
        ("P003", "Priya Sharma", "1990-11-03", "2950111222", "Asthma", "CLINIC-CBR"),
        ("P004", "Mohammed Ali", "1968-01-19", "2950333444", "COPD", "CLINIC-REG1"),
        ("P005", "Emma Wilson", "2001-06-30", "2950555666", "None", "CLINIC-SYD"),
    ]
    conn.executemany(
        "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?)",
        patients,
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
