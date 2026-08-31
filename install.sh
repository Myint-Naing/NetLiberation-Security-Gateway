#!/usr/bin/env bash
# NetLiberation Security Gateway - Automated Deployment & Installation Engine
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}       NetLiberation Security Gateway - Installation Engine     ${NC}"
echo -e "${BLUE}================================================================${NC}"

# --- 0. Command Line Option Parsing ---
if [ "$1" == "--uninstall" ] || [ "$1" == "-u" ]; then
  if [ -f "./uninstall.sh" ]; then
    exec bash ./uninstall.sh
  elif [ -f "/opt/netliberation/uninstall.sh" ]; then
    exec bash /opt/netliberation/uninstall.sh
  else
    echo -e "${RED}[ERROR] uninstall.sh script not found.${NC}"
    exit 1
  fi
fi

# --- 1. Root Execution Privilege Verification ---
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERROR] Installation must be executed as root. Please use 'sudo bash install.sh'${NC}"
  exit 1
fi

# --- 2. Interactive Pre-flight Prerequisite Checks ---
echo -e "\n${YELLOW}[PRE-FLIGHT] Executing System & Prerequisite Diagnostic Checks...${NC}"

# Hardware RAM Check (Minimum 1.5GB / 1500MB)
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
echo -e "  -> Memory Detected: ${TOTAL_RAM} MB"
if [ "$TOTAL_RAM" -lt 1200 ]; then
  echo -e "${RED}[WARNING] System RAM (${TOTAL_RAM}MB) is below the recommended 1.5GB - 2GB RAM threshold.${NC}"
  read -p "Do you want to continue anyway? (y/N): " ram_choice
  if [[ "$ram_choice" != "y" && "$ram_choice" != "Y" ]]; then
    echo -e "${RED}Installation aborted by user.${NC}"
    exit 1
  fi
fi

# Thermal Sensor Verification
if [ -d "/sys/class/thermal" ]; then
  echo -e "  -> Thermal Sensors: ${GREEN}Detected${NC}"
else
  echo -e "  -> Thermal Sensors: ${YELLOW}Not Found (Emulated mode will be used)${NC}"
fi

# Network Interface Audit (Require 1 Ethernet + at least 1 Wi-Fi)
IFACES=$(ip -br link show | awk '{print $1}')
ETH_COUNT=$(echo "$IFACES" | grep -c "^eth\|^en" || true)
WIFI_COUNT=$(echo "$IFACES" | grep -c "^wlan\|^wl\|^wlx" || true)

echo -e "  -> Ethernet Interfaces Found: ${ETH_COUNT}"
echo -e "  -> Wi-Fi Interfaces Found: ${WIFI_COUNT}"

if [ "$ETH_COUNT" -lt 1 ] || [ "$WIFI_COUNT" -lt 1 ]; then
  echo -e "${RED}[WARNING] Expected at least 1 Ethernet interface and 1 Wi-Fi interface.${NC}"
  read -p "Continue with single/custom network interface configuration? (y/N): " iface_choice
  if [[ "$iface_choice" != "y" && "$iface_choice" != "Y" ]]; then
    echo -e "${RED}Installation aborted by user.${NC}"
    exit 1
  fi
fi

# Global conflict tracker for reboot prompt
CONFLICTS_RESOLVED=0

# Service & Port Conflict Resolution
check_port_conflict() {
  local port=$1
  local service_name=$2
  if lsof -i :"$port" >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep -q ":$port "; then
    echo -e "${YELLOW}[CONFLICT] Port $port is currently in use (possibly by $service_name).${NC}"
    read -p "Automatically stop, disable, and purge conflicting packages for port $port? (Y/n): " conflict_choice
    if [[ "$conflict_choice" != "n" && "$conflict_choice" != "N" ]]; then
      echo -e "Stopping conflicting services and purging conflicting packages..."
      systemctl stop systemd-resolved dnsmasq apache2 nginx 2>/dev/null || true
      systemctl disable systemd-resolved dnsmasq apache2 nginx 2>/dev/null || true
      apt-get purge -y apache2 nginx 2>/dev/null || true

      # Preserve host DNS resolution during installation if systemd-resolved was stopped
      if [ "$port" -eq 53 ]; then
        rm -f /etc/resolv.conf
        echo -e "nameserver 1.1.1.1\nnameserver 8.8.8.8" > /etc/resolv.conf
        echo -e "  -> Temporary fallback DNS nameservers (1.1.1.1, 8.8.8.8) written to /etc/resolv.conf."
      fi

      echo -e "${GREEN}Port $port freed successfully.${NC}"
      CONFLICTS_RESOLVED=1
    else
      echo -e "${RED}Port conflict not resolved. Installation aborted.${NC}"
      exit 1
    fi
  fi
}

echo -e "\n${YELLOW}[PRE-FLIGHT] Checking Port & Service Conflicts...${NC}"
check_port_conflict 53 "systemd-resolved / dnsmasq"
check_port_conflict 80 "web server (apache/nginx)"
check_port_conflict 67 "DHCP Server"

# --- 3. Dependency Installation ---
echo -e "\n${YELLOW}[INSTALL] Installing System Dependencies & Routing Components...${NC}"
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv python3-pytest \
  hostapd dnsmasq iptables nftables rfkill \
  wireguard openvpn shadowsocks-libev xl2tpd \
  iw net-tools lsof speedtest-cli curl >/dev/null

# Attempt optional installation of legacy wireless-tools if available on distribution
apt-get install -y -qq wireless-tools >/dev/null 2>&1 || true

# --- 4. Virtual Environment & Service Deployment Setup ---
echo -e "\n${YELLOW}[SETUP] Deploying Gateway Core Services & Python Virtual Environment...${NC}"

mkdir -p /etc/netliberation
mkdir -p /var/log/netliberation
mkdir -p /etc/hostapd
mkdir -p /etc/dnsmasq.d
mkdir -p /etc/NetworkManager/conf.d

# Unmask hostapd if masked by systemd
systemctl unmask hostapd 2>/dev/null || true

# Configure /etc/default/hostapd to point to config file
if [ -f "/etc/default/hostapd" ]; then
  sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
else
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > /etc/default/hostapd
fi
mkdir -p /opt/netliberation

# Create Python Virtual Environment to eliminate root pip warnings & package conflicts
if [ ! -d "/opt/netliberation/venv" ]; then
  python3 -m venv /opt/netliberation/venv
fi

# Install python requirements in dedicated venv
/opt/netliberation/venv/bin/pip install --quiet \
  fastapi uvicorn pydantic psutil requests beautifulsoup4 pyjwt passlib pytest

# Symlink pytest into system PATH so 'pytest tests/ -v' and 'sudo pytest tests/ -v' work directly
ln -sf /opt/netliberation/venv/bin/pytest /usr/local/bin/pytest 2>/dev/null || true
ln -sf /opt/netliberation/venv/bin/pytest /usr/bin/pytest 2>/dev/null || true

# Systemd Service File Creation with explicitly set PYTHONPATH
cat << 'EOF' > /etc/systemd/system/netliberation.service
[Unit]
Description=NetLiberation Security Gateway Core Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/netliberation
Environment="PYTHONPATH=/opt/netliberation"
ExecStart=/opt/netliberation/venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Always copy codebase cleanly item-by-item to /opt/netliberation
mkdir -p /opt/netliberation
for item in backend frontend docs tests conftest.py uninstall.sh diagnose.sh; do
  if [ -e "$SCRIPT_DIR/$item" ]; then
    rm -rf "/opt/netliberation/$item"
    cp -r "$SCRIPT_DIR/$item" "/opt/netliberation/$item"
  fi
done

# Install diagnostic collector script and create system-wide symlinks
if [ -f "/opt/netliberation/diagnose.sh" ]; then
  chmod +x /opt/netliberation/diagnose.sh
  ln -sf /opt/netliberation/diagnose.sh /usr/local/bin/netliberation-diag 2>/dev/null || true
  ln -sf /opt/netliberation/diagnose.sh /usr/bin/netliberation-diag 2>/dev/null || true
fi

# Ensure full permissions so non-root users (e.g. myint) can run pytest and write .pytest_cache in /opt/netliberation
chmod -R 777 /opt/netliberation

# Configure NetworkManager unmanaged rule for LAN AP interface
echo -e "[keyfile]\nunmanaged-devices=interface-name:wlan0" > /etc/NetworkManager/conf.d/netliberation.conf
systemctl reload NetworkManager 2>/dev/null || nmcli general reload 2>/dev/null || true

# Configure regulatory domain, disconnect wlan0 from NetworkManager & unblock RF kill-switches
iw reg set US 2>/dev/null || true
nmcli dev disconnect wlan0 2>/dev/null || true
nmcli dev set wlan0 managed no 2>/dev/null || true
pkill -f "wpa_supplicant.*wlan0" 2>/dev/null || true
ip link set dev wlan0 down 2>/dev/null || true
rfkill unblock all 2>/dev/null || true

# Enable Systemd Service & Trigger Mode A Wi-Fi AP Startup
systemctl daemon-reload
systemctl enable netliberation.service
systemctl restart netliberation.service || true

# Trigger initial network mode setup (Mode A) & start hostapd / dnsmasq
/opt/netliberation/venv/bin/python -c "import sys; sys.path.insert(0, '/opt/netliberation'); from backend.network import apply_network_mode; apply_network_mode('A')" 2>/dev/null || true
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd dnsmasq 2>/dev/null || true
systemctl restart hostapd dnsmasq 2>/dev/null || true

# --- 5. Automated Cron & Retention Setup ---
echo -e "\n${YELLOW}[CRON] Setting up 7-Day Log Retention & Auto-Renewal Timers...${NC}"

# Daily Cron Job for 7-Day Log Purge & Cloudflare WARP/Outline Renewal
CRON_JOB="0 3 * * * PYTHONPATH=/opt/netliberation /opt/netliberation/venv/bin/python -c 'from backend.logging_service import purge_old_logs; purge_old_logs(7); from backend.warp import check_and_renew_warp_key; check_and_renew_warp_key()' >/dev/null 2>&1"
(crontab -l 2>/dev/null | grep -v "purge_old_logs"; echo "$CRON_JOB") | crontab -

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  NetLiberation Security Gateway Installed Successfully!        ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "Access Web Management Panel at: ${BLUE}http://192.168.200.254${NC} or ${BLUE}http://localhost${NC}"
echo -e "Default Credentials: Username: ${GREEN}admin${NC} | Password: ${GREEN}admin${NC}"
echo -e "Default Wi-Fi AP SSID: ${GREEN}NetLiberation${NC} | Passphrase: ${GREEN}Freedom4all${NC}\n"

if [ "$CONFLICTS_RESOLVED" -eq 1 ]; then
  echo -e "${YELLOW}[REBOOT RECOMMENDED] Services/ports were purged or modified during installation.${NC}"
  read -p "Would you like to reboot the system now? (y/N): " reboot_choice
  if [[ "$reboot_choice" == "y" || "$reboot_choice" == "Y" ]]; then
    echo -e "${GREEN}Rebooting system...${NC}"
    reboot
  fi
fi
