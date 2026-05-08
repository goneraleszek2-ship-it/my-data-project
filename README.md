# AML Transaction Monitoring Pipeline

End-to-end financial crime detection pipeline built in Python and SQL,
exposing results via a REST API. Covers the full AML workflow: from raw
transaction data through typology detection, risk scoring, SAR draft
generation, SQL performance analysis, network graph analysis, to a
queryable HTTP API.

Built as a portfolio project demonstrating the intersection of AML domain
knowledge, data engineering, and backend development skills.


## Architecture

Data Pipeline:

generate.py -> load.py -> queries.py -> score.py -> sar.py
    |              |           |             |          |
 412 synthetic  SQLite     3 FATF       risk score  SAR draft
 transactions   aml.db    typologies    0-100        (.txt)

graph_build.py -> graph_analyze.py
    |                    |
 DiGraph             PageRank, Betweenness
 24 nodes            Community detection
 244 edges           Blind spot detection

REST API (Django + DRF):

POST /api/transactions/analyze/          Risk score for account
GET  /api/transactions/graph/<id>/       Network metrics for account


## Project Structure

generate.py          Synthetic Polish banking data (Faker, IBAN, UUID)
load.py              Loads transactions into SQLite with schema validation
queries.py           AML alert detection - 3 FATF typologies
score.py             Additive risk scoring engine with audit trail
sar.py               SAR draft generator for MEDIUM/HIGH risk accounts
analysis.sql         5 advanced SQL queries with documented methodology
run_analysis.py      Executes SQL queries, shows query plans and benchmarks
graph_build.py       Builds directed transaction graph (NetworkX DiGraph)
graph_analyze.py     PageRank, betweenness centrality, community detection

aml_api/             Django project settings
transactions/        Django app - API views and URL routing
aml_engine/risk.py   Risk score lookup from aml.db
aml_engine/graph.py  Graph metrics lookup from aml.db


## REST API

Start the server:

  cd my-data-project
  source venv/bin/activate
  python manage.py runserver 0.0.0.0:8000

Endpoint 1 - Risk Score:

  POST /api/transactions/analyze/
  Content-Type: application/json
  {"account_id": "PL35494514930239454526246159"}

  Response:
  {
    "account_id": "PL35494514930239454526246159",
    "risk_score": 55,
    "risk_level": "MEDIUM",
    "signals": "structuring (8 txn, +40) | velocity (5 txn/day, +15)"
  }

Endpoint 2 - Graph Metrics:

  GET /api/transactions/graph/PL35494514930239454526246159/

  Response:
  {
    "account_id": "PL35494514930239454526246159",
    "pagerank": 0.031461,
    "betweenness": 0.0455,
    "in_degree": 9,
    "out_degree": 15,
    "community_id": 0,
    "network_role": "STANDARD"
  }


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

Metrics computed per account:

  PageRank        Importance in the network weighted by flow value
  Betweenness     How often account acts as intermediary (layering hub)
  In/Out degree   Consolidation vs distribution pattern
  Community ID    Cluster of accounts exchanging funds internally

Network roles:

  CONSOLIDATOR    High in-degree, high PageRank - funds consolidation
  DISTRIBUTOR     High out-degree - funds dispersed to many recipients
  HUB             High betweenness - intermediary, classic layering pattern
  CENTRAL         High PageRank without directional dominance
  STANDARD        No anomalous network pattern

Key finding: 2 accounts flagged as CENTRAL/HUB by network analysis had
NO alert from transaction monitoring - graph analysis surfaces blind spots
that rule-based monitoring cannot detect.


## SQL Analysis - Techniques Demonstrated

  Query 1   CTE + CASE WHEN        Account profiling and segmentation
  Query 2   RANK() + SUM() OVER    Percentile ranking across population
  Query 3   LAG() + AVG() OVER     7-day moving average, anomaly detection
  Query 4   RANK() OVER            Transaction flow matrix, top pairs
  Query 5   LEFT JOIN + COALESCE   Integrated risk view with score join


## Index Benchmarking Results

  Query                     Before    After     Change
  Account Profile (Q1)      3.60 ms   1.28 ms   -64%
  Ranking/Percentiles (Q2)  1.09 ms   0.97 ms   -11%
  Time Series / LAG (Q3)    1.44 ms   1.54 ms   +7%
  Flow Matrix (Q4)          1.85 ms   1.95 ms   +5%
  JOIN risk_scores (Q5)     1.05 ms   1.19 ms   +13%

Note: regression on small dataset is expected index overhead.
At production scale (millions of rows), indexed queries show 10-100x gains.


## Quickstart - Full Pipeline

  pip install faker rich datasette networkx matplotlib scipy
  python generate.py        generate synthetic transactions
  python load.py            load into SQLite
  python queries.py         AML alert detection
  python score.py           risk scoring
  python sar.py             SAR draft generation
  python run_analysis.py    SQL analysis + benchmarks
  python graph_build.py     build transaction graph
  python graph_analyze.py   network metrics + blind spot detection


## Quickstart - API

  pip install django djangorestframework django-cors-headers
  python manage.py runserver 0.0.0.0:8000


## Optional: Browser UI

  datasette aml.db --port 8001
  open http://localhost:8001


## Tech Stack

  Python 3.13       Core language
  SQLite            Local database (aml.db)
  Django 6.0        REST API framework
  Django REST       API serialization and routing
  Framework
  NetworkX          Graph construction and analysis
  Faker             Synthetic data generation
  Rich              Terminal output formatting
  Datasette         SQL browser UI
  Git               Version control


## Regulatory Basis

  Polish AML Act       Ustawa z dnia 1 marca 2018 r.
                       Art. 72 - reporting threshold PLN 15,000

  FATF                 Recommendations 2012 (updated 2023)
                       Typologies: structuring, layering, smurfing

  EU AMLD6             Directive 2018/1673

  EU Delegated Reg.    2016/1675 - high-risk third countries

  GIIF                 Generalny Inspektor Informacji Finansowej
                       Polish FIU - SAR submission authority


## Roadmap

  [x] Synthetic transaction generation
  [x] SQLite pipeline - Bronze/Silver/Gold layers (Medallion pattern)
  [x] AML typology detection - structuring, velocity, high-risk countries
  [x] Additive risk scoring engine
  [x] SAR draft generator
  [x] Advanced SQL analysis with index benchmarking
  [x] Network graph analysis - PageRank, betweenness, community detection
  [x] REST API - Django + DRF
  [ ] GitHub Actions CI/CD
  [ ] Deployment - Render/Railway
  [ ] PostgreSQL migration
  [ ] Graph metrics endpoint v2 - full account summary


## Author

Leszek Gonera
AML Analyst | Data Engineering background
ICA Certified | SQL | Python | RegTech | Django

https://github.com/goneraleszek2-ship-it
