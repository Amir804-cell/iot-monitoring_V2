import random
import psycopg2
import time
from datetime import datetime, timedelta

# Connect to QuestDB
conn = psycopg2.connect(
    dbname="qdb",
    user="admin",
    password="quest",
    host="127.0.0.1",  # use Docker container name if running inside network
    port=8812
)
cur = conn.cursor()

device_ids = ["ESP32_1", "ESP32_2", "ESP32_3"]

try:
    while True:
        ts = datetime.now()
        for device_id in device_ids:
            temperature = round(random.uniform(20, 30), 2)
            humidity = round(random.uniform(40, 70), 2)
            soil_moisture = round(random.uniform(20, 80), 2)
            energy = round(random.uniform(0.1, 5.0), 2)

            cur.execute(
                "INSERT INTO sensors (ts, device_id, temperature, humidity, soil_moisture, energy) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (ts, device_id, temperature, humidity, soil_moisture, energy)
            )
        conn.commit()
        print(f"Inserted data at {ts} for devices {device_ids}")
        time.sleep(10)  # wait 10 seconds before next insertion
finally:
    cur.close()
    conn.close()
