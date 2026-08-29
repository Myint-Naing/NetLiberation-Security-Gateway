from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os

from backend.security import rate_limiter, login_rate_limiter, sanitize_input, validate_domain_or_ip
from backend.auth import (
    LoginRequest,
    PasswordChangeRequest,
    authenticate_user,
    verify_session,
    logout_user,
    update_password
)
from backend.system import (
    GovernorRequest,
    get_system_metrics,
    set_cpu_governor,
    reboot_system,
    shutdown_system
)
from backend.network import (
    NetworkModeRequest,
    LanConfigRequest,
    WanConfigRequest,
    get_network_config,
    save_network_config,
    apply_network_mode,
    get_dhcp_clients,
    scan_wifi_networks
)
from backend.dns_engine import (
    DnsToggleRequest,
    DomainRuleRequest,
    FilterListRequest,
    get_dns_config,
    save_dns_config,
    sync_adblock_filters,
    get_dns_query_logs
)
from backend.vpn import (
    VpnToggleRequest,
    ProfileUploadRequest,
    get_vpn_state,
    toggle_vpn
)
from backend.warp import generate_cloudflare_warp_key, check_and_renew_warp_key
from backend.outline import fetch_active_outline_key
from backend.tools import (
    PingRequest,
    TracerouteRequest,
    NslookupRequest,
    run_ping,
    run_traceroute,
    run_nslookup,
    run_speedtest
)
from backend.logging_service import (
    get_logging_config,
    save_logging_config,
    log_event,
    get_logs,
    purge_old_logs
)

class LoggingToggleRequest(BaseModel):
    enabled: bool

app = FastAPI(title="NetLiberation Security Gateway API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api"):
        try:
            if request.url.path == "/api/auth/login":
                login_rate_limiter.check(request)
            else:
                rate_limiter.check(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    response = await call_next(request)
    return response

# --- Auth Endpoints ---
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    token = authenticate_user(req)
    if not token:
        log_event("WARNING", f"Failed login attempt for user: {req.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    log_event("INFO", f"User logged in successfully: {req.username}")
    return {"status": "success", "token": token, "expires_in": 86400}

@app.post("/api/auth/logout")
async def logout(token: str = Depends(verify_session)):
    logout_user(token)
    return {"status": "success"}

@app.post("/api/auth/change-password")
async def change_password(req: PasswordChangeRequest, token: str = Depends(verify_session)):
    if not update_password(req.old_password, req.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password incorrect"
        )
    log_event("INFO", "Admin password changed successfully.")
    return {"status": "success"}

# --- System Metrics & Controls ---
@app.get("/api/system/metrics")
async def metrics(token: str = Depends(verify_session)):
    return get_system_metrics()

@app.post("/api/system/governor")
async def set_governor(req: GovernorRequest, token: str = Depends(verify_session)):
    success = set_cpu_governor(req.governor)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to set CPU governor")
    log_event("INFO", f"CPU Governor updated to {req.governor}")
    return {"status": "success", "governor": req.governor}

@app.post("/api/system/reboot")
async def reboot(token: str = Depends(verify_session)):
    log_event("WARNING", "System reboot initiated via API.")
    reboot_system()
    return {"status": "success", "message": "Rebooting system..."}

@app.post("/api/system/shutdown")
async def shutdown(token: str = Depends(verify_session)):
    log_event("WARNING", "System shutdown initiated via API.")
    shutdown_system()
    return {"status": "success", "message": "Shutting down system..."}

# --- Network Management ---
@app.get("/api/network/status")
async def network_status(token: str = Depends(verify_session)):
    return get_network_config()

@app.post("/api/network/mode")
async def switch_mode(req: NetworkModeRequest, token: str = Depends(verify_session)):
    if req.mode not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Invalid operation mode")
    success = apply_network_mode(req.mode)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to apply network mode")
    log_event("INFO", f"Operation Mode switched to Mode {req.mode}")
    return {"status": "success", "mode": req.mode}

@app.post("/api/network/lan")
async def configure_lan(req: LanConfigRequest, token: str = Depends(verify_session)):
    cfg = get_network_config()
    cfg["lan"].update(req.dict())
    save_network_config(cfg)
    apply_network_mode(cfg["mode"])
    log_event("INFO", f"LAN Gateway IP updated to {req.ip}")
    return {"status": "success", "lan": cfg["lan"]}

@app.get("/api/network/dhcp-clients")
async def dhcp_clients(token: str = Depends(verify_session)):
    return get_dhcp_clients()

@app.get("/api/network/wifi-scan")
async def wifi_scan(iface: str = "wlan0", token: str = Depends(verify_session)):
    return scan_wifi_networks(iface)

# --- VPN Gateway Endpoints ---
@app.get("/api/vpn/status")
async def vpn_status(token: str = Depends(verify_session)):
    return get_vpn_state()

@app.post("/api/vpn/toggle")
async def vpn_toggle(req: VpnToggleRequest, token: str = Depends(verify_session)):
    res = toggle_vpn(req.enabled, req.protocol, req.kill_switch)
    log_event("INFO", f"VPN routing toggled: enabled={req.enabled}, protocol={req.protocol}")
    return res

@app.post("/api/vpn/warp/generate")
async def vpn_warp_generate(token: str = Depends(verify_session)):
    res = generate_cloudflare_warp_key()
    toggle_vpn(True, "wireguard", True)
    log_event("INFO", "Cloudflare WARP profile generated and activated.")
    return res

@app.post("/api/vpn/outline/fetch")
async def vpn_outline_fetch(token: str = Depends(verify_session)):
    res = fetch_active_outline_key()
    toggle_vpn(True, "shadowsocks", True)
    log_event("INFO", "Outline server key fetched and activated.")
    return res

# --- Security & DNS Engine ---
@app.get("/api/dns/status")
async def dns_status(token: str = Depends(verify_session)):
    return get_dns_config()

@app.post("/api/dns/toggle")
async def dns_toggle(req: DnsToggleRequest, token: str = Depends(verify_session)):
    cfg = get_dns_config()
    cfg["enabled"] = req.enabled
    save_dns_config(cfg)
    log_event("INFO", f"Master Ad-Blocker toggled to {req.enabled}")
    return {"status": "success", "enabled": req.enabled}

@app.get("/api/dns/logs")
async def dns_logs(token: str = Depends(verify_session)):
    return get_dns_query_logs()

@app.post("/api/dns/sync-filters")
async def dns_sync(token: str = Depends(verify_session)):
    count = sync_adblock_filters()
    log_event("INFO", f"Ad-blocker filter lists synced. {count} domains blocked.")
    return {"status": "success", "blocked_domains_count": count}

@app.post("/api/dns/whitelist")
async def add_whitelist(req: DomainRuleRequest, token: str = Depends(verify_session)):
    domain = validate_domain_or_ip(req.domain.lower())
    cfg = get_dns_config()
    if domain not in cfg["whitelist"]:
        cfg["whitelist"].append(domain)
        if domain in cfg["blacklist"]:
            cfg["blacklist"].remove(domain)
        save_dns_config(cfg)
    return {"status": "success", "whitelist": cfg["whitelist"]}

@app.post("/api/dns/blacklist")
async def add_blacklist(req: DomainRuleRequest, token: str = Depends(verify_session)):
    domain = validate_domain_or_ip(req.domain.lower())
    cfg = get_dns_config()
    if domain not in cfg["blacklist"]:
        cfg["blacklist"].append(domain)
        if domain in cfg["whitelist"]:
            cfg["whitelist"].remove(domain)
        save_dns_config(cfg)
    return {"status": "success", "blacklist": cfg["blacklist"]}

# --- Logging & Diagnostics ---
@app.get("/api/logs")
async def get_system_logs(level: str = "ALL", token: str = Depends(verify_session)):
    return get_logs(level)

@app.post("/api/logs/toggle")
async def toggle_operation_logging(req: LoggingToggleRequest, token: str = Depends(verify_session)):
    cfg = get_logging_config()
    cfg["logging_enabled"] = req.enabled
    save_logging_config(cfg)
    return {"status": "success", "logging_enabled": req.enabled}

@app.post("/api/tools/ping")
async def tool_ping(req: PingRequest, token: str = Depends(verify_session)):
    out = run_ping(req.target, req.count)
    return {"status": "success", "output": out}

@app.post("/api/tools/traceroute")
async def tool_traceroute(req: TracerouteRequest, token: str = Depends(verify_session)):
    out = run_traceroute(req.target)
    return {"status": "success", "output": out}

@app.post("/api/tools/nslookup")
async def tool_nslookup(req: NslookupRequest, token: str = Depends(verify_session)):
    out = run_nslookup(req.domain)
    return {"status": "success", "output": out}

@app.post("/api/tools/speedtest")
async def tool_speedtest(token: str = Depends(verify_session)):
    out = run_speedtest()
    return {"status": "success", "results": out}

# --- Static Files & Web UI Serving ---
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))
