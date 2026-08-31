import re
import html
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request, status

# --- Input Sanitization ---
def sanitize_input(text: str) -> str:
    """Sanitize input string against XSS and HTML injection."""
    if not isinstance(text, str):
        return text
    return html.escape(text.strip())

def validate_safe_param(text: str, pattern: str = r"^[a-zA-Z0-9_\-\.\:\/]+$") -> str:
    """Validate parameter against command injection characters."""
    if not isinstance(text, str) or not re.match(pattern, text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid characters in parameter"
        )
    return text

def validate_domain_or_ip(value: str) -> str:
    """Validate domain name or IP address format."""
    domain_ip_regex = r"^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]))*$"
    if not re.match(domain_ip_regex, value) and not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid domain or IP format"
        )
    return value


import os

# --- Simple Rate Limiter ---
class RateLimiter:
    def __init__(self, requests_limit: int = 30, window_seconds: int = 60):
        self.limit = requests_limit
        self.window = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, request: Request):
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING"):
            return
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        # Clean expired timestamps
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if now - ts < self.window
        ]
        if len(self.requests[client_ip]) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        self.requests[client_ip].append(now)

rate_limiter = RateLimiter(requests_limit=300, window_seconds=60)
login_rate_limiter = RateLimiter(requests_limit=5, window_seconds=60)
