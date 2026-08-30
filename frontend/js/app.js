/* NetLiberation Web UI Application Frontend Engine */
const API_BASE = '/api';
let authToken = localStorage.getItem('token') || '';

function toggleMobileMenu() {
  const links = document.getElementById('main-nav-links');
  if (links) links.classList.toggle('open');
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));

  const targetContent = document.getElementById(`tab-${tabId}`);
  if (targetContent) targetContent.classList.add('active');

  const navTab = document.querySelector(`.nav-tab[onclick*="'${tabId}'"]`);
  if (navTab) navTab.classList.add('active');

  // Close mobile drawer on tab click
  const links = document.getElementById('main-nav-links');
  if (links) links.classList.remove('open');

  if (tabId === 'dashboard') loadDashboardData();
  if (tabId === 'network') loadNetworkConfig();
  if (tabId === 'vpn') loadVpnConfig();
  if (tabId === 'security') loadSecurityConfig();
  if (tabId === 'admin') loadSystemLogs();
}

async function apiRequest(endpoint, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

  try {
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}${endpoint}`, opts);
    if (res.status === 401 && endpoint !== '/auth/login') {
      showLoginModal();
      return null;
    }
    if (res.ok) return await res.json();
  } catch (err) {
    console.error(`API Error ${endpoint}:`, err);
  }
  return null;
}

function showLoginModal() {
  const modal = document.getElementById('modal-login');
  if (modal) modal.style.display = 'flex';
}

function hideLoginModal() {
  const modal = document.getElementById('modal-login');
  if (modal) modal.style.display = 'none';
}

async function performLogin() {
  const user = document.getElementById('login-username').value || 'admin';
  const pass = document.getElementById('login-password').value || 'admin';

  const res = await apiRequest('/auth/login', 'POST', { username: user, password: pass });
  if (res && res.token) {
    authToken = res.token;
    localStorage.setItem('token', authToken);
    hideLoginModal();
    loadDashboardData();
  } else {
    alert('Invalid login credentials');
  }
}

function performLogout() {
  authToken = '';
  localStorage.removeItem('token');
  showLoginModal();
}

async function loadDashboardData() {
  if (!authToken) {
    showLoginModal();
    return;
  }

  const metrics = await apiRequest('/system/metrics');
  if (metrics) {
    document.getElementById('val-cpu').innerText = `${metrics.cpu_percent}%`;
    document.getElementById('val-temp').innerText = `${metrics.soc_temp_c}°C`;
    document.getElementById('val-governor').innerText = metrics.governor;
    document.getElementById('val-ram').innerText = `${metrics.ram.used_mb} MB`;
    document.getElementById('val-ram-pct').innerText = `${metrics.ram.percent}%`;

    const thermalBadge = document.getElementById('val-thermal-status');
    if (metrics.throttled) {
      thermalBadge.className = 'badge badge-danger';
      thermalBadge.innerText = 'Throttled';
    } else {
      thermalBadge.className = 'badge badge-success';
      thermalBadge.innerText = 'Normal';
    }
  }

  const ipInfo = await apiRequest('/network/ip-details');
  if (ipInfo) {
    document.getElementById('val-wan-ip').innerText = ipInfo.wan_ip;
    document.getElementById('val-lan-ip').innerText = ipInfo.lan_ip;
    document.getElementById('val-remote-vpn-ip').innerText = ipInfo.vpn_ip;
  }

  const vpn = await apiRequest('/vpn/status');
  if (vpn) {
    document.getElementById('val-vpn-status').innerText = vpn.status;
    const vpnBadge = document.getElementById('val-vpn-badge');
    if (vpn.enabled) {
      vpnBadge.className = 'badge badge-success';
      vpnBadge.innerText = 'Protected (Tunnel)';
    } else {
      vpnBadge.className = 'badge badge-danger';
      vpnBadge.innerText = 'Direct WAN';
    }
  }

  const clients = await apiRequest('/network/dhcp-clients');
  if (clients) {
    const tbody = document.getElementById('table-dhcp-clients');
    tbody.innerHTML = clients.map(c => `
      <tr>
        <td>${c.hostname}</td>
        <td>${c.ip}</td>
        <td>${c.mac}</td>
        <td>${c.bandwidth_dl} / ${c.bandwidth_ul}</td>
      </tr>
    `).join('');
  }

  const dnsLogs = await apiRequest('/dns/logs');
  if (dnsLogs) {
    const tbody = document.getElementById('table-dns-stream');
    tbody.innerHTML = dnsLogs.slice(0, 5).map(l => `
      <tr>
        <td>${l.timestamp.split(' ')[1] || l.timestamp}</td>
        <td>${l.client_ip}</td>
        <td>${l.domain}</td>
        <td><span class="badge ${l.status === 'Blocked' ? 'badge-danger' : 'badge-success'}">${l.status}</span></td>
      </tr>
    `).join('');
  }
}

// --- Tab 2: Network Functions ---
async function loadNetworkConfig() {
  const net = await apiRequest('/network/status');
  if (net) {
    document.getElementById('select-op-mode').value = net.mode;
    document.getElementById('input-lan-ip').value = net.lan.ip;
    document.getElementById('input-dhcp-start').value = net.lan.dhcp_start || '192.168.200.20';
    document.getElementById('input-dhcp-end').value = net.lan.dhcp_end || '192.168.200.200';
    document.getElementById('input-wifi-ssid').value = net.lan.ssid;
    document.getElementById('input-wifi-pass').value = net.lan.password || 'Freedom4all';
    document.getElementById('select-wifi-channel').value = net.lan.channel || 6;
  }
}

async function applyOperationMode() {
  const mode = document.getElementById('select-op-mode').value;
  const res = await apiRequest('/network/mode', 'POST', { mode });
  if (res) alert(`Operation Mode ${mode} applied successfully!`);
}

async function saveLanScopeSettings() {
  const ip = document.getElementById('input-lan-ip').value;
  const dhcp_start = document.getElementById('input-dhcp-start').value;
  const dhcp_end = document.getElementById('input-dhcp-end').value;
  const res = await apiRequest('/network/lan-scope', 'POST', { ip, dhcp_start, dhcp_end });
  if (res) alert('LAN Configuration Scope saved successfully!');
}

async function saveWifiApSettings() {
  const ssid = document.getElementById('input-wifi-ssid').value;
  const password = document.getElementById('input-wifi-pass').value;
  const channel = parseInt(document.getElementById('select-wifi-channel').value, 10);
  const res = await apiRequest('/network/wifi-ap', 'POST', { ssid, password, channel });
  if (res) alert('Wi-Fi Access Point Settings saved successfully!');
}

async function scanWifiNetworks() {
  const tbody = document.getElementById('table-wifi-scan');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="3">Scanning Wi-Fi networks...</td></tr>';
  const networks = await apiRequest('/network/wifi-scan');
  if (networks && networks.length > 0) {
    tbody.innerHTML = networks.map(n => `
      <tr>
        <td><strong>${n.ssid}</strong></td>
        <td>${n.signal}</td>
        <td><button class="btn btn-accent" style="padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="selectWifiSsid('${n.ssid}')">Connect</button></td>
      </tr>
    `).join('');
  } else {
    tbody.innerHTML = '<tr><td colspan="3">No networks found.</td></tr>';
  }
}

function selectWifiSsid(ssid) {
  const input = document.getElementById('input-wan-wifi-ssid');
  if (input) input.value = ssid;
}

async function connectWanWifi() {
  const ssid = document.getElementById('input-wan-wifi-ssid').value;
  const password = document.getElementById('input-wan-wifi-pass').value;
  if (!ssid) return alert('Please enter or select a Wi-Fi SSID');
  const res = await apiRequest('/network/wifi-connect', 'POST', { ssid, password });
  if (res) alert(`WAN uplink connected to Wi-Fi SSID '${ssid}' successfully!`);
}

// --- Tab 3: VPN Client Functions ---
function updateVpnProtocolFields() {
  const proto = document.getElementById('select-vpn-protocol').value;
  const labelFile = document.getElementById('label-vpn-file');
  const labelRaw = document.getElementById('label-vpn-raw');
  const rawInput = document.getElementById('input-vpn-raw');

  if (proto === 'wireguard') {
    labelFile.innerText = 'Upload WireGuard Profile (.conf)';
    labelRaw.innerText = 'Or Paste WireGuard Configuration File Content';
    rawInput.placeholder = '[Interface]\nPrivateKey = ...\nAddress = ...\n[Peer]\nPublicKey = ...';
  } else if (proto === 'openvpn') {
    labelFile.innerText = 'Upload OpenVPN Profile (.ovpn)';
    labelRaw.innerText = 'Or Paste OpenVPN Configuration File Content';
    rawInput.placeholder = 'client\ndev tun\nproto udp\nremote my-server.com 1194...';
  } else if (proto === 'l2tp') {
    labelFile.innerText = 'Upload L2TP/IPsec Configuration';
    labelRaw.innerText = 'Or Paste L2TP Server, IPSec PSK & Credentials';
    rawInput.placeholder = 'Server = 1.2.3.4\nPSK = secret\nUsername = user\nPassword = pass';
  } else if (proto === 'shadowsocks') {
    labelFile.innerText = 'Upload Shadowsocks JSON Config';
    labelRaw.innerText = 'Or Paste Shadowsocks ss:// URI Key / Base64 Payload';
    rawInput.placeholder = 'ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNjpwYXNzQDEuMi4zLjQ6ODM4OA==#OutlineServer';
  }
}

async function loadVpnConfig() {
  const vpn = await apiRequest('/vpn/status');
  if (vpn) {
    const btn = document.getElementById('btn-vpn-toggle');
    btn.innerText = vpn.enabled ? 'Disable VPN Tunnel' : 'Enable VPN Tunnel';
    btn.className = vpn.enabled ? 'btn btn-danger' : 'btn btn-primary';
    document.getElementById('select-vpn-protocol').value = vpn.active_protocol || 'wireguard';
    updateVpnProtocolFields();
  }
}

async function toggleVpnMaster() {
  const vpn = await apiRequest('/vpn/status');
  const targetState = !(vpn && vpn.enabled);
  const protocol = document.getElementById('select-vpn-protocol').value;
  const killSwitch = document.getElementById('chk-killswitch').checked;
  const res = await apiRequest('/vpn/toggle', 'POST', { enabled: targetState, protocol, kill_switch: killSwitch });
  if (res) {
    loadVpnConfig();
    loadDashboardData();
  }
}

async function generateWarp() {
  const metaBox = document.getElementById('box-vpn-meta');
  metaBox.innerText = 'Generating Cloudflare WARP key & registering account...';
  const res = await apiRequest('/vpn/warp/generate', 'POST');
  if (res) {
    metaBox.innerText = JSON.stringify(res.meta, null, 2);
    loadDashboardData();
  }
}

async function fetchOutlineKey() {
  const metaBox = document.getElementById('box-vpn-meta');
  metaBox.innerText = 'Scraping outlinekeys.com for active online servers...';
  const res = await apiRequest('/vpn/outline/fetch', 'POST');
  if (res) {
    metaBox.innerText = JSON.stringify(res.meta, null, 2);
    loadDashboardData();
  }
}

async function uploadVpnProfile() {
  const proto = document.getElementById('select-vpn-protocol').value;
  const fileInput = document.getElementById('input-vpn-file');
  const textInput = document.getElementById('input-vpn-raw');
  const metaBox = document.getElementById('box-vpn-meta');

  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];
    const reader = new FileReader();
    reader.onload = async function(e) {
      const content = e.target.result;
      const res = await apiRequest('/vpn/profile/upload', 'POST', { protocol: proto, filename: file.name, content });
      metaBox.innerText = `Uploaded VPN Profile '${file.name}' for protocol '${proto}':\n` + content;
      alert(`VPN Profile '${file.name}' imported successfully!`);
    };
    reader.readAsText(file);
  } else if (textInput.value.trim().length > 0) {
    const content = textInput.value.trim();
    const res = await apiRequest('/vpn/profile/raw', 'POST', { protocol: proto, content });
    metaBox.innerText = `Imported Custom Config for protocol '${proto}':\n` + content;
    alert(`VPN Credentials / Config for '${proto}' imported successfully!`);
  } else {
    alert('Please select a file or enter configuration credentials.');
  }
}

// --- Tab 4: Security Functions ---
async function loadSecurityConfig() {
  const dns = await apiRequest('/dns/status');
  if (dns) {
    document.getElementById('val-blocked-domains').innerText = dns.total_blocked_count.toLocaleString();
    const btn = document.getElementById('btn-dns-toggle');
    btn.innerText = dns.enabled ? 'Master Blocker: Enabled' : 'Master Blocker: Disabled';
    btn.className = dns.enabled ? 'btn btn-primary' : 'btn btn-danger';

    const box = document.getElementById('box-filter-feeds');
    if (box && dns.blocklist_urls) {
      box.innerHTML = dns.blocklist_urls.map(url => `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; border-bottom: 1px solid var(--glass-border); padding-bottom: 0.2rem;">
          <span style="font-size: 0.8rem; word-break: break-all;">${url}</span>
          <button class="btn btn-danger" style="padding: 0.2rem 0.5rem; font-size: 0.75rem; min-height: auto;" onclick="removeFilterFeedUrl('${url}')">Remove</button>
        </div>
      `).join('');
    }
  }
}

async function addFilterFeedUrl() {
  const url = document.getElementById('input-filter-url').value.trim();
  if (!url) return alert('Please enter a filter list URL');
  const res = await apiRequest('/dns/filter-list/add', 'POST', { url });
  if (res) {
    document.getElementById('input-filter-url').value = '';
    loadSecurityConfig();
    alert('Adblock filter list URL added successfully!');
  }
}

async function removeFilterFeedUrl(url) {
  if (confirm(`Remove filter feed '${url}'?`)) {
    const res = await apiRequest('/dns/filter-list/remove', 'POST', { url });
    if (res) loadSecurityConfig();
  }
}

async function toggleDnsMaster() {
  const dns = await apiRequest('/dns/status');
  const res = await apiRequest('/dns/toggle', 'POST', { enabled: !(dns && dns.enabled) });
  if (res) loadSecurityConfig();
}

async function syncAdblockLists() {
  alert('Syncing filter feeds. This takes a few seconds...');
  const res = await apiRequest('/dns/sync-filters', 'POST');
  if (res) {
    alert(`Filter sync complete! Total blocked domains: ${res.blocked_domains_count}`);
    loadSecurityConfig();
  }
}

async function addDomainWhitelist() {
  const domain = document.getElementById('input-domain-rule').value;
  if (!domain) return alert('Please enter a domain');
  const res = await apiRequest('/dns/whitelist', 'POST', { domain });
  if (res) alert(`Domain ${domain} added to Whitelist`);
}

async function addDomainBlacklist() {
  const domain = document.getElementById('input-domain-rule').value;
  if (!domain) return alert('Please enter a domain');
  const res = await apiRequest('/dns/blacklist', 'POST', { domain });
  if (res) alert(`Domain ${domain} added to Blacklist`);
}

// --- Tab 5: Administration Functions ---
async function loadSystemLogs() {
  const logs = await apiRequest('/logs');
  if (logs) {
    document.getElementById('box-sys-logs').innerText = logs.map(l => `[${l.timestamp}] [${l.level}] ${l.message}`).join('\n');
  }
}

async function changeGovernor() {
  const governor = document.getElementById('select-governor').value;
  const res = await apiRequest('/system/governor', 'POST', { governor });
  if (res) alert(`CPU Governor switched to ${governor}`);
}

async function saveScheduledReboot() {
  const enabled = document.getElementById('chk-sched-reboot').checked;
  const timeStr = document.getElementById('time-sched-reboot').value;
  const res = await apiRequest('/system/scheduled-reboot', 'POST', { enabled, time: timeStr, frequency: 'daily' });
  if (res) alert(`Scheduled reboot configuration updated!`);
}

async function rebootSystem() {
  if (confirm('Are you sure you want to reboot the NetLiberation Gateway?')) {
    await apiRequest('/system/reboot', 'POST');
    alert('Reboot signal sent.');
  }
}

async function shutdownSystem() {
  if (confirm('Are you sure you want to shutdown the NetLiberation Gateway?')) {
    await apiRequest('/system/shutdown', 'POST');
    alert('Shutdown signal sent.');
  }
}

// --- Tab 6: Tools Functions ---
async function runPingTool() {
  const target = document.getElementById('input-ping-target').value;
  const box = document.getElementById('box-ping-output');
  box.innerText = `Executing Ping to ${target}...`;
  const res = await apiRequest('/tools/ping', 'POST', { target, count: 4 });
  if (res) box.innerText = res.output;
}

async function runTracerouteTool() {
  const target = document.getElementById('input-trace-target').value;
  const box = document.getElementById('box-trace-output');
  box.innerText = `Executing Traceroute to ${target}...`;
  const res = await apiRequest('/tools/traceroute', 'POST', { target });
  if (res) box.innerText = res.output;
}

async function runNslookupTool() {
  const domain = document.getElementById('input-lookup-domain').value;
  const box = document.getElementById('box-lookup-output');
  box.innerText = `Executing Nslookup for ${domain}...`;
  const res = await apiRequest('/tools/nslookup', 'POST', { domain });
  if (res) box.innerText = res.output;
}

async function runSpeedtestTool() {
  const box = document.getElementById('box-speedtest-output');
  box.innerText = 'Running Speedtest benchmark (Download/Upload speed test)...';
  const res = await apiRequest('/tools/speedtest', 'POST');
  if (res) {
    const d = res.results;
    box.innerText = `Speedtest Results:
Download Speed: ${(d.download / (1024*1024)).toFixed(2)} Mbps
Upload Speed: ${(d.upload / (1024*1024)).toFixed(2)} Mbps
Ping Latency: ${d.ping} ms
Server: ${d.server.name} (${d.server.country})`;
  }
}

// Auto Refresh Intervals
setInterval(() => {
  const activeTab = document.querySelector('.tab-content.active');
  if (activeTab && authToken) {
    if (activeTab.id === 'tab-dashboard') loadDashboardData();
    if (activeTab.id === 'tab-admin') loadSystemLogs();
  }
}, 3000);

document.addEventListener('DOMContentLoaded', () => {
  if (!authToken) {
    showLoginModal();
  } else {
    loadDashboardData();
  }
});
