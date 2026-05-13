"""
transactions/tests.py — Unit & Integration Tests

Trzy poziomy testów:
    1. Unit — logika aml_engine (mock bazy danych)
    2. API  — endpointy Django REST Framework
    3. Edge — przypadki brzegowe (brak konta, pusty input)
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


# =============================================================================
# POZIOM 1 — Unit Tests: aml_engine
# Testujemy logikę get_risk() i get_graph_metrics() bez prawdziwej bazy.
# Używamy mock — symulujemy odpowiedź bazy zamiast jej odpytywać.
# =============================================================================

class TestGetRisk(TestCase):

    @patch('aml_engine.risk._get_connection')
    def test_known_account_returns_score(self, mock_conn):
        """Konto z danymi w bazie powinno zwrócić score, level i signals."""
        # Symuluj odpowiedź bazy — jedna kolumna: (score, level, signals)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (55, 'MEDIUM', 'structuring | velocity')
        mock_conn.return_value.__enter__ = lambda s: s
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close = MagicMock()

        from aml_engine.risk import get_risk
        result = get_risk('PL35494514930239454526246159')

        self.assertEqual(result['score'], 55)
        self.assertEqual(result['level'], 'MEDIUM')
        self.assertIn('structuring', result['signals'])

    @patch('aml_engine.risk._get_connection')
    def test_unknown_account_returns_unknown(self, mock_conn):
        """Konto bez danych powinno zwrócić score=0 i level=UNKNOWN."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close = MagicMock()

        from aml_engine.risk import get_risk
        result = get_risk('NONEXISTENT_ACCOUNT')

        self.assertEqual(result['score'], 0)
        self.assertEqual(result['level'], 'UNKNOWN')

    @patch('aml_engine.risk._get_connection')
    def test_account_id_stripped(self, mock_conn):
        """account_id z spacją powinno być oczyszczone przed zapytaniem."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close = MagicMock()

        from aml_engine.risk import get_risk
        # Spacja na początku — częsty błąd w danych wejściowych
        get_risk('  PL35494514930239454526246159  ')
        call_args = mock_cursor.execute.call_args[0][1]
        self.assertEqual(call_args[0], 'PL35494514930239454526246159')


class TestGetGraphMetrics(TestCase):

    @patch('aml_engine.graph._get_connection')
    def test_known_account_returns_metrics(self, mock_conn):
        """Konto z danymi grafowymi powinno zwrócić wszystkie metryki."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            0.031461, 0.0455, 9, 15, 0, 'STANDARD'
        )
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close = MagicMock()

        from aml_engine.graph import get_graph_metrics
        result = get_graph_metrics('PL35494514930239454526246159')

        self.assertIsNotNone(result)
        self.assertIn('pagerank', result)
        self.assertIn('network_role', result)
        self.assertEqual(result['network_role'], 'STANDARD')

    @patch('aml_engine.graph._get_connection')
    def test_unknown_account_returns_none(self, mock_conn):
        """Konto bez danych grafowych powinno zwrócić None."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close = MagicMock()

        from aml_engine.graph import get_graph_metrics
        result = get_graph_metrics('NONEXISTENT')

        self.assertIsNone(result)


# =============================================================================
# POZIOM 2 — API Tests: endpointy Django
# Testujemy HTTP responses przez APIClient.
# Mock na aml_engine żeby testy nie wymagały bazy danych.
# =============================================================================

class TestAnalyzeEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    @patch('transactions.views.get_risk')
    def test_valid_account_returns_200(self, mock_risk):
        """POST z poprawnym account_id powinien zwrócić 200."""
        mock_risk.return_value = {
            'score': 55,
            'level': 'MEDIUM',
            'signals': 'structuring | velocity'
        }
        response = self.client.post(
            '/api/transactions/analyze/',
            {'account_id': 'PL35494514930239454526246159'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['risk_score'], 55)
        self.assertEqual(response.data['risk_level'], 'MEDIUM')

    def test_missing_account_id_returns_400(self):
        """POST bez account_id powinien zwrócić 400."""
        response = self.client.post(
            '/api/transactions/analyze/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)


class TestGraphEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    @patch('transactions.views.get_graph_metrics')
    def test_known_account_returns_200(self, mock_graph):
        """GET z kontem w grafie powinien zwrócić 200."""
        mock_graph.return_value = {
            'pagerank': 0.031,
            'betweenness': 0.045,
            'in_degree': 9,
            'out_degree': 15,
            'community_id': 0,
            'network_role': 'STANDARD'
        }
        response = self.client.get(
            '/api/transactions/graph/PL35494514930239454526246159/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('pagerank', response.data)

    @patch('transactions.views.get_graph_metrics')
    def test_unknown_account_returns_404(self, mock_graph):
        """GET z kontem bez danych grafowych powinien zwrócić 404."""
        mock_graph.return_value = None
        response = self.client.get(
            '/api/transactions/graph/NONEXISTENT/'
        )
        self.assertEqual(response.status_code, 404)


class TestAccountSummaryEndpoint(TestCase):

    def setUp(self):
        self.client = APIClient()

    @patch('transactions.views.get_graph_metrics')
    @patch('transactions.views.get_risk')
    def test_blind_spot_detected(self, mock_risk, mock_graph):
        """LOW risk + HUB role powinno triggerować blind_spot=True."""
        mock_risk.return_value = {
            'score': 36,
            'level': 'LOW',
            'signals': 'high-risk country'
        }
        mock_graph.return_value = {
            'pagerank': 0.044,
            'betweenness': 0.152,
            'in_degree': 12,
            'out_degree': 15,
            'community_id': 1,
            'network_role': 'HUB'
        }
        response = self.client.get(
            '/api/transactions/account/PL06224328939123573761120204/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['blind_spot'])
        self.assertIn('BLIND SPOT', response.data['summary'])

    @patch('transactions.views.get_graph_metrics')
    @patch('transactions.views.get_risk')
    def test_medium_risk_no_blind_spot(self, mock_risk, mock_graph):
        """MEDIUM risk + STANDARD role nie powinno triggerować blind_spot."""
        mock_risk.return_value = {
            'score': 55,
            'level': 'MEDIUM',
            'signals': 'structuring'
        }
        mock_graph.return_value = {
            'pagerank': 0.031,
            'betweenness': 0.045,
            'in_degree': 9,
            'out_degree': 15,
            'community_id': 0,
            'network_role': 'STANDARD'
        }
        response = self.client.get(
            '/api/transactions/account/PL35494514930239454526246159/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['blind_spot'])
