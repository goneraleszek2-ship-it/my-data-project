
from django.urls import path
from . import views

urlpatterns = [
    path('analyze/', views.analyze_account, name='analyze'),
    path('graph/<str:account_id>/', views.graph_metrics_view, name='graph_metrics'),
]
