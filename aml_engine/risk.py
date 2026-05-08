import sqlite3
import os

# Get absolute path to the database (assuming it's in the project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "aml.db")

def get_risk(account_id):
    """Return risk score and level for a given account_id from precomputed table."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT score, level, signals FROM risk_scores WHERE account = ?",
        (account_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"score": row[0], "level": row[1], "signals": row[2]}
    else:
        return {"score": 0, "level": "UNKNOWN", "signals": "No data for this account"}
