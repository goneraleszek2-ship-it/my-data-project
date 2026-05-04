# sar.py — SAR Draft Generator
# Generuje szkielety Suspicious Activity Report dla kont MEDIUM i HIGH.
# Wejście: tabela risk_scores (score.py) + tabela transactions (load.py)
# Wyjście: pliki tekstowe SAR_DRAFT_<konto>.txt

import sqlite3
import os
from datetime import datetime
from rich.console import Console

con = sqlite3.connect("aml.db")
console = Console()

# Pobierz konta kwalifikujące się do SAR draft (MEDIUM i HIGH)
candidates = con.execute("""
    SELECT account, score, level, signals
    FROM risk_scores
    WHERE level IN ('HIGH', 'MEDIUM')
    ORDER BY score DESC
""").fetchall()

if not candidates:
    console.print("[yellow]Brak kont kwalifikujących się do SAR draft.[/yellow]")
    con.close()
    exit()

# Utwórz katalog na drafty jeśli nie istnieje
os.makedirs("sar_drafts", exist_ok=True)

generated = []

for account, score, level, signals in candidates:

    # Pobierz statystyki transakcji dla tego konta
    stats = con.execute("""
        SELECT
            COUNT(*)                    as total_txn,
            ROUND(SUM(amount), 2)       as total_amount,
            MIN(DATE(timestamp))        as date_from,
            MAX(DATE(timestamp))        as date_to,
            GROUP_CONCAT(DISTINCT currency) as currencies,
            GROUP_CONCAT(DISTINCT country)  as countries,
            GROUP_CONCAT(DISTINCT channel)  as channels
        FROM transactions
        WHERE account_from = ?
    """, (account,)).fetchone()

    total_txn, total_amount, date_from, date_to, currencies, countries, channels = stats

    # Pobierz top 5 transakcji (najwyższe kwoty) jako przykłady
    top_txns = con.execute("""
        SELECT timestamp, amount, currency, country, channel
        FROM transactions
        WHERE account_from = ?
        ORDER BY amount DESC
        LIMIT 5
    """, (account,)).fetchall()

    # Określ typologię na podstawie sygnałów
    typologies = []
    if "structuring" in signals:
        typologies.append(
            "STRUCTURING: Multiple transactions detected below the PLN 15,000 "
            "mandatory reporting threshold (Art. 72, Polish AML Act 2018). "
            "Pattern consistent with deliberate avoidance of transaction reporting obligations."
        )
    if "high-risk country" in signals:
        typologies.append(
            "HIGH-RISK JURISDICTION EXPOSURE: Transactions involving countries "
            "listed under FATF high-risk jurisdictions and EU Delegated Regulation "
            "2016/1675. Potential layering or integration through high-risk corridors."
        )
    if "velocity" in signals:
        typologies.append(
            "VELOCITY ANOMALY: Unusual transaction frequency detected within 24-hour "
            "windows. Pattern may indicate layering — rapid movement of funds to "
            "obscure origin trail."
        )

    # Zbuduj treść SAR draft
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    account_short = account[:34]

    content = f"""
SUSPICIOUS ACTIVITY REPORT — DRAFT
Generated: {now}
Status: DRAFT — requires analyst review before submission
Reference: SAR-DRAFT-{account[:10].replace(' ', '')}-{datetime.now().strftime('%Y%m%d')}

SUBJECT INFORMATION
Account number : {account_short}
Risk score     : {score}/100
Risk level     : {level}
Active signals : {signals}

TRANSACTION SUMMARY
Total transactions : {total_txn}
Total amount       : {total_amount:,.2f}
Period             : {date_from} to {date_to}
Currencies used    : {currencies}
Countries involved : {countries}
Channels used      : {channels}

TOP TRANSACTIONS BY AMOUNT
"""

    for ts, amt, curr, country, channel in top_txns:
        content += f"  {ts[:16]}  {amt:>12,.2f} {curr}  {country}  {channel}\n"

    content += f"""
TYPOLOGY ASSESSMENT
"""
    for i, t in enumerate(typologies, 1):
        content += f"\n{i}. {t}\n"

    content += f"""
REGULATORY BASIS
Primary    : Polish AML Act (Ustawa z dnia 1 marca 2018 r. o przeciwdziałaniu
             praniu pieniędzy oraz finansowaniu terroryzmu)
Secondary  : FATF Recommendations 2012 (updated 2023)
             EU AMLD6 (Directive 2018/1673)
             EU Delegated Regulation 2016/1675 (high-risk third countries)

ANALYST SECTION — TO BE COMPLETED
Investigation date    : _______________
Analyst name          : _______________
Case reference        : _______________

Supporting evidence reviewed:
  [ ] Transaction history verified
  [ ] KYC/CDD documentation reviewed
  [ ] Adverse media screening completed
  [ ] PEP/Sanctions screening completed
  [ ] Customer explanation obtained

Narrative:
  [ opisz okoliczności, wyjaśnienie klienta, ocenę wiarygodności ]

Recommended action:
  [ ] Submit SAR to GIIF (Generalny Inspektor Informacji Finansowej)
  [ ] Enhanced Due Diligence — escalate to Senior Analyst
  [ ] No SAR — document rationale below
  [ ] Account restriction / exit

Rationale for decision:
  [ uzasadnienie decyzji ]

Supervisor approval: _______________  Date: _______________
"""

    # Zapisz plik
    filename = f"sar_drafts/SAR_DRAFT_{account[:20].replace(' ', '_')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    generated.append((account_short, score, level, filename))
    console.print(f"[green]Wygenerowano:[/green] {filename}")

console.print(f"\n[bold]Łącznie wygenerowano {len(generated)} SAR draft(s) w katalogu sar_drafts/[/bold]")
con.close()
