#!/usr/bin/env bash
# NetLiberation Security Gateway - Clean Uninstallation Engine
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo -e "\n${YELLOW}[4/5] Restoring network configurations & DNS resolver...${NC}"
systemctl stop hostapd dnsmasq 2>/dev/null || true
systemctl disable hostapd dnsmasq 2>/dev/null || true
echo -e "  -> Stopped and disabled hostapd and dnsmasq instances."

# Restore systemd-resolved and DNS resolution settings
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "systemd-resolved"; then
  echo -e "  -> Re-enabling and starting systemd-resolved..."
  systemctl enable systemd-resolved 2>/dev/null || true
  systemctl start systemd-resolved 2>/dev/null || true
  if [ -d "/run/systemd/resolve" ]; then
    rm -f /etc/resolv.conf 2>/dev/null || true
    ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf 2>/dev/null || true
    echo -e "  -> Restored /etc/resolv.conf symlink to systemd-resolved stub-resolv.conf."
  fi
fi

# Fallback DNS resolution if domain lookup fails
if ! host google.com >/dev/null 2>&1 && ! nslookup google.com >/dev/null 2>&1; then
  rm -f /etc/resolv.conf 2>/dev/null || true
  echo -e "nameserver 1.1.1.1\nnameserver 8.8.8.8" > /etc/resolv.conf
  echo -e "  -> Configured fallback nameservers in /etc/resolv.conf (1.1.1.1, 8.8.8.8)."
fi

echo -e "\n${YELLOW}[5/5] Removing installed files and directories...${NC}"
rm -rf /etc/netliberation
rm -rf /var/log/netliberation
rm -rf /opt/netliberation
echo -e "  -> System directories (/etc/netliberation, /var/log/netliberation, /opt/netliberation) removed."

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  NetLiberation Security Gateway has been completely uninstalled. ${NC}"
echo -e "${GREEN}================================================================${NC}\n"
