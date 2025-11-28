# Roadmap for Further Development

## Short term (0–3 months)

- Harden credentials (move passwords to `.env`, remove from git).
- Add auto-setup scripts for:
  - QuestDB schema (CREATE TABLE).
  - Grafana datasource and dashboards.
- Extend unit tests to:
  - `mqtt_ingestor.py`
  - `sparkplug_bridge.py`
- Add CI (GitHub Actions) to run:
  - `pytest`
  - `python3 test_system.py` (smoke test with mocked services).

## Medium term (3–6 months)

- Use full SparkplugB payloads end-to-end (not only in bridge).
- Add authentication/authorization on the API (JWT/OAuth2).
- Provide configuration templates for multi-site deployments.
- Containerise backend and ingestors (Python services in Docker) with health checks.

## Long term (6–12 months)

- Add more field protocols (Modbus TCP, BACnet, OPC UA).
- Add analytics: anomaly detection / performance KPIs for ventilation.
- Integrate with building management systems (BMS).
- Prepare structured documentation set for future ISO 9001 / 27001 pre-audit.
