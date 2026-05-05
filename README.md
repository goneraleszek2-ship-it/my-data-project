# AML Transaction Monitoring Pipeline

A local AML detection pipeline built in Python, demonstrating an end-to-end
financial crime detection workflow from raw transaction data to SAR draft.

## Stack

- **Python 3.13** — data generation and analysis
- **SQLite** — lightweight local database
- **Faker** — synthetic Polish banking data (IBAN, UUIDs)
- **Rich** — terminal alert output
- **Datasette** — optional SQL browser UI

## Pipeline

generate.py  ->  load.py  ->  queries.py  ->  score.py  ->  sar.py
     |               |              |              |             |
transactions    aml.db         3 AML alerts   risk score   SAR draft
  (412 txn)   (SQLite)                          0-100        (.txt)

## Modules

| File | Description |
|---|---|
| generate.py | Generates 400+ synthetic transactions with embedded AML patterns |
| load.py | Loads transactions into SQLite |
| queries.py | Detects 3 FATF typologies: structuring, high-risk countries, velocity |
| score.py | Additive risk scoring engine - assigns 0-100 score per account |
| sar.py | Generates SAR draft documents for MEDIUM/HIGH risk accounts |

## Typologies Detected

| Alert | Description | Threshold |
|---|---|---|
| Structuring | Transactions just below reporting threshold | < 15 000 PLN, 3+ txn |
| High-risk countries | Exposure to sanctioned jurisdictions | IR, KP, RU, BY, CY |
| Velocity | Unusual transaction frequency | > 4 txn/24h |

## Risk Scoring

| Signal | Max points | Logic |
|---|---|---|
| Structuring | 40 | 5 pts per transaction |
| High-risk country | 40 | 1 pt per 5 000 currency units |
| Velocity | 20 | 3 pts per txn/day above threshold |

| Level | Score | Action |
|---|---|---|
| HIGH | >= 70 | SAR submission to GIIF |
| MEDIUM | >= 40 | Enhanced Due Diligence |
| LOW | < 40 | Standard monitoring |

## Quickstart

pip install faker rich datasette
python generate.py
python load.py
python queries.py
python score.py
python sar.py

## Optional: Browser UI

datasette aml.db --port 8001

## Regulatory Context

- Structuring threshold: Polish AML Act 2018 (Art. 72) - PLN 15 000
- High-risk jurisdictions: FATF + EU Delegated Regulation 2016/1675
- SAR reporting authority: GIIF (Generalny Inspektor Informacji Finansowej)
- Secondary: EU AMLD6 (Directive 2018/1673), FATF Recommendations 2023

## Author

AML Analyst with background in data engineering.
Interested in RegTech, compliance automation, and financial crime detection.

https://github.com/goneraleszek2-ship-it
