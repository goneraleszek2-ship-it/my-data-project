# AML Transaction Monitoring Pipeline

End-to-end financial crime detection pipeline built in Python and SQL,
exposing results via a REST API. Covers the full AML workflow: from raw
transaction data through typology detection, risk scoring, SAR draft
generation, SQL performance analysis, network graph analysis, to a
queryable HTTP API backed by PostgreSQL.

Built as a portfolio project demonstrating the intersection of AML domain
knowledge, data engineering, and backend development skills.


## Architecture

Data Pipeline:

generate.py -> load.py -> queries.py -> score.py -> sar.py
    |              |           |             |          |
 412 synthetic  PostgreSQL  3 FATF       risk score  SAR draft
 transactions   aml_db     typologies    0-100        (.txt)

graph_build.py -> graph_analyze.py
    |                    |
 DiGraph             PageRank, Betweenness
 24 nodes            Community detection
 244 edges           Blind spot detection

REST API (Django 6.0 + DRF):

POST /api/transactions/analyze/            Risk score for account
GET  /api/transactions/graph/<id>/         Network metrics for account
GET  /api/transactions/account/<id>/       Full account summary (aggregated)


## Project Structure

generate.py          Synthetic Polish banking data (Faker, IBAN, UUID)
load.py              Loads transactions into PostgreSQL with schema validation
queries.py           AML alert detection - 3 FATF typologies
score.py             Additive risk scoring engine with audit trail
sar.py               SAR draft generator for MEDIUM/HIGH risk accounts
analysis.sql         5 advanced SQL queries with documented methodology
run_analysis.py      Executes SQL queries, shows query plans and benchmarks
graph_build.py       Builds directed transaction graph (NetworkX DiGraph)
graph_analyze.py     PageRank, betweenness centrality, community detection

aml_api/             Django project settings (.env based configuration)
transactions/        Django app - API views and URL routing
aml_engine/risk.py   Risk score lookup from PostgreSQL
aml_engine/graph.py  Graph metrics lookup from PostgreSQL


## REST API

## Live API

Deployed on Render — no setup required:

  POST https://aml-pipeline.onrender.com/api/transactions/analyze/
  GET  https://aml-pipeline.onrender.com/api/transactions/graph/<account_id>/
  GET  https://aml-pipeline.onrender.com/api/transactions/account/<account_id>/

Example — full account summary with blind spot detection:

  curl https://aml-pipeline.onrender.com/api/transactions/account/PL06224328939123573761120204/

Response:
  {
    "account_id": "PL06224328939123573761120204",
    "risk": {"score": 36, "level": "LOW", "signals": "high-risk country (181,637, +36)"},
    "network": {"pagerank": 0.044169, "betweenness": 0.1522, "network_role": "HUB"},
    "blind_spot": true,
    "summary": "LOW risk account, network role: HUB — BLIND SPOT: escalation recommended"
  }

Note: free tier spins down after inactivity — first request may take 30-50 seconds.


Start the server:

  cd my-data-project
  source venv/bin/activate
  python manage.py runserver 0.0.0.0:8000

Endpoint 1 - Risk Score:

  POST /api/transactions/analyze/
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

Endpoint 3 - Full Account Summary (aggregated):

  GET /api/transactions/account/PL06224328939123573761120204/

  Response:
  {
    "account_id": "PL06224328939123573761120204",
    "risk": {
      "score": 36,
      "level": "LOW",
      "signals": "high-risk country (181,637, +36)"
    },
    "network": {
      "pagerank": 0.044169,
      "betweenness": 0.1522,
      "in_degree": 12,
      "out_degree": 15,
      "community_id": 1,
      "network_role": "HUB"
    },
    "summary": "LOW risk account, network role: HUB"
  }

Key finding: this account scores LOW by transaction rules but is the
highest betweenness node in the network (0.1522) with exposure to
high-risk jurisdictions (181k USD via RU/CY). Classic blind spot -
rule-based monitoring misses network-level risk. Escalation required.


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
NO alert from transaction monitoring. Graph analysis surfaces blind spots
that rule-based monitoring cannot detect.


## Architectural Decisions

Separation of concerns:
  aml_engine/risk.py    answers "how risky is this account?" (rules)
  aml_engine/graph.py   answers "what role does it play?" (graph math)
  transactions/views.py orchestrates both - no business logic of its own

Facade pattern:
  GET /account/<id>/ aggregates risk + network into one response.
  Frontend or analyst gets complete picture in a single request.
  Individual endpoints remain available for systems needing partial data.

Granularity vs convenience tradeoff:
  Granular endpoints (/analyze/, /graph/) for systems needing one signal.
  Aggregated endpoint (/account/) for human analysts and dashboards.


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


## Tech Stack

  Python 3.13           Core language
  PostgreSQL 18.2       Production database
  Django 6.0            Web framework
  Django REST Framework API layer
  NetworkX              Graph construction and analysis
  Faker                 Synthetic data generation
  Rich                  Terminal output formatting
  Datasette             SQL browser UI
  python-dotenv         Secrets management
  Git                   Version control


## Security

  Secrets managed via .env (not committed to repository)
  .gitignore covers .env, venv/, __pycache__, *.pyc
  PostgreSQL with dedicated user and password
  ALLOWED_HOSTS configured


## Quickstart - Full Pipeline

  pip install faker rich datasette networkx matplotlib scipy
  python generate.py        generate synthetic transactions
  python load.py            load into PostgreSQL
  python queries.py         AML alert detection
  python score.py           risk scoring
  python sar.py             SAR draft generation
  python run_analysis.py    SQL analysis + benchmarks
  python graph_build.py     build transaction graph
  python graph_analyze.py   network metrics + blind spot detection


## Quickstart - API

  cp .env.example .env      configure database credentials
  pip install django djangorestframework django-cors-headers psycopg2-binary python-dotenv
  python manage.py migrate
  python manage.py runserver 0.0.0.0:8000


## Roadmap

  [x] Synthetic transaction generation
  [x] PostgreSQL pipeline - Bronze/Silver/Gold layers (Medallion pattern)
  [x] AML typology detection - structuring, velocity, high-risk countries
  [x] Additive risk scoring engine
  [x] SAR draft generator
  [x] Advanced SQL analysis with index benchmarking
  [x] Network graph analysis - PageRank, betweenness, community detection
  [x] REST API - Django + DRF (3 endpoints)
  [x] PostgreSQL migration from SQLite
  [x] Secrets management via .env
  [ ] Cross-signal alert - flag LOW risk + HUB network role contradiction
  [ ] GitHub Actions CI/CD
  [ ] Deployment - Render/Railway
  [ ] Unit tests


## Regulatory Basis

  Polish AML Act       Ustawa z dnia 1 marca 2018 r.
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
ICA Certified | SQL | Python | RegTech | Django | PostgreSQL

https://github.com/goneraleszek2-ship-it
