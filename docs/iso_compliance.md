
---

## 3️⃣ `docs/iso_compliance.md`

```markdown
# ISO Standard Compliance – Overview

This project is not certified, but the design is inspired by:

## ISO 9001 – Quality Management

- Documented system setup in `README.md`.
- Architecture and dependencies documented in:
  - `docs/network_topology.md`
  - `docs/dependency_graph.md`
- Testing:
  - Integration: `test_system.py`
  - Backend unit tests: `backend/tests/test_api.py`.

## ISO/IEC 27001 – Information Security (informal alignment)

- **Network segregation**  
  - Docker bridge network `iot-net` separates services from host.
- **Access control**  
  - Mosquitto uses username/password (`edgeuser` / `Optilogic25` in lab setup).  
  - Grafana admin credentials via environment variables.
- **Logging & monitoring**  
  - Structured logging in `backend/logging_config.py`.  
  - Health/diagnostic scripts: `quick_check.sh`, `test_system.py`.

## IEC 62443 / industrial practices (conceptual)

- Layered architecture:
  - Field: DV10 + Modbus.
  - Edge: ESP32-POE.
  - Control: MQTT, QuestDB, FastAPI.
  - Supervision: Web dashboard, Grafana.
- Use of standard protocols:
  - Modbus RTU, MQTT, SparkplugB topics (via bridge), HTTP/REST, PostgreSQL wire protocol.

> This mapping is meant for documentation and exam purposes and does not
> represent formal ISO certification.
