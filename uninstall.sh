#!/usr/bin/env bash
# NetLiberation Security Gateway - Clean Uninstallation Engine
set -e

RED='\030[0;31m'
GREEN='\030[0;32m'
YELLOW='\030[1;33m'
BLUE='\030[0;34m'
NC='\030[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}       NetLiberation Security Gateway - Uninstallation Engine   ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Root Execution Privilege Verification
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERROR] Uninstallation must be executed as root. Please use 'sudo bash uninstall.sh'${NC}"
  exit 1
fi

read -p "Are you sure you want to completely uninstall NetLiberation Security Gateway? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo -e "${YELLOW}Uninstallation cancelled.${NC}"
  exit 0
fi

echo -e "\n${YELLOW}[1/5] Stopping and disabling NetLiberation systemd service...${NC}"
if systemctl is-active --quiet netliberation.service 2>/dev/null; then
  systemctl stop netliberation.service || true
fi
if systemctl is-enabled --quiet netliberation.service 2>/dev/null; then
  systemctl disable netliberation.service || true
fi

if [ -f "/etc/systemd/system/netliberation.service" ]; then
  rm -f /etc/systemd/system/netliberation.service
  systemctl daemon-reload
  echo -e "  -> Systemd service file removed."
fi

echo -e "\n${YELLOW}[2/5] Cleaning up NetLiberation crontab entries...${NC}"
if crontab -l 2>/dev/null | grep -q "purge_old_logs"; then
  (crontab -l 2>/dev/null | grep -v "purge_old_logs") | crontab -
  echo -e "  -> Automated maintenance cron jobs removed from crontab."
fi

echo -e "\n${YELLOW}[3/5] Resetting firewall / iptables rules & routing...${NC}"
iptables -t nat -F 2>/dev/null || true
iptables -F 2>/dev/null || true
echo -e "  -> NAT and forwarding rules flushed."

echo -e "\n${YELLOW}[4/5] Restoring network configurations...${NC}"
systemctl stop hostapd dnsmasq 2>/dev/null || true
echo -e "  -> Stopped hostapd and dnsmasq instances."

echo -e "\n${YELLOW}[5/5] Removing installed files and directories...${NC}"
rm -rf /etc/netliberation
rm -rf /var/log/netliberation
rm -rf /opt/netliberation
echo -e "  -> System directories (/etc/netliberation, /var/log/netliberation, /opt/netliberation) removed."

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  NetLiberation Security Gateway has been completely uninstalled. ${NC}"
echo -e "${GREEN}================================================================${NC}\n"
