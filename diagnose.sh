#!/usr/bin/env bash
# NetLiberation Security Gateway - System Diagnostic Collector

REPORT_FILE="/var/log/netliberation/diagnostic_report.log"
mkdir -p /var/log/netliberation

exec > >(tee "$REPORT_FILE") 2>&1

echo "================================================================"
echo "      NetLiberation Security Gateway - System Diagnostic Report"
echo "      Generated at: $(date)"
echo "================================================================"

echo -e "\n--- 1. SYSTEM ENVIRONMENT & OS RELEASE ---"
uname -a
if [ -f /etc/os-release ]; then
  cat /etc/os-release
fi

echo -e "\n--- 2. NETWORK INTERFACES & IP CONFIGURATION ---"
ip -br link
echo ""
ip -br addr

echo -e "\n--- 3. REGULATORY DOMAIN & RFKILL WIRELESS STATUS ---"
iw reg get || true
echo ""
rfkill list || true

echo -e "\n--- 4. SERVICE STATUSES ---"
for svc in netliberation hostapd dnsmasq NetworkManager wpa_supplicant; do
  echo ">>> Service: $svc <<<"
  systemctl status "$svc" --no-pager -l || true
  echo ""
done

echo -e "\n--- 5. HOSTAPD CONFIGURATION (/etc/hostapd/hostapd.conf) ---"
if [ -f /etc/hostapd/hostapd.conf ]; then
  cat /etc/hostapd/hostapd.conf
else
  echo "File /etc/hostapd/hostapd.conf NOT FOUND."
fi

echo -e "\n--- 6. DNSMASQ CONFIGURATION (/etc/dnsmasq.conf) ---"
if [ -f /etc/dnsmasq.conf ]; then
  cat /etc/dnsmasq.conf
else
  echo "File /etc/dnsmasq.conf NOT FOUND."
fi

echo -e "\n--- 7. NETLIBERATION STATE CONFIG (/etc/netliberation/network_config.json) ---"
if [ -f /etc/netliberation/network_config.json ]; then
  cat /etc/netliberation/network_config.json
else
  echo "File /etc/netliberation/network_config.json NOT FOUND."
fi

echo -e "\n--- 8. PORT BINDINGS (LSOF / NETSTAT) ---"
lsof -i :53 -i :80 -i :8000 -i :67 -i :68 || netstat -tuln || true

echo -e "\n--- 9. IPTABLES NAT & FORWARDING RULES ---"
iptables -t nat -L -n -v || true
echo ""
iptables -L FORWARD -n -v || true

echo -e "\n--- 10. DIRECTORY STRUCTURE (/opt/netliberation) ---"
ls -la /opt/netliberation || true
echo ""
if [ -d /opt/netliberation/tests ]; then
  ls -la /opt/netliberation/tests || true
else
  echo "Directory /opt/netliberation/tests NOT FOUND."
fi

echo -e "\n--- 11. SYSTEMD JOURNAL LOGS (NETLIBERATION / HOSTAPD) ---"
journalctl -u netliberation -u hostapd -n 50 --no-pager || true

echo "================================================================"
echo " Diagnostic Report Saved to: $REPORT_FILE"
echo "================================================================"
