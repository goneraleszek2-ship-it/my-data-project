# AML Transaction Monitoring Pipeline

End-to-end financial crime detection pipeline built in Python and SQL.
Covers the full AML workflow: from raw transaction data through typology
detection, risk scoring, SAR draft generation, to SQL performance analysis.

Built as a portfolio project demonstrating the intersection of AML domain
knowledge and data engineering skills.

## Pipeline Architecture

generate.py -> load.py -> queries.py -> score.py -> sar.py
    |              |           |             |          |
 412 synthetic  SQLite     3 FATF       risk score  SAR draft
 transactions   aml.db    typologies    0-100        (.txt)


## Files

generate.py     Synthetic Polish banking data (Faker, IBAN, UUID)
load.py         Loads transactions into SQLite with schema validation
queries.py      AML alert detection — 3 FATF typologies
score.py        Additive risk scoring engine with audit trail
sar.py          SAR draft generator for MEDIUM/HIGH risk accounts
analysis.sql    5 advanced SQL queries with documented methodology
run_analysis.py Executes SQL queries, shows query plans and benchmarks


## AML Typologies Detected

Structuring       Transactions below PLN 15,000 reporting threshold
                  Art. 72, Polish AML Act 2018 — >= 3 transactions
                  FATF Typology: Smurfing

High-risk         Exposure to sanctioned/high-risk jurisdictions
jurisdictions     IR, KP, RU, BY, CY
                  EU Delegated Regulation 2016/1675

Velocity          Transaction frequency anomaly within 24h window
                  Indicator of layering — second stage of ML cycle
                  Threshold: > 4 transactions per day


## Risk Scoring Model

Additive model — each signal contributes weighted points independently.
Design principle: no single signal should alone produce HIGH classification.

  Signal                Max pts   Logic
  Structuring             40      5 pts per transaction below threshold
  High-risk country       40      1 pt per 5,000 currency units
  Velocity                20      3 pts per txn/day above threshold

  Level     Score    Recommended action
  HIGH      >= 70    SAR submission to GIIF
  MEDIUM    >= 40    Enhanced Due Diligence
  LOW       < 40     Standard monitoring


## SQL Analysis — Techniques Demonstrated

analysis.sql contains 5 queries with documented methodology:

  Query 1   CTE + CASE WHEN        Account profiling and segmentation
  Query 2   RANK() + SUM() OVER    Percentile ranking across population
  Query 3   LAG() + AVG() OVER     7-day moving average, anomaly detection
  Query 4   RANK() OVER            Transaction flow matrix, top pairs
  Query 5   LEFT JOIN + COALESCE   Integrated risk view with score join

Each query includes rationale for technique selection and AML context.


## Index Benchmarking Results

Measured on 412 transactions, SQLite 3.x, Python 3.13, ARM64 Android.

  Query                     Before    After     Change    Plan change
  Account Profile (Q1)      3.60 ms   1.28 ms   -64%      FULL SCAN -> INDEX SCAN
  Ranking/Percentiles (Q2)  1.09 ms   0.97 ms   -11%      INDEX SCAN
  Time Series / LAG (Q3)    1.44 ms   1.54 ms   +7%       no change (optimal)
  Flow Matrix (Q4)          1.85 ms   1.95 ms   +5%       INDEX SCAN
  JOIN risk_scores (Q5)     1.05 ms   1.19 ms   +13%      no change

Note: Q3-Q5 regression on small dataset is expected index overhead.
At production scale (millions of rows), indexed queries show 10-100x gains.
idx_timestamp unused in Q3 because full chronological scan is optimal
for moving average window calculations.

Indexes created:
  idx_account_from      transactions(account_from)
  idx_currency_amount   transactions(currency, amount)
  idx_country           transactions(country)
  idx_timestamp         transactions(timestamp)


## Quickstart

  pip install faker rich datasette
  python generate.py      # generate synthetic transactions
  python load.py          # load into SQLite
  python queries.py       # AML alert detection
  python score.py         # risk scoring
  python sar.py           # SAR draft generation
  python run_analysis.py  # SQL analysis + benchmarks


## Optional: Browser UI

  datasette aml.db --port 8001
  open http://localhost:8001


## Regulatory Basis

  Polish AML Act       Ustawa z dnia 1 marca 2018 r. o przeciwdzialaniu
                       praniu pieniedzy oraz finansowaniu terroryzmu
                       Art. 72 — reporting threshold PLN 15,000

  FATF                 Recommendations 2012 (updated 2023)
                       Typologies: structuring, layering, smurfing

  EU AMLD6             Directive 2018/1673

  EU Delegated Reg.    2016/1675 — high-risk third countries

  GIIF                 Generalny Inspektor Informacji Finansowej
                       Polish FIU — SAR submission authority


## Author

Leszek Gonera
AML Analyst | Data Engineering background
ICA Certified | SQL | Python | RegTech

https://github.com/goneraleszek2-ship-it
