import unittest
from unittest.mock import patch, MagicMock
import psycopg2
import json
import datetime

MOCK_NOW = datetime.datetime(2025, 12, 2, 9, 30, 0)

class TestMqttIngestor(unittest.TestCase):

    @patch('backend.mqtt_ingestor.time.sleep')
    @patch('backend.mqtt_ingestor.psycopg2')
    @patch('backend.mqtt_ingestor.mqtt')  # FIXED: Correct original path
    @patch('backend.mqtt_ingestor.datetime.datetime')
    def test_create_db_connection_retries(self, mock_dt, mock_mqtt, mock_psycopg2, mock_sleep):
        mock_dt.now.return_value = MOCK_NOW
        mock_psycopg2.OperationalError = psycopg2.OperationalError
        mock_conn = MagicMock()
        mock_psycopg2.connect.side_effect = [
            psycopg2.OperationalError("Fail 1"),
            psycopg2.OperationalError("Fail 2"),
            mock_conn
        ]
        
        import backend.mqtt_ingestor
        backend.mqtt_ingestor.create_db_connection(max_retries=3)
        self.assertEqual(mock_psycopg2.connect.call_count, 3)

    @patch('backend.mqtt_ingestor.time.sleep')
    @patch('backend.mqtt_ingestor.psycopg2')
    @patch('backend.mqtt_ingestor.mqtt')
    @patch('backend.mqtt_ingestor.datetime.datetime')
    def test_create_table_success(self, mock_dt, mock_mqtt, mock_psycopg2, mock_sleep):
        mock_dt.now.return_value = MOCK_NOW
        import backend.mqtt_ingestor
        ingestor = backend.mqtt_ingestor
        
        mock_conn = MagicMock()
        mock_cur = mock_conn.cursor.return_value
        ingestor.conn = mock_conn
        
        ingestor.create_table(mock_cur)
        mock_conn.commit.assert_called_once()

    @patch('backend.mqtt_ingestor.time.sleep')
    @patch('backend.mqtt_ingestor.psycopg2')
    @patch('backend.mqtt_ingestor.mqtt')
    @patch('backend.mqtt_ingestor.datetime.datetime')
    def test_on_message_success_and_sql_generation(self, mock_dt, mock_mqtt, mock_psycopg2, mock_sleep):
        mock_dt.now.return_value = MOCK_NOW
        import backend.mqtt_ingestor
        ingestor = backend.mqtt_ingestor
        
        mock_conn = MagicMock()
        mock_cur = mock_conn.cursor.return_value
        ingestor.conn = mock_conn
        ingestor.cur = mock_cur
        
        TEST_TOPIC = "sensors/air/unit/OLIMEX_POE"
        TEST_PAYLOAD = {"heat_exchanger_efficiency": 88.0, "outdoor_temp": 25.5, "extra_value": "test"}
        mock_msg = MagicMock()
        mock_msg.topic = TEST_TOPIC
        mock_msg.payload.decode.return_value = json.dumps(TEST_PAYLOAD)
        
        ingestor.on_message(None, None, mock_msg)
        mock_cur.execute.assert_called()
        mock_conn.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
