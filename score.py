# score.py — AML Risk Scoring Engine
# Przypisuje wynik ryzyka 0-100 każdemu kontu z alertu.
# Progi: HIGH >= 70, MEDIUM >= 40, LOW < 40

import sqlite3
from rich.console import Console
from rich.table import Table
from rich import box

con = sqlite3.connect("aml.db")
console = Console()

# Sygnał 1: Structuring — transakcje tuż poniżej progu 15k PLN (Art. 72 Ustawy AML)
structuring = {row[0]: row[1] for row in con.execute("""
    SELECT account_from, COUNT(*) as cnt
    FROM transactions
    WHERE currency = 'PLN' AND amount BETWEEN 10000 AND 14999
    GROUP BY account_from
    HAVING COUNT(*) >= 3
""").fetchall()}

# Sygnał 2: High-risk countries — ekspozycja na jurysdykcje FATF/KE 2016/1675
high_risk = {row[0]: row[1] for row in con.execute("""
    SELECT account_from, ROUND(SUM(amount), 2)
    FROM transactions
    WHERE country IN ('IR','KP','RU','BY','CY')
    GROUP BY account_from
""").fetchall()}

# Sygnał 3: Velocity — layering przez szybką sekwencję transakcji
velocity = {row[0]: row[1] for row in con.execute("""
    SELECT account_from, MAX(cnt) as max_daily
    FROM (
        SELECT account_from, COUNT(*) as cnt
        FROM transactions
        GROUP BY account_from, strftime('%Y-%m-%d', timestamp)
    )
    GROUP BY account_from
    HAVING MAX(cnt) > 4
""").fetchall()}

# Unia kont ze wszystkich alertów
all_accounts = set(structuring) | set(high_risk) | set(velocity)


def compute_score(account):
    score = 0
    reasons = []

    # Structuring: 5 pkt za transakcję, max 40
    if account in structuring:
        txn_count = structuring[account]
        points = min(40, txn_count * 5)
        score += points
        reasons.append(f"structuring ({txn_count} txn, +{points})")

    # High-risk: 1 pkt za 5000 jednostek waluty, max 40
    if account in high_risk:
        amount = high_risk[account]
        points = min(40, int(amount / 5000))
        score += points
        reasons.append(f"high-risk country ({amount:,.0f}, +{points})")

    # Velocity: 3 pkt za txn/dzień powyżej progu, max 20
    # Mniejsza waga — velocity może mieć uzasadnienie biznesowe
    if account in velocity:
        daily = velocity[account]
        points = min(20, daily * 3)
        score += points
        reasons.append(f"velocity ({daily} txn/day, +{points})")

    return min(score, 100), reasons


# Oblicz i posortuj malejąco
results = []
for account in all_accounts:
    score, reasons = compute_score(account)
    results.append((account, score, reasons))

results.sort(key=lambda x: x[1], reverse=True)

# Wyświetl tabelę z kolorowym kodowaniem ryzyka
console.rule("[bold red]AML RISK SCORING")

t = Table(box=box.SIMPLE)
t.add_column("Konto", style="cyan")
t.add_column("Score", style="bold")
t.add_column("Poziom", style="bold")
t.add_column("Sygnały — audit trail")

for account, score, reasons in results:
    if score >= 70:
        level = "[red]HIGH[/red]"
    elif score >= 40:
        level = "[yellow]MEDIUM[/yellow]"
    else:
        level = "[green]LOW[/green]"

    t.add_row(
        account[:30] + "...",
        str(score),
        level,
        " | ".join(reasons)
    )

console.print(t)

# Zapisz do bazy — wejście dla sar.py
# INSERT OR REPLACE zapewnia idempotentność
con.execute("""
    CREATE TABLE IF NOT EXISTS risk_scores (
        account  TEXT PRIMARY KEY,
        score    INTEGER,
        level    TEXT,
        signals  TEXT
    )
""")

con.executemany("""
    INSERT OR REPLACE INTO risk_scores VALUES (?,?,?,?)
""", [
    (acc, score,
     "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW",
     " | ".join(reasons))
    for acc, score, reasons in results
])

con.commit()
print(f"\nZapisano {len(results)} kont do tabeli risk_scores.")
print("Konta HIGH gotowe dla sar.py")
con.close()
