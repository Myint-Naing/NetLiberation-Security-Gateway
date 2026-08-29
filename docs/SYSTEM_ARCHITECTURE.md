# NetLiberation Security Gateway - System Architecture & Networking

## 1. System Overview & Core Architecture
NetLiberation Security Gateway is a lightweight, high-performance network security router software suite designed for Debian Linux SBCs. It combines:
- **FastAPI Python Backend**: System controls, network state management, REST APIs, logging, and metrics.
- **Liquid Glass Web UI**: Single-Page Application (SPA) with Glassmorphic visual aesthetics.
- **Dynamic 4-Mode Router Engine**: Automated configuration generator for `hostapd`, `dnsmasq`, `wpa_supplicant`, `iptables`, and `nftables`.
- **eBlocker / AdGuard Home DNS Blocker**: Native domain filter parser, local port 53 DNS redirection, and DoH fallback.
- **Automated Multi-Protocol VPN Engine**: WireGuard, OpenVPN, L2TP, Shadowsocks (Outline), plus automated Cloudflare WARP and Outline key web-scraping & auto-renewal engines.

---

## 2. Dynamic 4-Mode Operation Modes

The system dynamically orchestrates Linux network interfaces into 4 distinct physical/logical topologies:

```
+-------------------------------------------------------------------------------+
| Mode A (Default): Eth WAN -> WLAN AP                                         |
| [Internet] <== (DHCP Client) ==> [eth0] --> [Routing/NAT] --> [wlan0 AP]     |
| Default LAN: 192.168.200.254/24 | DHCP Range: 192.168.200.20 - .200             |
+-------------------------------------------------------------------------------+
| Mode B: USB WLAN WAN -> WLAN AP                                               |
| [Internet] <== (Wi-Fi STA) ==> [wlan1] --> [Routing/NAT] --> [wlan0 AP]       |
+-------------------------------------------------------------------------------+
| Mode C: WLAN WAN -> USB WLAN AP                                               |
| [Internet] <== (Wi-Fi STA) ==> [wlan0] --> [Routing/NAT] --> [wlan1 AP]       |
+-------------------------------------------------------------------------------+
| Mode D: WLAN WAN Client -> Eth LAN                                            |
| [Internet] <== (Wi-Fi STA) ==> [wlan0] --> [Routing/NAT] --> [eth0 LAN]       |
+-------------------------------------------------------------------------------+
```

### Network Configuration Defaults
- **LAN Gateway IP**: `192.168.200.254`
- **Subnet Mask**: `255.255.255.0` (`/24`)
- **DHCP Range**: `192.168.200.20` to `192.168.200.200`
- **Primary DNS Handed to Clients**: `192.168.200.254` (Port 53)
- **Wi-Fi AP Defaults**: SSID `NetLiberation`, WPA2 Passphrase `Freedom4all`

---

## 3. DNS & Native Ad-Blocking Engine
1. **Inbound DNS Interception**: `iptables` / `nftables` redirects all outgoing UDP/TCP destination port 53 traffic from local LAN to `192.168.200.254:53`.
2. **Filter Parser**: Downloads filter lists (eBlocker, AdGuard Home, EasyList), extracts domains, normalizes ad domains into blocklist files read by `dnsmasq` (`address=/bad-domain.com/0.0.0.0`).
3. **Whitelist & Blacklist**: Custom user overrides checked prior to blocklists.
4. **Upstream & DoH Fallback**: Queries forwarded to secure upstream DNS servers (1.1.1.1, 8.8.8.8) with DNS-over-HTTPS (DoH) fallback client capability.

---

## 4. VPN Gateway & Automated Tunnel Routing

### Dynamic Routing Engine (`iptables` / `nftables`)
When VPN Master Switch is turned **ON**:
- Creates policy routing table and updates packet filtering rules.
- Redirects outgoing traffic from LAN interface through active VPN tunnel interface (`wg0`, `tun0`, or `ss-local` transparent proxy bridge).
- Performs Source NAT / Masquerade on the active tunnel interface.
- **Kill-Switch**: When active, blocks non-VPN outgoing forwarding on the physical WAN interface (`eth0`/`wlan0`/`wlan1`) if the VPN tunnel drops.
When VPN Master Switch is turned **OFF**:
- Restores default WAN interface masquerade and routing rules.

### Cloudflare WARP Automated Generator (`wireguard-warp-generator`)
- Generates a new WireGuard WARP account identity via Cloudflare API.
- Formats profile (`/etc/wireguard/warp.conf`).
- **Auto-Renewal Cron**: Evaluates configuration validity daily; regenerates and swaps key 2 days before expiration.

### Outline Key Scraper (`https://outlinekeys.com/protocols/outline/`)
- Scrapes Outline keys website for active "Online" servers.
- Parses `ss://` URI, decodes base64 payload into server address, port, cipher, and password.
- Generates Shadowsocks client config (`/etc/shadowsocks-libev/outline.json`).
- **Auto-Renewal Cron**: Tests connectivity daily; automatically re-scrapes and swaps key if server goes offline or connection times out.

---

## 5. Logging Infrastructure & 7-Day Retention
- Centralized system and operation logging daemon writing to `/var/log/netliberation/app.log`.
- Log levels: `INFO`, `WARNING`, `ERROR`.
- **Retention Cron**: Automated `logrotate` job daily purges logs older than 7 days to preserve SBC flash storage.

---

## 6. Installation & Uninstallation Engine

### `install.sh` Workflow
1. **Command Line Parsing**: Checks for `--uninstall` / `-u` flags (delegates to `uninstall.sh`).
2. **Root Verification**: Verifies root execution privileges.
3. **Hardware Diagnostics**: Checks RAM (>=1.5GB threshold warning) and thermal sensors.
4. **Port Conflict Check**: Detects occupied ports (53, 80, 67, 68) and prompts for service cleanup.
5. **Dependency Installation**: Installs hostapd, dnsmasq, iptables, WireGuard, Python packages, etc.
6. **Service Deployment**: Deploys `netliberation.service` systemd unit and copies backend/frontend code to `/opt/netliberation`.
7. **Cron Setup**: Registers 7-day log purge & VPN key renewal daily cron jobs.

### `uninstall.sh` Workflow
1. **Service Teardown**: Stops and disables `netliberation.service`, removes systemd unit file.
2. **Cron Removal**: Cleans up auto-maintenance and key renewal crontab entries.
3. **Firewall Reset**: Flushes custom iptables NAT and forwarding rules.
4. **Daemon Reset**: Stops hostapd and dnsmasq instances.
5. **File Purge**: Removes `/opt/netliberation`, `/etc/netliberation`, and `/var/log/netliberation`.
