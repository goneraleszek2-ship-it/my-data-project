"""
transactions/views.py — API Views

Trzy endpointy AML:
    POST /api/transactions/analyze/          risk score dla konta
    GET  /api/transactions/graph/<id>/       metryki sieciowe dla konta
    GET  /api/transactions/account/<id>/     pełne podsumowanie (agregacja)

Widoki nie zawierają logiki biznesowej — delegują do aml_engine/.
Wzorzec: Facade — jeden punkt wejścia ukrywający złożoność modułów.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response

from aml_engine.risk import get_risk
from aml_engine.graph import get_graph_metrics


@api_view(['POST'])
def analyze_account(request):
    """
    Zwraca risk score dla konta na podstawie reguł AML.

    Body: {"account_id": "PL35..."}
    Response: {account_id, risk_score, risk_level, signals}
    """
    account_id = request.data.get('account_id')
    if not account_id:
        return Response({"error": "account_id required"}, status=400)
    try:
        risk_data = get_risk(account_id)
        return Response({
            "account_id": account_id,
            "risk_score": risk_data["score"],
            "risk_level": risk_data["level"],
            "signals":    risk_data["signals"]
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
def graph_metrics_view(request, account_id):
    """
    Zwraca metryki sieciowe dla konta (PageRank, betweenness, rola w sieci).

    Response: {account_id, pagerank, betweenness, in_degree,
               out_degree, community_id, network_role}
    404 jeśli konto nie istnieje w grafie.
    """
    try:
        metrics = get_graph_metrics(account_id)
        if not metrics:
            return Response(
                {"error": f"Account {account_id} not found in graph"},
                status=404
            )
        return Response({"account_id": account_id, **metrics})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
def account_summary(request, account_id):
    """
    Agreguje risk score i metryki sieciowe w jeden spójny widok.

    Wzorzec Facade: łączy wyniki get_risk() i get_graph_metrics()
    bez duplikowania logiki biznesowej.

    Response: {account_id, risk{}, network{}, summary}

    Uwaga: konto może mieć niski risk score ale wysoką centralność
    w sieci (blind spot) — summary jawnie to komunikuje.
    """
    try:
        risk    = get_risk(account_id)
        network = get_graph_metrics(account_id)

        # Wykryj blind spot — niski scoring AML ale centralna rola w sieci
        blind_spot = (
            network is not None
            and risk["level"] in ("LOW", "UNKNOWN")
            and network["network_role"] in ("HUB", "CENTRAL", "CONSOLIDATOR")
        )

        if network:
            summary = (
                f"{risk['level']} risk account, "
                f"network role: {network['network_role']}"
            )
            if blind_spot:
                summary += " — BLIND SPOT: escalation recommended"
        else:
            summary = f"{risk['level']} risk account, no network data"

        return Response({
            "account_id": account_id,
            "risk": {
                "score":   risk["score"],
                "level":   risk["level"],
                "signals": risk["signals"]
            },
            "network":    network if network else "no data",
            "blind_spot": blind_spot,
            "summary":    summary
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)
