import pytest
from backend.system import get_system_metrics, set_cpu_governor
from backend.logging_service import log_event, get_logs, purge_old_logs
from backend.tools import run_ping

def test_system_metrics():
    metrics = get_system_metrics()
    assert "cpu_percent" in metrics
    assert "soc_temp_c" in metrics
    assert "ram" in metrics
    assert metrics["ram"]["total_mb"] > 0

def test_cpu_governor():
    assert set_cpu_governor("schedutil") is True
    assert set_cpu_governor("invalid_gov") is False

def test_logging_and_purge():
    log_event("INFO", "Test log entry for unit test")
    logs = get_logs()
    assert isinstance(logs, list)
    assert len(logs) > 0
    purge_old_logs(7)

def test_diagnostic_tools():
    ping_out = run_ping("127.0.0.1", count=1)
    assert "127.0.0.1" in ping_out
