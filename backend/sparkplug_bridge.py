"""
Sparkplug-style bridge (JSON version, no extra libraries)

Listens on JSON topics "sensors/#" and republishes the same values on
SparkplugB-style topics:

  spBv1.0/<GROUP_ID>/NDATA/<EDGE_ID>/<device_id>

Instead of real binary SparkplugB protobuf payloads, we send a simple JSON:

{
  "device_id": "...",
  "timestamp": 1234567890,
  "metrics": {
      "SupplyTemp": ...,
      "ExtractTemp": ...,
      "SupplyFlow": ...,
      "Efficiency": ...,
      "RunMode": ...
  }
}

This is enough to:
- Demonstrate Sparkplug topic structure
- Separate JSON telemetry from "Sparkplug-style" telemetry
- Avoid external library installation problems
"""

import json
import time

import paho.mqtt.client as mqtt

# ======== USER CONFIGURATION =====================================

# >>> SET ME: Sparkplug group and edge identifiers (for exam/diagram)
GROUP_ID = "VentilationGroup"   # e.g. building/site name
EDGE_ID = "EdgeNode1"           # e.g. "BasementRack1"

# MQTT broker config (same Mosquitto as rest of system)
MQTT_HOST = "127.0.0.1"         # change if broker is on another host
MQTT_PORT = 1883
MQTT_USER = "edgeuser"
MQTT_PASS = "Optilogic25"

# We listen on the existing JSON topics from ESP32
SOURCE_TOPIC = "sensors/#"

# ================================================================


def build_sparkplug_style_payload(device_id: str, data: dict) -> str:
    """
    Build a simple JSON payload that *looks* like Sparkplug metrics.

    Real Sparkplug uses protobuf binary; here we focus on:
    - naming
    - grouping
    - topic layout
    """
    metrics = {}

    if "supply_temp" in data:
        metrics["SupplyTemp"] = float(data["supply_temp"])
    if "extract_temp" in data:
        metrics["ExtractTemp"] = float(data["extract_temp"])
    if "supply_flow" in data:
        metrics["SupplyFlow"] = float(data["supply_flow"])
    if "efficiency" in data:
        metrics["Efficiency"] = float(data["efficiency"])
    if "run_mode" in data:
        try:
            metrics["RunMode"] = int(data["run_mode"])
        except ValueError:
            metrics["RunMode"] = data["run_mode"]

    payload = {
        "device_id": device_id,
        "timestamp": int(time.time()),
        "metrics": metrics,
    }
    return json.dumps(payload)


def on_connect(client, userdata, flags, rc, properties=None):
    print("Sparkplug JSON bridge connected to MQTT with result code", rc)
    client.subscribe(SOURCE_TOPIC)
    print(f"Subscribed to {SOURCE_TOPIC}")


def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode("utf-8", errors="ignore")
        data = json.loads(payload_str)

        device_id = data.get("device_id", "UNKNOWN")
        sp_payload_str = build_sparkplug_style_payload(device_id, data)

        topic = f"spBv1.0/{GROUP_ID}/NDATA/{EDGE_ID}/{device_id}"
        client.publish(topic, sp_payload_str, qos=0, retain=False)

        print(f"Bridged JSON -> Sparkplug-style JSON on topic: {topic}")
        print(f"  payload: {sp_payload_str}")

    except Exception as e:
        print("Error in sparkplug JSON bridge:", e)


def main():
    client = mqtt.Client(client_id="sparkplug_json_bridge", protocol=mqtt.MQTTv311)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
