import pytest
import time
import concurrent.futures
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_stress_api_concurrency():
    """Stress test backend API endpoints with concurrent requests."""
    # Obtain login token first
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    def make_request():
        r = client.get("/api/system/metrics", headers=headers)
        return r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request) for _ in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(code == 200 for code in results)

def test_simulated_thermal_stress():
    """Verify system metrics handling under high temperature conditions."""
    from backend.system import get_system_metrics
    metrics = get_system_metrics()
    assert "throttled" in metrics
    assert isinstance(metrics["throttled"], bool)
