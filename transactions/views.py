from rest_framework.decorators import api_view
from rest_framework.response import Response
from aml_engine.risk import get_risk

@api_view(['POST'])
def analyze_account(request):
    account_id = request.data.get('account_id')
    if not account_id:
        return Response({"error": "account_id required"}, status=400)
    try:
        risk_data = get_risk(account_id)
        return Response({
            "account_id": account_id,
            "risk_score": risk_data["score"],
            "risk_level": risk_data["level"],
            "signals": risk_data["signals"]
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)
from aml_engine.graph import get_graph_metrics

@api_view(['GET'])
def graph_metrics_view(request, account_id):
    metrics = get_graph_metrics(account_id)
    if not metrics:
        return Response({"error": "Account not found in graph"}, status=404)
    return Response({"account_id": account_id, **metrics})
