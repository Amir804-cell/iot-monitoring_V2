# IoT Ventilation Monitoring System

End-to-end system for monitoring a DV10 ventilation unit via Modbus → ESP32-POE → MQTT → QuestDB → FastAPI → Web Dashboard and Grafana.

## Architecture

- **Field device**: DV10 ventilation unit (Modbus RTU)
- **Edge device**: Olimex ESP32-POE  
  - Reads Modbus registers  
  - Publishes JSON over MQTT and can be bridged to SparkplugB topics
- **MQTT broker**: Eclipse Mosquitto (Docker)
- **Database**: QuestDB (time-series, Docker)
- **Backend API**: FastAPI + Uvicorn
- **Visualization**:
  - Custom web dashboard (`webserver/index.html`)
  - Grafana dashboards (QuestDB as PostgreSQL datasource)

See `docs/network_topology.md` for a detailed topology diagram and `docs/dependency_graph.md` for component dependencies.

## Getting Started

### 1. Start infrastructure (Docker)

```bash
cd ~/iot-monitoring
docker-compose up -d
./quick_check.sh
