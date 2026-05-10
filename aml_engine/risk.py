"""
aml_engine/risk.py — Risk Score Lookup

Pobiera prekalkulowane wyniki scoringu AML z PostgreSQL.
Dane są generowane przez score.py i przechowywane w tabeli risk_scores.

Schemat tabeli:
    account  TEXT PRIMARY KEY
    score    INTEGER  (0-100)
    level    TEXT     (HIGH / MEDIUM / LOW / UNKNOWN)
    signals  TEXT     (audit trail - jakie sygnały złożyły się na wynik)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def _get_connection():
    """Otwiera połączenie z PostgreSQL na podstawie zmiennych .env."""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )


def get_risk(account_id):
    """
    Zwraca risk score dla podanego account_id.

    Args:
        account_id (str): numer konta bankowego (IBAN)

    Returns:
        dict: {score, level, signals}
              Jeśli konto nie istnieje w tabeli, zwraca score=0, level=UNKNOWN.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT score, level, signals FROM risk_scores WHERE account = %s",
            (account_id.strip(),)
        )
        row = cur.fetchone()
        return (
            {"score": row[0], "level": row[1], "signals": row[2]}
            if row
            else {"score": 0, "level": "UNKNOWN", "signals": "No data for this account"}
        )
    finally:
        conn.close()
