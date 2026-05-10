"""
aml_engine/graph.py — Graph Metrics Lookup

Pobiera metryki sieciowe dla konta z PostgreSQL.
Dane są generowane przez graph_analyze.py i przechowywane w tabeli graph_metrics.

Schemat tabeli:
    account           TEXT PRIMARY KEY
    degree_centrality REAL
    in_degree         INTEGER
    out_degree        INTEGER
    pagerank          REAL
    betweenness       REAL
    community_id      INTEGER
    network_role      TEXT  (CONSOLIDATOR / DISTRIBUTOR / HUB / CENTRAL / STANDARD)
    risk_score        INTEGER
    risk_level        TEXT
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


def get_graph_metrics(account_id):
    """
    Zwraca metryki sieciowe dla podanego account_id.

    Args:
        account_id (str): numer konta bankowego (IBAN)

    Returns:
        dict: {pagerank, betweenness, in_degree, out_degree,
               community_id, network_role}
        None: jeśli konto nie istnieje w tabeli graph_metrics
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT pagerank, betweenness, in_degree, out_degree,
                   community_id, network_role
            FROM graph_metrics
            WHERE account = %s
        """, (account_id.strip(),))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "pagerank":     round(row[0], 6),
            "betweenness":  round(row[1], 4),
            "in_degree":    row[2],
            "out_degree":   row[3],
            "community_id": row[4],
            "network_role": row[5]
        }
    finally:
        conn.close()
