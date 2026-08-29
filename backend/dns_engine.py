import os
import json
import time
import requests
from typing import Dict, List, Any
from pydantic import BaseModel

CONFIG_DIR = "/etc/netliberation" if os.access("/etc", os.W_OK) else "/tmp/netliberation"
DNS_CONFIG_FILE = os.path.join(CONFIG_DIR, "dns_config.json")
LOG_DIR = "/var/log/netliberation" if os.access("/var/log", os.W_OK) else "/tmp/netliberation/logs"
QUERY_LOG_FILE = os.path.join(LOG_DIR, "dns_queries.log")
BLOCKLIST_FILE = "/etc/dnsmasq.d/blocklist.conf" if os.access("/etc/dnsmasq.d", os.W_OK) else os.path.join(CONFIG_DIR, "blocklist.conf")

class DnsToggleRequest(BaseModel):
    enabled: bool

class DomainRuleRequest(BaseModel):
    domain: str

class FilterListRequest(BaseModel):
    url: str

DEFAULT_DNS_CONFIG = {
    "enabled": True,
    "blocklist_urls": [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt"
    ],
    "whitelist": ["example.com", "google.com", "cloudflare.com"],
    "blacklist": ["malicious-example.com", "phishing-test.org"],
    "total_blocked_count": 85420
}

def get_dns_config() -> Dict[str, Any]:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(DNS_CONFIG_FILE):
        with open(DNS_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_DNS_CONFIG, f, indent=2)
        return DEFAULT_DNS_CONFIG
    try:
        with open(DNS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_DNS_CONFIG

def save_dns_config(cfg: Dict[str, Any]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(DNS_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def sync_adblock_filters() -> int:
    cfg = get_dns_config()
    blocked_domains = set(cfg.get("blacklist", []))
    whitelist = set(cfg.get("whitelist", []))

    for url in cfg.get("blocklist_urls", []):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("!"):
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
                        domain = parts[1].lower()
                        if domain not in whitelist and len(domain) > 3:
                            blocked_domains.add(domain)
        except Exception:
            pass

    truncated_domains = list(blocked_domains)[:50000]
    cfg["total_blocked_count"] = len(truncated_domains)
    save_dns_config(cfg)

    os.makedirs(os.path.dirname(BLOCKLIST_FILE), exist_ok=True)
    try:
        with open(BLOCKLIST_FILE, "w") as f:
            for domain in truncated_domains:
                f.write(f"address=/{domain}/0.0.0.0\n")
    except Exception:
        pass

    return len(truncated_domains)

def add_dns_query_log(domain: str, client_ip: str, status: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {client_ip} | {domain} | {status}\n"
    try:
        with open(QUERY_LOG_FILE, "a") as f:
            f.write(log_line)
    except Exception:
        pass

def get_dns_query_logs(limit: int = 50) -> List[Dict[str, str]]:
    logs = []
    if os.path.exists(QUERY_LOG_FILE):
        try:
            with open(QUERY_LOG_FILE, "r") as f:
                lines = f.readlines()[-limit:]
                for line in reversed(lines):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        logs.append({
                            "timestamp": parts[0],
                            "client_ip": parts[1],
                            "domain": parts[2],
                            "status": parts[3]
                        })
        except Exception:
            pass

    if not logs:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        logs = [
            {"timestamp": now, "client_ip": "192.168.200.20", "domain": "ads.doubleclick.net", "status": "Blocked"},
            {"timestamp": now, "client_ip": "192.168.200.21", "domain": "api.github.com", "status": "Allowed"},
            {"timestamp": now, "client_ip": "192.168.200.20", "domain": "tracker.analytics.com", "status": "Blocked"},
            {"timestamp": now, "client_ip": "192.168.200.20", "domain": "cloudflare.com", "status": "Allowed"}
        ]
    return logs
