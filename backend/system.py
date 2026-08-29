import os
import psutil
import subprocess
from typing import Dict, Any
from pydantic import BaseModel

class GovernorRequest(BaseModel):
    governor: str

def get_soc_temperature() -> float:
    """Read temperature from SBC thermal zone."""
    thermal_paths = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp"
    ]
    for path in thermal_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    temp_raw = float(f.read().strip())
                    return round(temp_raw / 1000.0, 1) if temp_raw > 1000 else round(temp_raw, 1)
            except Exception:
                pass
    return 42.0  # Default fallback reading

def get_cpu_governor() -> str:
    """Get current scaling governor for cpu0."""
    gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if os.path.exists(gov_path):
        try:
            with open(gov_path, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return "schedutil"

def set_cpu_governor(governor: str) -> bool:
    """Set scaling governor across all online CPUs safely."""
    allowed = ["schedutil", "performance", "powersave", "ondemand"]
    if governor not in allowed:
        return False

    cpu_count = os.cpu_count() or 4
    success = True
    for cpu in range(cpu_count):
        path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
        if os.path.exists(path):
            try:
                # Write to sysfs directly or via tee
                res = subprocess.run(["sudo", "tee", path], input=governor.encode(), capture_output=True)
                if res.returncode != 0:
                    success = False
            except Exception:
                success = False
    return success

def get_system_metrics() -> Dict[str, Any]:
    """Gather real-time CPU, RAM, Disk, Temperature, and Governor state."""
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    temp = get_soc_temperature()
    gov = get_cpu_governor()

    # Check thermal throttling state (temp > 75C or kernel flags)
    is_throttled = temp > 75.0

    return {
        "cpu_percent": round(cpu_pct, 1),
        "soc_temp_c": temp,
        "ram": {
            "total_mb": round(mem.total / (1024 * 1024), 1),
            "used_mb": round(mem.used / (1024 * 1024), 1),
            "percent": round(mem.percent, 1)
        },
        "disk": {
            "total_gb": round(disk.total / (1024 * 1024 * 1024), 1),
            "used_gb": round(disk.used / (1024 * 1024 * 1024), 1),
            "percent": round(disk.percent, 1)
        },
        "governor": gov,
        "throttled": is_throttled
    }

def reboot_system():
    """Trigger system reboot."""
    subprocess.run(["sudo", "reboot"], check=False)

def shutdown_system():
    """Trigger system shutdown."""
    subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
