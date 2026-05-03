import sqlite3
from rich.console import Console
from rich.table import Table
from rich import box

con = sqlite3.connect("aml.db")
console = Console()

# --- ALERT 1: Structuring ---
console.rule("[bold red]ALERT: Structuring (próg 15 000 PLN)")
rows = con.execute("""
    SELECT
        account_from,
        COUNT(*)            AS liczba_txn,
        ROUND(SUM(amount), 2)  AS suma,
        ROUND(MIN(amount), 2)  AS min_kwota,
        ROUND(MAX(amount), 2)  AS max_kwota,
        MIN(DATE(timestamp))   AS od,
        MAX(DATE(timestamp))   AS do
    FROM transactions
    WHERE currency = 'PLN'
      AND amount BETWEEN 10000 AND 14999
    GROUP BY account_from
    HAVING COUNT(*) >= 3
    ORDER BY liczba_txn DESC
""").fetchall()

t = Table(box=box.SIMPLE)
for col in ["Konto", "Liczba txn", "Suma PLN", "Min", "Max", "Od", "Do"]:
    t.add_column(col)
for row in rows:
    t.add_row(*[str(x) for x in row])
console.print(t)

# --- ALERT 2: Kraje wysokiego ryzyka ---
console.rule("[bold red]ALERT: Kraje wysokiego ryzyka")
rows = con.execute("""
    SELECT
        account_from,
        country,
        COUNT(*)              AS liczba_txn,
        ROUND(SUM(amount), 2) AS suma,
        currency
    FROM transactions
    WHERE country IN ('IR','KP','RU','BY','CY')
    GROUP BY account_from, country, currency
    ORDER BY suma DESC
""").fetchall()

t2 = Table(box=box.SIMPLE)
for col in ["Konto", "Kraj", "Txn", "Suma", "Waluta"]:
    t2.add_column(col)
for row in rows:
    t2.add_row(*[str(x) for x in row])
console.print(t2)

# --- ALERT 3: Velocity ---
console.rule("[bold red]ALERT: Velocity (>4 txn w ciągu 24h)")
rows = con.execute("""
    SELECT
        account_from,
        COUNT(*)              AS txn_24h,
        ROUND(SUM(amount), 2) AS suma,
        MIN(timestamp)        AS pierwsza,
        MAX(timestamp)        AS ostatnia
    FROM transactions
    GROUP BY account_from,
             strftime('%Y-%m-%d', timestamp)
    HAVING COUNT(*) > 4
    ORDER BY txn_24h DESC
    LIMIT 10
""").fetchall()

t3 = Table(box=box.SIMPLE)
for col in ["Konto", "Txn/24h", "Suma", "Pierwsza", "Ostatnia"]:
    t3.add_column(col)
for row in rows:
    t3.add_row(*[str(x) for x in row])
console.print(t3)

con.close()
