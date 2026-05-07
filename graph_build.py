# graph_build.py — Budowanie grafu przepływów finansowych
#
# Co robi ten moduł:
#   Czyta transakcje z bazy danych i buduje graf skierowany (DiGraph).
#   Węzeł = konto bankowe
#   Krawędź = przepływ pieniędzy między kontami
#   Waga krawędzi = łączna kwota transakcji
#
# Wynik:
#   Plik graph.pkl gotowy do analizy przez graph_analyze.py

import sqlite3
import pickle
import networkx as nx
from rich.console import Console

console = Console()

def load_transactions(db_path="aml.db"):
    # Pobierz wszystkie transakcje między różnymi kontami
    # Wykluczamy transakcje własne (account_from = account_to)
    con = sqlite3.connect(db_path)
    rows = con.execute("""
        SELECT
            account_from,
            account_to,
            COUNT(*)              AS txn_count,
            ROUND(SUM(amount), 2) AS total_amount,
            ROUND(AVG(amount), 2) AS avg_amount
        FROM transactions
        WHERE account_from != account_to
        GROUP BY account_from, account_to
    """).fetchall()
    con.close()
    return rows

def build_graph(transactions):
    # Tworzymy graf skierowany — kierunek krawędzi = kierunek przepływu
    # DiGraph zamiast Graph bo A->B to nie to samo co B->A w AML
    G = nx.DiGraph()

    for account_from, account_to, txn_count, total_amount, avg_amount in transactions:

        # Każde konto staje się węzłem automatycznie przy dodaniu krawędzi
        # Atrybuty krawędzi przechowują kontekst finansowy
        G.add_edge(
            account_from,
            account_to,
            weight=total_amount,      # waga = łączna kwota (używana w wizualizacji)
            txn_count=txn_count,      # liczba transakcji na tej parze
            avg_amount=avg_amount     # średnia kwota pojedynczej transakcji
        )

    return G

def attach_risk_scores(G, db_path="aml.db"):
    # Dołącz wyniki scoringu AML do węzłów grafu
    # Konta bez alertu otrzymują score=0, level='NO ALERT'
    con = sqlite3.connect(db_path)
    scores = con.execute("""
        SELECT account, score, level FROM risk_scores
    """).fetchall()
    con.close()

    # Najpierw ustaw domyślne wartości dla wszystkich węzłów
    for node in G.nodes():
        G.nodes[node]['risk_score'] = 0
        G.nodes[node]['risk_level'] = 'NO ALERT'

    # Nadpisz dla kont które mają alert
    for account, score, level in scores:
        if account in G.nodes:
            G.nodes[account]['risk_score'] = score
            G.nodes[account]['risk_level'] = level

    return G

def save_graph(G, path="graph.pkl"):
    # Zapisz graf jako plik binarny (pickle)
    # Pickle zachowuje wszystkie atrybuty węzłów i krawędzi
    with open(path, "wb") as f:
        pickle.dump(G, f)

def print_summary(G):
    console.rule("[bold cyan]GRAPH BUILD — SUMMARY")

    # Podstawowe statystyki grafu
    console.print(f"Węzły (konta)  : [bold]{G.number_of_nodes()}[/bold]")
    console.print(f"Krawędzie      : [bold]{G.number_of_edges()}[/bold]")

    # Gęstość grafu — 1.0 oznaczałoby że każde konto wysyła do każdego
    density = nx.density(G)
    console.print(f"Gęstość grafu  : [bold]{density:.4f}[/bold]  (0=rozproszony, 1=pełny)")

    # Znajdź węzły z największą liczbą połączeń (hubów sieci)
    # degree = liczba krawędzi wchodzących + wychodzących
    top_by_degree = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:5]
    console.print("\n[bold]Top 5 węzłów po liczbie połączeń:[/bold]")
    for account, degree in top_by_degree:
        risk = G.nodes[account]['risk_level']
        console.print(f"  {account[:30]}...  połączeń: {degree}  ryzyko: {risk}")

    # Konta z alertem AML
    flagged = [(n, d) for n, d in G.nodes(data=True) if d['risk_level'] != 'NO ALERT']
    console.print(f"\n[bold red]Konta z alertem AML w grafie: {len(flagged)}[/bold red]")
    for account, data in flagged:
        console.print(f"  {account[:30]}...  score: {data['risk_score']}  level: {data['risk_level']}")

if __name__ == "__main__":
    console.print("[cyan]Ładowanie transakcji z bazy...[/cyan]")
    transactions = load_transactions()
    console.print(f"Załadowano {len(transactions)} par kont z przepływami.")

    console.print("[cyan]Budowanie grafu...[/cyan]")
    G = build_graph(transactions)

    console.print("[cyan]Dołączanie risk scores...[/cyan]")
    G = attach_risk_scores(G)

    console.print("[cyan]Zapisywanie grafu...[/cyan]")
    save_graph(G)

    print_summary(G)
    console.print("\n[green]Graf zapisany do graph.pkl — gotowy dla graph_analyze.py[/green]")
	
	
