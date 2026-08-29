import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.auth import authenticate_user, LoginRequest
from backend.security import sanitize_input, validate_domain_or_ip
from fastapi import HTTPException

client = TestClient(app)

def test_login_success():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "token" in data

def test_login_failure():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401

def test_input_sanitization():
    raw_xss = "<script>alert('xss')</script>"
    clean = sanitize_input(raw_xss)
    assert "<script>" not in clean
    assert "&lt;script&gt;" in clean

def test_validate_domain_ip():
    valid_domain = validate_domain_or_ip("example.com")
    assert valid_domain == "example.com"

    valid_ip = validate_domain_or_ip("192.168.200.254")
    assert valid_ip == "192.168.200.254"

    with pytest.raises(HTTPException):
        validate_domain_or_ip("example.com; rm -rf /")
