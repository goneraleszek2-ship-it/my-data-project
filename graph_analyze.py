# graph_analyze.py — Analiza grafu przepływów finansowych
#
# Metryki:
#   Degree centrality, In-degree, Out-degree, PageRank, Betweenness
#
# Wynik:
#   Tabela graph_metrics w PostgreSQL + podsumowanie w terminalu

import os
import pickle
import psycopg2
import networkx as nx
from collections import Counter
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

load_dotenv()
console = Console()


def load_graph(path="graph.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)


def _get_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )


def compute_metrics(G):
    console.print("[cyan]Obliczanie degree centrality...[/cyan]")
    degree_centrality = nx.degree_centrality(G)

    console.print("[cyan]Obliczanie in/out degree...[/cyan]")
    in_degree  = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    console.print("[cyan]Obliczanie PageRank...[/cyan]")
    pagerank = nx.pagerank(G, weight='weight', alpha=0.85)

    console.print("[cyan]Obliczanie betweenness centrality...[/cyan]")
    betweenness = nx.betweenness_centrality(G, weight='weight', normalized=True)

    console.print("[cyan]Wykrywanie spolecznosci (clustrow)...[/cyan]")
    G_undirected  = G.to_undirected()
    communities   = nx.community.greedy_modularity_communities(G_undirected)
    community_map = {}
    for i, community in enumerate(communities):
        for node in community:
            community_map[node] = i

    return {
        'degree_centrality': degree_centrality,
        'in_degree':         in_degree,
        'out_degree':        out_degree,
        'pagerank':          pagerank,
        'betweenness':       betweenness,
        'community':         community_map
    }


def classify_node(in_deg, out_deg, pagerank, betweenness):
    if in_deg > out_deg * 2 and pagerank > 0.06:
        return "CONSOLIDATOR"
    if out_deg > in_deg * 2 and pagerank > 0.04:
        return "DISTRIBUTOR"
    if betweenness > 0.15:
        return "HUB"
    if pagerank > 0.07:
        return "CENTRAL"
    return "STANDARD"


def save_metrics(G, metrics):
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
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

        cur.executemany("""
            INSERT INTO graph_metrics
                (account, degree_centrality, in_degree, out_degree,
                 pagerank, betweenness, community_id, network_role,
                 risk_score, risk_level)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (account)
            DO UPDATE SET
                degree_centrality = EXCLUDED.degree_centrality,
                in_degree         = EXCLUDED.in_degree,
                out_degree        = EXCLUDED.out_degree,
                pagerank          = EXCLUDED.pagerank,
                betweenness       = EXCLUDED.betweenness,
                community_id      = EXCLUDED.community_id,
                network_role      = EXCLUDED.network_role,
                risk_score        = EXCLUDED.risk_score,
                risk_level        = EXCLUDED.risk_level
        """, rows)

        conn.commit()
        return rows
    finally:
        conn.close()


def print_results(rows):
    console.rule("[bold cyan]GRAPH ANALYSIS — RESULTS")
    rows_sorted = sorted(rows, key=lambda x: x[4], reverse=True)

    t = Table(box=box.SIMPLE)
    for col in ["Konto", "Role", "PageRank", "Betweenness", "In", "Out", "Cluster", "AML Level"]:
        t.add_column(col)

    for row in rows_sorted:
        account, deg, in_d, out_d, pr, bw, comm, role, score, level = row

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

    console.rule("[bold]Network Role Distribution")
    roles = Counter(r[7] for r in rows)
    for role, count in roles.most_common():
        console.print(f"  {role:<15} {count} kont")

    console.rule("[bold red]Cross-signal Findings")
    blind_spots = [r for r in rows if r[7] in ('HUB', 'CONSOLIDATOR', 'CENTRAL')
                   and r[9] == 'NO ALERT']
    if blind_spots:
        console.print(f"[yellow]Konta z rola sieciowa HIGH ale bez alertu AML: {len(blind_spots)}[/yellow]")
        for r in blind_spots:
            console.print(f"  {r[0][:30]}...  rola: {r[7]}  PageRank: {r[4]:.4f}")
    else:
        console.print("[green]Brak blind spots.[/green]")


if __name__ == "__main__":
    console.print("[cyan]Ladowanie grafu...[/cyan]")
    G = load_graph()
    console.print(f"Graf: {G.number_of_nodes()} wezlow, {G.number_of_edges()} krawedzi")

    metrics = compute_metrics(G)
    rows    = save_metrics(G, metrics)

    print_results(rows)
    console.print("\n[green]Metryki zapisane do graph_metrics w PostgreSQL[/green]")
