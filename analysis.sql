-- =============================================================================
-- analysis.sql — Advanced AML SQL Analysis
-- Database: aml.db (SQLite)
-- Author: Leszek Gonera
--
-- Cel: demonstracja zaawansowanych technik SQL w kontekście AML:
-- CTEs, window functions, ranking, analiza szeregów czasowych.
-- Każde zapytanie rozwiązuje konkretny problem analityczny.
-- =============================================================================


-- =============================================================================
-- ZAPYTANIE 1: Profil aktywności kont
--
-- Cel: zbudować pełny profil każdego konta w jednym zapytaniu.
-- Techniki: CTE, agregacje wielowymiarowe, CASE WHEN.
--
-- Dlaczego CTE a nie subquery?
-- CTE (WITH) pozwala nazwać każdy etap obliczeń — kod czyta się
-- jak opis procesu analitycznego, nie jak zagnieżdżone nawiasy.
-- =============================================================================

WITH account_profile AS (

    -- Krok 1: podstawowe statystyki per konto
    SELECT
        account_from,
        COUNT(*)                        AS total_txn,
        ROUND(SUM(amount), 2)           AS total_amount,
        ROUND(AVG(amount), 2)           AS avg_amount,
        ROUND(MIN(amount), 2)           AS min_amount,
        ROUND(MAX(amount), 2)           AS max_amount,
        COUNT(DISTINCT currency)        AS currency_count,
        COUNT(DISTINCT country)         AS country_count,
        COUNT(DISTINCT channel)         AS channel_count,
        MIN(DATE(timestamp))            AS first_txn_date,
        MAX(DATE(timestamp))            AS last_txn_date,

        -- Liczba dni aktywności (zakres dat)
        JULIANDAY(MAX(timestamp)) -
        JULIANDAY(MIN(timestamp))       AS active_days

    FROM transactions
    GROUP BY account_from

),
account_classified AS (

    -- Krok 2: klasyfikacja profilu na podstawie statystyk
    -- CASE WHEN pozwala budować czytelne reguły bez zagnieżdżonych IFów
    SELECT
        *,
        CASE
            WHEN total_amount > 100000              THEN 'HIGH VALUE'
            WHEN total_amount > 50000               THEN 'MEDIUM VALUE'
            ELSE                                         'STANDARD'
        END AS value_segment,

        CASE
            WHEN active_days > 0
            THEN ROUND(total_txn * 1.0 / active_days, 2)
            ELSE total_txn
        END AS avg_txn_per_day

    FROM account_profile

)

-- Krok 3: wynik końcowy posortowany po wartości obrotów
SELECT
    account_from,
    total_txn,
    total_amount,
    avg_amount,
    value_segment,
    avg_txn_per_day,
    currency_count,
    country_count,
    first_txn_date,
    last_txn_date
FROM account_classified
ORDER BY total_amount DESC;


-- =============================================================================
-- ZAPYTANIE 2: Ranking kont z percentylami
--
-- Cel: uszeregować konta według wartości obrotów i pokazać
-- ich pozycję względem całej populacji.
-- Techniki: Window functions — RANK(), SUM() OVER, ROUND().
--
-- Window functions obliczają wartości "przez okno" całego zbioru
-- bez GROUP BY — każdy wiersz zachowuje swój kontekst.
-- =============================================================================

WITH account_totals AS (

    -- Krok 1: agregacja obrotów per konto
    SELECT
        account_from,
        COUNT(*)                AS txn_count,
        ROUND(SUM(amount), 2)   AS total_amount
    FROM transactions
    GROUP BY account_from

),
ranked AS (

    -- Krok 2: ranking i udział procentowy przez window functions
    SELECT
        account_from,
        txn_count,
        total_amount,

        -- RANK() numeruje wiersze według wartości — ex aequo dostają tę samą pozycję
        RANK() OVER (ORDER BY total_amount DESC)    AS amount_rank,

        -- Udział procentowy w łącznych obrotach całej populacji kont
        -- SUM() OVER () bez PARTITION BY = suma dla całego zbioru
        ROUND(
            100.0 * total_amount / SUM(total_amount) OVER (),
        2)                                          AS pct_of_total,

        -- Skumulowany udział — ile % obrotów skupia top N kont
        ROUND(
            100.0 * SUM(total_amount) OVER (
                ORDER BY total_amount DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) / SUM(total_amount) OVER (),
        2)                                          AS cumulative_pct

    FROM account_totals

)

-- Krok 3: wynik z interpretacją pozycji
SELECT
    account_from,
    txn_count,
    total_amount,
    amount_rank,
    pct_of_total    || '%'  AS share,
    cumulative_pct  || '%'  AS cumulative_share
FROM ranked
ORDER BY amount_rank;


-- =============================================================================
-- ZAPYTANIE 3: Analiza czasowa — aktywność dzienna z trendem
--
-- Cel: zobaczyć jak zmienia się wolumen transakcji w czasie
-- i wykryć dni anomalnej aktywności.
-- Techniki: LAG(), AVG() OVER z oknem kroczącym, strftime().
--
-- LAG() pozwala porównać bieżący wiersz z poprzednim —
-- bez self-JOIN i bez subquery.
-- =============================================================================

WITH daily_volume AS (

    -- Krok 1: agregacja dzienna
    SELECT
        DATE(timestamp)             AS txn_date,
        COUNT(*)                    AS daily_txn,
        ROUND(SUM(amount), 2)       AS daily_amount
    FROM transactions
    GROUP BY DATE(timestamp)

),
daily_with_trend AS (

    -- Krok 2: dodaj trend przez window functions
    SELECT
        txn_date,
        daily_txn,
        daily_amount,

        -- Poprzedni dzień przez LAG() — bez self-JOIN
        LAG(daily_amount) OVER (ORDER BY txn_date)  AS prev_day_amount,

        -- Zmiana dzień do dnia w PLN
        daily_amount -
        LAG(daily_amount) OVER (ORDER BY txn_date)  AS day_over_day_change,

        -- Kroczące 7-dniowe średnie obrotów — wygładza szumy
        ROUND(AVG(daily_amount) OVER (
            ORDER BY txn_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2)                                        AS moving_avg_7d

    FROM daily_volume

)

-- Krok 3: flaguj dni gdzie obroty przekraczają 2x średnią kroczącą
SELECT
    txn_date,
    daily_txn,
    daily_amount,
    moving_avg_7d,
    day_over_day_change,
    CASE
        WHEN daily_amount > 2 * moving_avg_7d THEN 'ANOMALY'
        ELSE 'NORMAL'
    END AS day_status
FROM daily_with_trend
ORDER BY txn_date;


-- =============================================================================
-- ZAPYTANIE 4: Macierz przepływów między kontami
--
-- Cel: zidentyfikować pary kont z największymi wzajemnymi przepływami —
-- podstawa do analizy sieci powiązań (network analysis).
-- Techniki: self-aggregation, CASE dla kierunku przepływu.
--
-- W realu to wejście do algorytmów grafowych (np. PageRank w Neo4j).
-- Tu pokazujemy ile możemy wyciągnąć czystym SQL.
-- =============================================================================

WITH flow_matrix AS (

    -- Krok 1: agregacja przepływów per para kont
    SELECT
        account_from,
        account_to,
        COUNT(*)                AS txn_count,
        ROUND(SUM(amount), 2)   AS total_flow,
        ROUND(AVG(amount), 2)   AS avg_flow,
        MIN(DATE(timestamp))    AS first_flow,
        MAX(DATE(timestamp))    AS last_flow
    FROM transactions
    WHERE account_from != account_to   -- wyklucz transakcje własne
    GROUP BY account_from, account_to

),
flow_ranked AS (

    -- Krok 2: ranking par według wartości przepływów
    SELECT
        *,
        RANK() OVER (ORDER BY total_flow DESC) AS flow_rank
    FROM flow_matrix

)

-- Krok 3: top 10 par z największymi przepływami
SELECT
    flow_rank,
    account_from,
    account_to,
    txn_count,
    total_flow,
    avg_flow,
    first_flow,
    last_flow
FROM flow_ranked
WHERE flow_rank <= 10
ORDER BY flow_rank;


-- =============================================================================
-- ZAPYTANIE 5: Integracja z risk_scores — pełny obraz konta
--
-- Cel: połączyć dane transakcyjne z wynikami scoringu w jeden widok.
-- Techniki: JOIN z CTE, COALESCE dla kont bez score.
--
-- To jest widok który dostałby analityk AML przed rozmową z klientem —
-- wszystko w jednym miejscu.
-- =============================================================================

WITH txn_summary AS (

    -- Krok 1: statystyki transakcyjne
    SELECT
        account_from,
        COUNT(*)                            AS total_txn,
        ROUND(SUM(amount), 2)               AS total_amount,
        COUNT(DISTINCT country)             AS countries_used,
        COUNT(DISTINCT currency)            AS currencies_used,
        SUM(CASE WHEN country IN
            ('IR','KP','RU','BY','CY')
            THEN 1 ELSE 0 END)              AS high_risk_txn_count
    FROM transactions
    GROUP BY account_from

)

-- Krok 2: JOIN z tabelą risk_scores
-- COALESCE obsługuje konta które nie wystąpiły w żadnym alercie
SELECT
    t.account_from,
    t.total_txn,
    t.total_amount,
    t.countries_used,
    t.currencies_used,
    t.high_risk_txn_count,
    COALESCE(r.score, 0)            AS risk_score,
    COALESCE(r.level, 'NO ALERT')   AS risk_level,
    COALESCE(r.signals, '-')        AS signals
FROM txn_summary t
LEFT JOIN risk_scores r
    ON t.account_from = r.account
ORDER BY risk_score DESC, total_amount DESC;
