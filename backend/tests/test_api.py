import os
import sys

# Allow "import main" when running pytest from backend/
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
import main


client = TestClient(main.app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json().get("status") == "Backend running"


def test_devices_endpoint():
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert "devices" in response.json()


def test_query_endpoint_validation():
    """
    Simple sanity test that /api/data/query responds and validates body.
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    payload = {
        "device_id": "DUMMY",
        "start_time": (now - timedelta(hours=1)).isoformat(),
        "end_time": now.isoformat(),
        "limit": 10,
    }

    response = client.post("/api/data/query", json=payload)
    # Even if there is no data, we should get 200 and a JSON object
    assert response.status_code == 200
    assert "data" in response.json()
