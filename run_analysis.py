# run_analysis.py — executes AML queries and measures performance

import sqlite3
import time
from rich.console import Console
from rich.table import Table
from rich import box

con = sqlite3.connect("aml.db")
console = Console()

queries = [

("1: Account Profile (CTE + CASE WHEN)", """
WITH account_profile AS (
    SELECT
        account_from,
        COUNT(*)                        AS total_txn,
        ROUND(SUM(amount), 2)           AS total_amount,
        ROUND(AVG(amount), 2)           AS avg_amount,
        COUNT(DISTINCT currency)        AS currency_count,
        COUNT(DISTINCT country)         AS country_count,
        MIN(DATE(timestamp))            AS first_txn_date,
        MAX(DATE(timestamp))            AS last_txn_date,
        JULIANDAY(MAX(timestamp)) -
        JULIANDAY(MIN(timestamp))       AS active_days
    FROM transactions
    GROUP BY account_from
)
SELECT
    account_from,
    total_txn,
    total_amount,
    avg_amount,
    currency_count,
    country_count,
    CASE
        WHEN total_amount > 100000 THEN 'HIGH VALUE'
        WHEN total_amount > 50000  THEN 'MEDIUM VALUE'
        ELSE                            'STANDARD'
    END AS value_segment,
    CASE
        WHEN active_days > 0
        THEN ROUND(total_txn * 1.0 / active_days, 2)
        ELSE total_txn
    END AS avg_txn_per_day
FROM account_profile
ORDER BY total_amount DESC
"""),

("2: Ranking + Percentiles (Window Functions)", """
WITH account_totals AS (
    SELECT
        account_from,
        COUNT(*)              AS txn_count,
        ROUND(SUM(amount), 2) AS total_amount
    FROM transactions
    GROUP BY account_from
)
SELECT
    account_from,
    txn_count,
    total_amount,
    RANK() OVER (ORDER BY total_amount DESC) AS amount_rank,
    ROUND(100.0 * total_amount / SUM(total_amount) OVER (), 2) || '%' AS share,
    ROUND(100.0 * SUM(total_amount) OVER (
        ORDER BY total_amount DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / SUM(total_amount) OVER (), 2) || '%' AS cumulative_share
FROM account_totals
ORDER BY amount_rank
"""),

("3: Daily Volume + 7d Moving Average (LAG + AVG OVER)", """
WITH daily_volume AS (
    SELECT
        DATE(timestamp)           AS txn_date,
        COUNT(*)                  AS daily_txn,
        ROUND(SUM(amount), 2)     AS daily_amount
    FROM transactions
    GROUP BY DATE(timestamp)
)
SELECT
    txn_date,
    daily_txn,
    daily_amount,
    ROUND(AVG(daily_amount) OVER (
        ORDER BY txn_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_7d,
    daily_amount - LAG(daily_amount) OVER (ORDER BY txn_date) AS day_over_day,
    CASE
        WHEN daily_amount > 2 * AVG(daily_amount) OVER (
            ORDER BY txn_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) THEN 'ANOMALY'
        ELSE 'NORMAL'
    END AS day_status
FROM daily_volume
ORDER BY txn_date
"""),

("4: Flow Matrix - Top 10 Pairs (RANK OVER)", """
WITH flow_matrix AS (
    SELECT
        account_from,
        account_to,
        COUNT(*)              AS txn_count,
        ROUND(SUM(amount), 2) AS total_flow,
        ROUND(AVG(amount), 2) AS avg_flow
    FROM transactions
    WHERE account_from != account_to
    GROUP BY account_from, account_to
)
SELECT
    RANK() OVER (ORDER BY total_flow DESC) AS flow_rank,
    account_from,
    account_to,
    txn_count,
    total_flow,
    avg_flow
FROM flow_matrix
ORDER BY flow_rank
LIMIT 10
"""),

("5: Full Account View - JOIN risk_scores (LEFT JOIN + COALESCE)", """
WITH txn_summary AS (
    SELECT
        account_from,
        COUNT(*)                                    AS total_txn,
        ROUND(SUM(amount), 2)                       AS total_amount,
        COUNT(DISTINCT country)                     AS countries_used,
        COUNT(DISTINCT currency)                    AS currencies_used,
        SUM(CASE WHEN country IN
            ('IR','KP','RU','BY','CY')
            THEN 1 ELSE 0 END)                      AS high_risk_txn
    FROM transactions
    GROUP BY account_from
)
SELECT
    t.account_from,
    t.total_txn,
    t.total_amount,
    t.countries_used,
    t.high_risk_txn,
    COALESCE(r.score, 0)          AS risk_score,
    COALESCE(r.level, 'NO ALERT') AS risk_level
FROM txn_summary t
LEFT JOIN risk_scores r ON t.account_from = r.account
ORDER BY risk_score DESC, total_amount DESC
"""),

]


def run_query(title, sql):
    console.rule(f"[bold cyan]QUERY {title}")

    console.print("[bold yellow]Query Plan:[/bold yellow]")
    plan = con.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
    for row in plan:
        console.print(f"  [dim]{row}[/dim]")

    start = time.perf_counter()
    cursor = con.execute(sql)
    rows = cursor.fetchall()
    elapsed = (time.perf_counter() - start) * 1000

    if not rows:
        console.print("[yellow]No results.[/yellow]")
        return

    col_names = [d[0] for d in cursor.description]
    t = Table(box=box.SIMPLE)
    for col in col_names:
        t.add_column(col, overflow="fold")
    for row in rows[:15]:
        t.add_row(*[str(x) if x is not None else "NULL" for x in row])
    console.print(t)

    if len(rows) > 15:
        console.print(f"[dim]... {len(rows) - 15} more rows[/dim]")

    console.print(
        f"[green]Rows:[/green] {len(rows)}  "
        f"[green]Time:[/green] {elapsed:.2f} ms  "
        f"[green]Cols:[/green] {len(col_names)}\n"
    )


for title, sql in queries:
    run_query(title, sql)

# Index analysis
console.rule("[bold magenta]INDEX ANALYSIS")
indexes = con.execute("""
    SELECT name, tbl_name FROM sqlite_master WHERE type = 'index'
""").fetchall()

if indexes:
    for name, table in indexes:
        console.print(f"[green]{name}[/green] on [cyan]{table}[/cyan]")
else:
    console.print("[yellow]No indexes — all queries use full table scans.[/yellow]")
    console.print("\nRecommended indexes for this AML workload:")
    console.print("  CREATE INDEX idx_account_from ON transactions(account_from);")
    console.print("  CREATE INDEX idx_currency_amount ON transactions(currency, amount);")
    console.print("  CREATE INDEX idx_country ON transactions(country);")
    console.print("  CREATE INDEX idx_timestamp ON transactions(timestamp);")

con.close()
