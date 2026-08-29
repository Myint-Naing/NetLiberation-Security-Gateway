import pytest
from backend.dns_engine import get_dns_config, save_dns_config, sync_adblock_filters, get_dns_query_logs

def test_dns_config_and_sync():
    cfg = get_dns_config()
    assert "enabled" in cfg
    assert isinstance(cfg["whitelist"], list)
    assert isinstance(cfg["blacklist"], list)

    count = sync_adblock_filters()
    assert count >= 0

def test_dns_query_logs():
    logs = get_dns_query_logs()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "domain" in logs[0]
    assert "status" in logs[0]
