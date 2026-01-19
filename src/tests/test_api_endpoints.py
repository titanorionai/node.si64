import os
import sys
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

from brain.dispatcher import app  # type: ignore  # noqa: E402

client = TestClient(app)


def test_stats_endpoint_basic():
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "fleet_size" in data
    assert "queue_depth" in data
    assert "total_revenue" in data


def test_fleet_endpoint_shape():
    resp = client.get("/api/fleet")
    assert resp.status_code == 200
    data = resp.json()
    assert "pools" in data
    assert "fleet_size" in data
    assert isinstance(data["pools"], dict)


@pytest.mark.parametrize("tier", ["M2", "ORIN", "M3_ULTRA", "THOR"])
def test_devices_endpoint_tiers(tier):
    resp = client.get(f"/api/devices/{tier}")
    assert resp.status_code == 200
    devices = resp.json()
    assert isinstance(devices, list)
    for d in devices:
        assert "id" in d
        assert "name" in d
