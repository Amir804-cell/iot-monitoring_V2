Backend (Python / FastAPI)
   ├─ main.py
   ├─ mqtt_ingestor.py
   │   ├─ paho-mqtt
   │   └─ psycopg2-binary
   ├─ sparkplug_bridge.py
   │   ├─ paho-mqtt
   │   └─ sparkplug-b      <-- SparkplugB library lives HERE
   ├─ logging_config.py
   └─ tests/test_api.py
