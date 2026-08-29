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
  else
    echo -e "${RED}[ERROR] uninstall.sh script not found in current directory.${NC}"
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
WIFI_COUNT=$(echo "$IFACES" | grep -c "^wlan\|^wl" || true)

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
check_port_conflict 68 "DHCP Client"

# --- 3. Dependency Installation ---
echo -e "\n${YELLOW}[INSTALL] Installing System Dependencies & Routing Components...${NC}"
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv \
  hostapd dnsmasq iptables nftables \
  wireguard openvpn shadowsocks-libev xl2tpd \
  iw net-tools lsof speedtest-cli curl >/dev/null

# Attempt optional installation of legacy wireless-tools if available on distribution
apt-get install -y -qq wireless-tools >/dev/null 2>&1 || true

# Install python requirements
python3 -m pip install --quiet --break-system-packages \
  fastapi uvicorn pydantic psutil requests beautifulsoup4 pyjwt passlib || true

# --- 4. Service Deployment & Directories Setup ---
echo -e "\n${YELLOW}[SETUP] Deploying Gateway Core Services & Services Systemd Units...${NC}"

mkdir -p /etc/netliberation
mkdir -p /var/log/netliberation
mkdir -p /etc/hostapd
mkdir -p /etc/dnsmasq.d

# Systemd Service File Creation
cat << 'EOF' > /etc/systemd/system/netliberation.service
[Unit]
Description=NetLiberation Security Gateway Core Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/netliberation
ExecStart=/usr/bin/python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Copy codebase to /opt/netliberation if executing from outside
if [ "$(pwd)" != "/opt/netliberation" ]; then
  mkdir -p /opt/netliberation
  cp -r backend frontend docs /opt/netliberation/ 2>/dev/null || true
fi

# Enable Systemd Service
systemctl daemon-reload
systemctl enable netliberation.service
systemctl restart netliberation.service || true

# --- 5. Automated Cron & Retention Setup ---
echo -e "\n${YELLOW}[CRON] Setting up 7-Day Log Retention & Auto-Renewal Timers...${NC}"

# Daily Cron Job for 7-Day Log Purge & Cloudflare WARP/Outline Renewal
CRON_JOB="0 3 * * * python3 -c 'from backend.logging_service import purge_old_logs; purge_old_logs(7); from backend.warp import check_and_renew_warp_key; check_and_renew_warp_key()' >/dev/null 2>&1"
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
