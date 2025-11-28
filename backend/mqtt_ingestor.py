import json
import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime

# =======================
# CONFIG
# =======================

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "sensors/#"

DB_CONFIG = {
    "dbname": "qdb",
    "user": "admin",
    "password": "quest",
    "host": "localhost",
    "port": 8812
}

# =======================
# CONNECT TO QUESTDB
# =======================

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("Connected to QuestDB")

# =======================
# Ensure OLIMEX table exists
# =======================

cur.execute("""
CREATE TABLE IF NOT EXISTS olimex_data (
    ts TIMESTAMP,
    device_id SYMBOL,

    heat_exchanger_efficiency DOUBLE,
    run_mode INT,

    outdoor_temp DOUBLE,
    supply_air_temp DOUBLE,
    supply_air_setpoint_temp DOUBLE,
    exhaust_air_temp DOUBLE,
    extract_air_temp DOUBLE,

    supply_air_pressure DOUBLE,
    extract_air_pressure DOUBLE,

    supply_air_flow DOUBLE,
    extract_air_flow DOUBLE,
    extra_supply_air_flow DOUBLE,
    extra_extract_air_flow DOUBLE,

    supply_air_fan_runtime LONG,
    extract_air_fan_runtime LONG
) TIMESTAMP(ts)
PARTITION BY DAY;
""")

conn.commit()
print("Ensured 'olimex_data' table exists")


# =======================
# MQTT CALLBACK
# =======================

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        print(f"Received: {data}")

        # extract fields safely
        ts = datetime.utcnow()

        query = """
        INSERT INTO olimex_data (
            ts, device_id,
            heat_exchanger_efficiency, run_mode,
            outdoor_temp, supply_air_temp, supply_air_setpoint_temp,
            exhaust_air_temp, extract_air_temp,
            supply_air_pressure, extract_air_pressure,
            supply_air_flow, extract_air_flow, extra_supply_air_flow,
            extra_extract_air_flow,
            supply_air_fan_runtime, extract_air_fan_runtime
        ) VALUES (
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s,
            %s, %s
        );
        """

        cur.execute(query, (
            ts,
            data.get("device_id", "UNKNOWN"),
            data.get("heat_exchanger_efficiency"),
            data.get("run_mode"),

            data.get("outdoor_temp"),
            data.get("supply_air_temp"),
            data.get("supply_air_setpoint_temp"),
            data.get("exhaust_air_temp"),
            data.get("extract_air_temp"),

            data.get("supply_air_pressure"),
            data.get("extract_air_pressure"),

            data.get("supply_air_flow"),
            data.get("extract_air_flow"),
            data.get("extra_supply_air_flow"),
            data.get("extra_extract_air_flow"),

            data.get("supply_air_fan_runtime"),
            data.get("extract_air_fan_runtime")
        ))

        conn.commit()
        print("Inserted row into olimex_data")

    except Exception as e:
        print("Error:", e)


# =======================
# RUN MQTT CLIENT
# =======================

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT)
client.subscribe(MQTT_TOPIC)

print(f"Subscribed to {MQTT_TOPIC}")
client.loop_forever()
