# AML Transaction Monitoring Pipeline

End-to-end financial crime detection pipeline built in Python and SQL.
Covers the full AML workflow: from raw transaction data through typology
detection, risk scoring, SAR draft generation, SQL performance analysis,
to network graph analysis.

Built as a portfolio project demonstrating the intersection of AML domain
knowledge and data engineering skills.


## Pipeline Architecture

generate.py -> load.py -> queries.py -> score.py -> sar.py
    |              |           |             |          |
 412 synthetic  SQLite     3 FATF       risk score  SAR draft
 transactions   aml.db    typologies    0-100        (.txt)

graph_build.py -> graph_analyze.py
    |                    |
 DiGraph             PageRank
 24 nodes            Betweenness
 244 edges           Communities
                     Blind spots


## Files

generate.py        Synthetic Polish banking data (Faker, IBAN, UUID)
load.py            Loads transactions into SQLite with schema validation
queries.py         AML alert detection - 3 FATF typologies
score.py           Additive risk scoring engine with audit trail
sar.py             SAR draft generator for MEDIUM/HIGH risk accounts
analysis.sql       5 advanced SQL queries with documented methodology
run_analysis.py    Executes SQL queries, shows query plans and benchmarks
graph_build.py     Builds directed transaction graph (NetworkX DiGraph)
graph_analyze.py   PageRank, betweenness centrality, community detection


## AML Typologies Detected

Structuring       Transactions below PLN 15,000 reporting threshold
                  Art. 72, Polish AML Act 2018 - >= 3 transactions
                  FATF Typology: Smurfing

High-risk         Exposure to sanctioned/high-risk jurisdictions
jurisdictions     IR, KP, RU, BY, CY
                  EU Delegated Regulation 2016/1675

Velocity          Transaction frequency anomaly within 24h window
                  Indicator of layering - second stage of ML cycle
                  Threshold: > 4 transactions per day


## Risk Scoring Model

Additive model - each signal contributes weighted points independently.
Design principle: no single signal should alone produce HIGH classification.

  Signal                Max pts   Logic
  Structuring             40      5 pts per transaction below threshold
  High-risk country       40      1 pt per 5,000 currency units
  Velocity                20      3 pts per txn/day above threshold

  Level     Score    Recommended action
  HIGH      >= 70    SAR submission to GIIF
  MEDIUM    >= 40    Enhanced Due Diligence
  LOW       < 40     Standard monitoring


## Network Analysis

graph_build.py and graph_analyze.py add a graph layer on top of the
transaction data. Each account becomes a node, each money flow an edge.

Metrics computed per account:

  PageRank        Importance in the network weighted by flow value
  Betweenness     How often account acts as intermediary (layering hub)
  In/Out degree   Consolidation vs distribution pattern
  Community ID    Cluster of accounts exchanging funds internally

Network roles assigned:

  CONSOLIDATOR    High in-degree, high PageRank
                  Funds flowing in from many sources
  DISTRIBUTOR     High out-degree
                  Funds dispersed to many recipients
  HUB             High betweenness
                  Intermediary between clusters - classic layering pattern
  CENTRAL         High PageRank without directional dominance
  STANDARD        No anomalous network pattern

Key finding on synthetic data:
  2 accounts flagged as CENTRAL/HUB by network analysis had NO AML alert
  from transaction monitoring. Graph analysis surfaces blind spots that
  rule-based transaction monitoring cannot detect.


## SQL Analysis - Techniques Demonstrated

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

  pip install faker rich datasette networkx matplotlib scipy
  python generate.py        generate synthetic transactions
  python load.py            load into SQLite
  python queries.py         AML alert detection
  python score.py           risk scoring
  python sar.py             SAR draft generation
  python run_analysis.py    SQL analysis + benchmarks
  python graph_build.py     build transaction graph
  python graph_analyze.py   network metrics + blind spot detection


## Optional: Browser UI

  datasette aml.db --port 8001
  open http://localhost:8001


## Regulatory Basis

  Polish AML Act       Ustawa z dnia 1 marca 2018 r. o przeciwdzialaniu
                       praniu pieniedzy oraz finansowaniu terroryzmu
                       Art. 72 - reporting threshold PLN 15,000

  FATF                 Recommendations 2012 (updated 2023)
                       Typologies: structuring, layering, smurfing

  EU AMLD6             Directive 2018/1673

  EU Delegated Reg.    2016/1675 - high-risk third countries

  GIIF                 Generalny Inspektor Informacji Finansowej
                       Polish FIU - SAR submission authority


## Author

Leszek Gonera
AML Analyst | Data Engineering background
ICA Certified | SQL | Python | RegTech

https://github.com/goneraleszek2-ship-it
