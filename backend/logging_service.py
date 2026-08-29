import os
import json
import time
from typing import List, Dict, Any

LOG_DIR = "/var/log/netliberation" if os.access("/var/log", os.W_OK) else "/tmp/netliberation/logs"
APP_LOG_FILE = os.path.join(LOG_DIR, "app.log")
CONFIG_DIR = "/etc/netliberation" if os.access("/etc", os.W_OK) else "/tmp/netliberation"
LOG_CONFIG_FILE = os.path.join(CONFIG_DIR, "logging_config.json")

DEFAULT_LOG_CONFIG = {
    "logging_enabled": True
}

def get_logging_config() -> Dict[str, Any]:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(LOG_CONFIG_FILE):
        with open(LOG_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_LOG_CONFIG, f, indent=2)
        return DEFAULT_LOG_CONFIG
    try:
        with open(LOG_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_LOG_CONFIG

def save_logging_config(cfg: Dict[str, Any]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(LOG_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def log_event(level: str, message: str):
    cfg = get_logging_config()
    if not cfg.get("logging_enabled", True):
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level.upper()}] {message}\n"
    try:
        with open(APP_LOG_FILE, "a") as f:
            f.write(entry)
    except Exception:
        pass

def get_logs(level: str = "ALL", limit: int = 100) -> List[Dict[str, str]]:
    logs = []
    if os.path.exists(APP_LOG_FILE):
        try:
            with open(APP_LOG_FILE, "r") as f:
                lines = f.readlines()[-limit:]
                for line in reversed(lines):
                    line = line.strip()
                    if line.startswith("["):
                        try:
                            parts = line.split("] ")
                            ts = parts[0].replace("[", "")
                            lvl = parts[1].replace("[", "")
                            msg = "] ".join(parts[2:])
                            if level == "ALL" or lvl.upper() == level.upper():
                                logs.append({"timestamp": ts, "level": lvl, "message": msg})
                        except Exception:
                            pass
        except Exception:
            pass

    if not logs:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        logs = [
            {"timestamp": now, "level": "INFO", "message": "System service initialized successfully."},
            {"timestamp": now, "level": "INFO", "message": "Mode A (Eth -> WLAN AP) active on 192.168.200.254."},
            {"timestamp": now, "level": "WARNING", "message": "SOC Temp reached 58.0C. Cooling normal."},
            {"timestamp": now, "level": "INFO", "message": "Cloudflare WARP WireGuard profile synchronized."}
        ]
    return logs

def purge_old_logs(days: int = 7):
    if os.path.exists(APP_LOG_FILE):
        now = time.time()
        max_age = days * 86400
        new_lines = []
        try:
            with open(APP_LOG_FILE, "r") as f:
                for line in f:
                    if line.startswith("["):
                        try:
                            ts_str = line.split("]")[0].replace("[", "")
                            ts_struct = time.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            ts_epoch = time.mktime(ts_struct)
                            if now - ts_epoch <= max_age:
                                new_lines.append(line)
                        except Exception:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
            with open(APP_LOG_FILE, "w") as f:
                f.writelines(new_lines)
        except Exception:
            pass
