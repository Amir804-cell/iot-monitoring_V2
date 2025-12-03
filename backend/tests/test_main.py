import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import row_to_metrics, app
import psycopg2
import json

MOCK_TIMESTAMP = datetime(2023, 10, 27, 10, 30, 0, tzinfo=timezone.utc)
MOCK_DEVICE_ID = "OLIMEX_POE"
MOCK_DB_ROW_VALUES = [85.5, 1, 20.0, 22.5, 23.0, 21.0, 20.5, 105.0, 95.0, 300.0, 310.0, None, 5.0, 5000, 4800]
MOCK_LATEST_ROW = (MOCK_TIMESTAMP, *MOCK_DB_ROW_VALUES)

class TestBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('backend.main.psycopg2')
    def test_get_devices_success(self, mock_psycopg2):
        mock_conn = mock_psycopg2.connect.return_value
        mock_cur = mock_conn.cursor.return_value
        mock_cur.fetchall.return_value = [("OLIMEX_POE",)]
        
        response = self.client.get("/api/devices")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {"devices": ["OLIMEX_POE"]})

    @patch('backend.main.psycopg2')
    def test_get_latest_data_success(self, mock_psycopg2):
        mock_conn = mock_psycopg2.connect.return_value
        mock_cur = mock_conn.cursor.return_value
        mock_cur.fetchone.return_value = MOCK_LATEST_ROW
        
        response = self.client.get(f"/api/data/latest/{MOCK_DEVICE_ID}")
        self.assertEqual(response.status_code, 200)

    @patch('backend.main.psycopg2')
    def test_query_data_success(self, mock_psycopg2):
        mock_conn = mock_psycopg2.connect.return_value
        mock_cur = mock_conn.cursor.return_value
        mock_cur.fetchall.return_value = [MOCK_LATEST_ROW]
        mock_cur.fetchone.return_value = MOCK_LATEST_ROW
        mock_cur.description = [
            ('ts',), ('heat_exchanger_efficiency',), ('run_mode',), ('outdoor_temp',), 
            ('supply_air_temp',), ('supply_air_setpoint_temp',), ('exhaust_air_temp',), 
            ('extract_air_temp',), ('supply_air_pressure',), ('extract_air_pressure',), 
            ('supply_air_flow',), ('extract_air_flow',), ('extra_extract_air_flow',), 
            ('supply_air_fan_runtime',), ('extract_air_fan_runtime',)
        ]
        mock_conn.commit.return_value = None
        
        query_body = {"device_id": MOCK_DEVICE_ID, "start_time": "2023-10-27T10:00:00Z", "end_time": "2023-10-27T11:00:00Z", "limit": 100}
        response = self.client.post("/api/data/query", json=query_body)
        self.assertEqual(response.status_code, 200)

    @patch('backend.main.psycopg2.connect')
    def test_error_handling(self, mock_connect):
        """Test 500 status code on database failure"""
        mock_conn = mock_connect.return_value
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_conn.cursor.side_effect = psycopg2.OperationalError("DB is offline")
        
        response = self.client.get("/api/devices")
        self.assertEqual(response.status_code, 500)  # ✅ Matches your app behavior

    def test_row_to_metrics_conversion(self):
        ts_local = datetime(2024, 1, 1, 12, 0, 0)
        metrics = row_to_metrics(ts_local, MOCK_DB_ROW_VALUES)
        self.assertEqual(len(metrics), 14)
        self.assertEqual(metrics[0]["metric_value"], 85.5)

if __name__ == '__main__':
    unittest.main()
