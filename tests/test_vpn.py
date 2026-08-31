import pytest
from backend.vpn import toggle_vpn, get_vpn_state
from backend.warp import generate_cloudflare_warp_key
from backend.outline import parse_ss_uri, fetch_active_outline_key

def test_vpn_toggle():
    state_on = toggle_vpn(True, "wireguard", True)
    assert state_on["enabled"] is True
    assert state_on["status"] == "Connected"

    state_off = toggle_vpn(False, "wireguard", True)
    assert state_off["enabled"] is False
    assert state_off["status"] == "Disconnected"

def test_cloudflare_warp_generator():
    res = generate_cloudflare_warp_key()
    assert res["status"] == "success"
    assert "meta" in res
    assert res["meta"]["status"].startswith("Active")
    state = get_vpn_state()
    assert "warp.conf" in state["profiles"]

def test_outline_ss_uri_parser():
    # Base64 of aes-256-gcm:Password123456
    ss_uri = "ss://YWVzLTI1Ni1nY206UGFzc3dvcmQxMjM0NTY=@185.220.101.5:8388#Test-Server"
    parsed = parse_ss_uri(ss_uri)
    assert parsed is not None
    assert parsed["server"] == "185.220.101.5"
    assert parsed["server_port"] == 8388
    assert parsed["method"] == "aes-256-gcm"

def test_outline_fetcher():
    res = fetch_active_outline_key()
    assert res["status"] == "success"
    assert "ss_uri" in res
    assert res["ss_uri"].startswith("ss://")
    assert "NetLiberation" in res["ss_uri"]
    assert "config" in res
    assert "meta" in res
    state = get_vpn_state()
    assert "outline.json" in state["profiles"]
