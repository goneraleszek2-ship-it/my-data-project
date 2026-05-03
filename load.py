import sqlite3, json

con = sqlite3.connect("aml.db")
con.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        txn_id       TEXT PRIMARY KEY,
        timestamp    TEXT,
        account_from TEXT,
        account_to   TEXT,
        amount       REAL,
        currency     TEXT,
        country      TEXT,
        channel      TEXT,
        flagged      INTEGER
    )
""")

with open("transactions.json") as f:
    data = json.load(f)

con.executemany("""
    INSERT OR IGNORE INTO transactions
    VALUES (?,?,?,?,?,?,?,?,?)
""", [
    (r["txn_id"], r["timestamp"], r["account_from"],
     r["account_to"], r["amount"], r["currency"],
     r["country"], r["channel"], int(r["flagged"]))
    for r in data
])

con.commit()
count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
print(f"Załadowano {count} rekordów do aml.db")
con.close()
