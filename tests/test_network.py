import pytest
from backend.network import apply_network_mode, get_network_config, get_dhcp_clients, scan_wifi_networks

def test_network_mode_switching():
    for mode in ["A", "B", "C", "D"]:
        assert apply_network_mode(mode) is True
        cfg = get_network_config()
        assert cfg["mode"] == mode

def test_dhcp_clients():
    clients = get_dhcp_clients()
    assert isinstance(clients, list)
    assert len(clients) > 0
    assert "mac" in clients[0]
    assert "ip" in clients[0]

def test_wifi_scanning():
    aps = scan_wifi_networks("wlan0")
    assert isinstance(aps, list)
    assert len(aps) > 0
    assert "ssid" in aps[0]
