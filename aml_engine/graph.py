import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "aml.db")

def get_graph_metrics(account_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT pagerank, betweenness, in_degree, out_degree,
               community_id, network_role
        FROM graph_metrics
        WHERE account = ?
    """, (account_id.strip(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "pagerank":     round(row[0], 6),
            "betweenness":  round(row[1], 4),
            "in_degree":    row[2],
            "out_degree":   row[3],
            "community_id": row[4],
            "network_role": row[5]
        }
    return None
