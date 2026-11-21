"""SQLite storage for battery assessments."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

# The database file is created automatically next to this file.
# Set REVOLT_DB_PATH to store it somewhere else (tests do this).
DB_PATH = os.environ.get(
    "REVOLT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "revolt.db"),
)

INPUT_FIELDS = ["cycle_number", "avg_voltage", "avg_current", "avg_temperature", "discharge_time"]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us read columns by name
    return conn


def init_db():
    """Create the table if it does not exist yet (safe to call many times)."""
    with closing(_connect()) as conn:
        with conn:  # commits when the block finishes
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_number          REAL NOT NULL,
                    avg_voltage           REAL NOT NULL,
                    avg_current           REAL NOT NULL,
                    avg_temperature       REAL NOT NULL,
                    discharge_time        REAL NOT NULL,
                    soh_percent           REAL NOT NULL,
                    remaining_capacity_ah REAL NOT NULL,
                    rated_capacity_ah     REAL NOT NULL,
                    category              TEXT NOT NULL,
                    created_at            TEXT NOT NULL
                )
                """
            )


def save_assessment(inputs, result):
    """Save one assessment. Returns the new row id."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # The ? marks are placeholders: SQLite fills them in safely (prevents SQL injection).
    with closing(_connect()) as conn:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO assessments
                    (cycle_number, avg_voltage, avg_current, avg_temperature, discharge_time,
                     soh_percent, remaining_capacity_ah, rated_capacity_ah, category, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inputs["cycle_number"], inputs["avg_voltage"], inputs["avg_current"],
                    inputs["avg_temperature"], inputs["discharge_time"],
                    result["soh_percent"], result["remaining_capacity_ah"],
                    result["rated_capacity_ah"], result["category"], created_at,
                ),
            )
            return cursor.lastrowid


def get_history(limit=50):
    """Return the most recent assessments, newest first, as a list of dicts."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM assessments ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "inputs": {name: row[name] for name in INPUT_FIELDS},
            "soh_percent": row["soh_percent"],
            "remaining_capacity_ah": row["remaining_capacity_ah"],
            "rated_capacity_ah": row["rated_capacity_ah"],
            "category": row["category"],
            "created_at": row["created_at"],
        })
    return history
