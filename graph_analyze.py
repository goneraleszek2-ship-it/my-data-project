# graph_analyze.py — Analiza grafu przepływów finansowych
#
# Co robi ten moduł:
#   Ładuje graf z graph.pkl i oblicza metryki sieciowe dla każdego konta.
#   Każda metryka odpowiada na inne pytanie analityczne.
#
# Metryki:
#   Degree centrality   — ile kont jest bezpośrednio połączonych z danym kontem?
#   In-degree           — ile kont wysyła DO tego konta? (potencjalny cel konsolidacji)
#   Out-degree          — ile kont otrzymuje Z tego konta? (potencjalny dystrybutor)
#   PageRank            — jak ważne jest konto w całej sieci? (uwzględnia wagę połączeń)
#   Betweenness         — jak często konto leży na ścieżce między innymi? (pośrednik)
#
# Wynik:
#   Tabela graph_metrics w aml.db + podsumowanie w terminalu

import pickle
import sqlite3
import networkx as nx
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def load_graph(path="graph.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)

def compute_metrics(G):
    console.print("[cyan]Obliczanie degree centrality...[/cyan]")
    # Degree centrality — odsetek wszystkich możliwych połączeń które konto posiada
    # 1.0 = połączone z każdym innym kontem w sieci
    degree_centrality = nx.degree_centrality(G)

    console.print("[cyan]Obliczanie in/out degree...[/cyan]")
    # In-degree — liczba kont które wysyłają DO tego konta
    # Wysokie in-degree przy niskim out-degree = konto konsolidujące (smurfing target)
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    console.print("[cyan]Obliczanie PageRank...[/cyan]")
    # PageRank — algorytm Google zaadaptowany do AML
    # Konto jest ważne jeśli otrzymuje środki od innych ważnych kont
    # weight='weight' = uwzględnia kwoty transakcji, nie tylko ich liczbę
    pagerank = nx.pagerank(G, weight='weight', alpha=0.85)

    console.print("[cyan]Obliczanie betweenness centrality...[/cyan]")
    # Betweenness — jak często konto leży na najkrótszej ścieżce między innymi?
    # Wysoki betweenness = pośrednik w sieci (layering hub)
    # normalized=True = wynik 0-1 niezależnie od rozmiaru grafu
    betweenness = nx.betweenness_centrality(G, weight='weight', normalized=True)

    console.print("[cyan]Wykrywanie społeczności (clustrów)...[/cyan]")
    # Wykrywanie społeczności na grafie nieskierowanym
    # Społeczność = grupa kont która intensywnie wymienia środki między sobą
    # W AML: clustry mogą wskazywać na zorganizowane grupy przestępcze
    G_undirected = G.to_undirected()
    communities = nx.community.greedy_modularity_communities(G_undirected)

    # Przypisz numer clustra do każdego węzła
    community_map = {}
    for i, community in enumerate(communities):
        for node in community:
            community_map[node] = i

    return {
        'degree_centrality': degree_centrality,
        'in_degree': in_degree,
        'out_degree': out_degree,
        'pagerank': pagerank,
        'betweenness': betweenness,
        'community': community_map
    }

def classify_node(in_deg, out_deg, pagerank, betweenness):
    # Klasyfikacja roli konta w sieci na podstawie kombinacji metryk
    # Te wzorce odpowiadają typologiom etapów prania pieniędzy

    if in_deg > out_deg * 2 and pagerank > 0.06:
        # Dużo przychodzi, mało wychodzi, wysoki PageRank
        # = konto konsolidujące środki z wielu źródeł (placement/integration)
        return "CONSOLIDATOR"

    if out_deg > in_deg * 2 and pagerank > 0.04:
        # Dużo wychodzi, mało przychodzi
        # = konto dystrybuujące środki do wielu odbiorców (layering)
        return "DISTRIBUTOR"

    if betweenness > 0.15:
        # Często leży na ścieżce między innymi kontami
        # = pośrednik w sieci, klasyczny layering hub
        return "HUB"

    if pagerank > 0.07:
        # Wysoki PageRank bez dominującego kierunku
        # = konto centralne w sieci, wymaga uwagi
        return "CENTRAL"

    return "STANDARD"

def save_metrics(G, metrics, db_path="aml.db"):
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS graph_metrics (
            account           TEXT PRIMARY KEY,
            degree_centrality REAL,
            in_degree         INTEGER,
            out_degree        INTEGER,
            pagerank          REAL,
            betweenness       REAL,
            community_id      INTEGER,
            network_role      TEXT,
            risk_score        INTEGER,
            risk_level        TEXT
        )
    """)

    rows = []
    for node in G.nodes():
        role = classify_node(
            metrics['in_degree'][node],
            metrics['out_degree'][node],
            metrics['pagerank'][node],
            metrics['betweenness'][node]
        )
        rows.append((
            node,
            round(metrics['degree_centrality'][node], 4),
            metrics['in_degree'][node],
            metrics['out_degree'][node],
            round(metrics['pagerank'][node], 6),
            round(metrics['betweenness'][node], 4),
            metrics['community'][node],
            role,
            G.nodes[node]['risk_score'],
            G.nodes[node]['risk_level']
        ))

    con.executemany("""
        INSERT OR REPLACE INTO graph_metrics VALUES
        (?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()
    con.close()
    return rows

def print_results(rows):
    console.rule("[bold cyan]GRAPH ANALYSIS — RESULTS")

    # Sortuj po PageRank — najważniejsze konta w sieci na górze
    rows_sorted = sorted(rows, key=lambda x: x[4], reverse=True)

    t = Table(box=box.SIMPLE)
    t.add_column("Konto", style="cyan")
    t.add_column("Role", style="bold")
    t.add_column("PageRank")
    t.add_column("Betweenness")
    t.add_column("In")
    t.add_column("Out")
    t.add_column("Cluster")
    t.add_column("AML Level", style="bold")

    for row in rows_sorted:
        account, deg, in_d, out_d, pr, bw, comm, role, score, level = row

        # Kolorowanie na podstawie roli i poziomu ryzyka
        role_colored = {
            "CONSOLIDATOR": "[red]CONSOLIDATOR[/red]",
            "DISTRIBUTOR":  "[yellow]DISTRIBUTOR[/yellow]",
            "HUB":          "[magenta]HUB[/magenta]",
            "CENTRAL":      "[blue]CENTRAL[/blue]",
            "STANDARD":     "STANDARD"
        }.get(role, role)

        level_colored = {
            "HIGH":     "[red]HIGH[/red]",
            "MEDIUM":   "[yellow]MEDIUM[/yellow]",
            "LOW":      "[green]LOW[/green]",
            "NO ALERT": "[dim]NO ALERT[/dim]"
        }.get(level, level)

        t.add_row(
            account[:22] + "...",
            role_colored,
            str(round(pr, 4)),
            str(round(bw, 4)),
            str(in_d),
            str(out_d),
            str(comm),
            level_colored
        )

    console.print(t)

    # Podsumowanie ról
    console.rule("[bold]Network Role Distribution")
    from collections import Counter
    roles = Counter(r[7] for r in rows)
    for role, count in roles.most_common():
        console.print(f"  {role:<15} {count} kont")

    # Kluczowe ostrzeżenia — konta które są hubami sieci ale nie mają alertu AML
    console.rule("[bold red]Cross-signal Findings")
    blind_spots = [r for r in rows if r[7] in ('HUB','CONSOLIDATOR','CENTRAL')
                   and r[9] == 'NO ALERT']
    if blind_spots:
        console.print(f"[yellow]Konta z rolą sieciową HIGH ale bez alertu AML: {len(blind_spots)}[/yellow]")
        for r in blind_spots:
            console.print(f"  {r[0][:30]}...  rola: {r[7]}  PageRank: {r[4]:.4f}")
    else:
        console.print("[green]Brak blind spots — scoring AML pokrywa węzły sieciowe.[/green]")

if __name__ == "__main__":
    console.print("[cyan]Ładowanie grafu...[/cyan]")
    G = load_graph()
    console.print(f"Graf: {G.number_of_nodes()} węzłów, {G.number_of_edges()} krawędzi")

    metrics = compute_metrics(G)
    rows = save_metrics(G, metrics)

    print_results(rows)
    console.print("\n[green]Metryki zapisane do graph_metrics w aml.db[/green]")
    console.print("[green]Gotowy dla graph_visualize.py[/green]")
