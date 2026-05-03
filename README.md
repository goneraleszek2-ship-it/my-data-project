# AML Transaction Monitoring Pipeline

A local AML detection pipeline built in Python, demonstrating three core FATF typologies on synthetic transaction data.

## Stack

- **Python 3.13** — data generation and analysis
- **SQLite** — lightweight local database
- **Faker** — synthetic Polish banking data (IBAN, UUIDs)
- **Rich** — terminal alert output
- **Datasette** — optional SQL browser UI

## Typologies Detected

| Alert | Description | Threshold |
|---|---|---|
| Structuring | Multiple transactions just below reporting threshold | < 15 000 PLN, ≥ 3 txn |
| High-risk countries | Exposure to sanctioned/high-risk jurisdictions | IR, KP, RU, BY, CY |
| Velocity | Unusual transaction frequency within 24h window | > 4 txn/day |

## Pipeline
cd
cd
## Quickstart

```bash
pip install faker rich datasette
python generate.py   # generates 400+ synthetic transactions
python load.py       # loads into SQLite
python queries.py    # runs AML detection, prints alerts
exit()
q
:q
x
