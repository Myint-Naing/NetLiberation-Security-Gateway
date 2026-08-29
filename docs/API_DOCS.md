# NetLiberation Security Gateway - API Specifications

Base URL: `http://192.168.200.254/api`

## Authentication API

### POST `/api/auth/login`
Authenticate user session.
- **Request Body**: `{"username": "admin", "password": "..."}`
- **Response**: `{"status": "success", "token": "...", "expires_in": 86400}`

### POST `/api/auth/logout`
Logout active session.
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `{"status": "success"}`

### POST `/api/auth/change-password`
Change admin login password.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**: `{"old_password": "...", "new_password": "..."}`
- **Response**: `{"status": "success"}`

---

## System Metrics API

### GET `/api/system/metrics`
Retrieve live CPU, RAM, SOC temperature, disk usage, and power status.
- **Response**:
```json
{
  "cpu_percent": 12.5,
  "soc_temp_c": 44.2,
  "ram": {"total_mb": 2048, "used_mb": 420, "percent": 20.5},
  "disk": {"total_gb": 16.0, "used_gb": 3.2, "percent": 20.0},
  "governor": "schedutil",
  "throttled": false
}
```

### POST `/api/system/governor`
Set CPU frequency governor.
- **Request Body**: `{"governor": "schedutil" | "performance" | "powersave"}`

### POST `/api/system/reboot`
Trigger system reboot.

### POST `/api/system/shutdown`
Trigger system shutdown.

---

## Network & Operation Mode API

### GET `/api/network/status`
Get current operation mode, interfaces, LAN configuration, and active WAN status.

### POST `/api/network/mode`
Switch operation mode (A, B, C, or D).
- **Request Body**: `{"mode": "A" | "B" | "C" | "D"}`

### POST `/api/network/lan`
Configure LAN IP, gateway, and DHCP pool.
- **Request Body**: `{"ip": "192.168.200.254", "dhcp_start": "192.168.200.20", "dhcp_end": "192.168.200.200", "ssid": "NetLiberation", "password": "Freedom4all"}`

### GET `/api/network/dhcp-clients`
Get list of active DHCP clients (MAC, IP, Hostname, Active time, Bandwidth).

### GET `/api/network/wifi-scan`
Scan available Wi-Fi access points for WAN Wi-Fi connection.

---

## VPN Management API

### GET `/api/vpn/status`
Get current VPN connection state, active profile, protocol, IP, and traffic metrics.

### POST `/api/vpn/toggle`
Enable or disable global VPN tunnel routing.
- **Request Body**: `{"enabled": true | false, "kill_switch": true | false}`

### POST `/api/vpn/warp/generate`
Trigger Cloudflare WARP account generation and connection.

### POST `/api/vpn/outline/fetch`
Trigger web scraper to fetch active Outline key from outlinekeys.com and connect.

### POST `/api/vpn/upload-profile`
Upload custom WireGuard (`.conf`) or OpenVPN (`.ovpn`) profile.

---

## Security & DNS Blocker API

### GET `/api/dns/status`
Get ad-blocker status, total blocked domains count, and active lists count.

### POST `/api/dns/toggle`
Enable or disable master ad-blocker.
- **Request Body**: `{"enabled": true | false}`

### GET `/api/dns/logs`
Get real-time DNS query log stream.

### POST `/api/dns/whitelist`
Add or remove domain on custom whitelist.

### POST `/api/dns/blacklist`
Add or remove domain on custom blacklist.

---

## Logging & Diagnostics API

### GET `/api/logs`
View system logs with level filter (`INFO`, `WARNING`, `ERROR`).

### POST `/api/tools/ping`
Run ping diagnostic.
- **Request Body**: `{"target": "8.8.8.8", "count": 4}`

### POST `/api/tools/traceroute`
Run traceroute diagnostic.
- **Request Body**: `{"target": "1.1.1.1"}`

### POST `/api/tools/nslookup`
Run nslookup query.
- **Request Body**: `{"domain": "example.com"}`

### POST `/api/tools/speedtest`
Run Speedtest benchmark.
