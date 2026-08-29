import os
import json
import time
import secrets
import hashlib
from typing import Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

CONFIG_DIR = "/etc/netliberation" if os.access("/etc", os.W_OK) else "/tmp/netliberation"
CREDS_FILE = os.path.join(CONFIG_DIR, "credentials.json")

SESSION_STORE = {}
SESSION_EXPIRY_SECONDS = 86400

def _ensure_credentials():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CREDS_FILE):
        default_hash = hashlib.sha256("admin".encode()).hexdigest()
        data = {
            "username": "admin",
            "password_hash": default_hash
        }
        with open(CREDS_FILE, "w") as f:
            json.dump(data, f)

_ensure_credentials()

def _get_creds():
    _ensure_credentials()
    try:
        with open(CREDS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"username": "admin", "password_hash": hashlib.sha256("admin".encode()).hexdigest()}

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

def authenticate_user(req: LoginRequest) -> Optional[str]:
    creds = _get_creds()
    req_hash = hashlib.sha256(req.password.encode()).hexdigest()
    if req.username == creds["username"] and req_hash == creds["password_hash"]:
        token = secrets.token_hex(32)
        SESSION_STORE[token] = time.time() + SESSION_EXPIRY_SECONDS
        return token
    return None

def verify_session(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    token = authorization.split("Bearer ")[1].strip()
    expiry = SESSION_STORE.get(token)
    if not expiry or time.time() > expiry:
        if token in SESSION_STORE:
            del SESSION_STORE[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )
    return token

def logout_user(token: str):
    if token in SESSION_STORE:
        del SESSION_STORE[token]

def update_password(old_pass: str, new_pass: str) -> bool:
    creds = _get_creds()
    old_hash = hashlib.sha256(old_pass.encode()).hexdigest()
    if old_hash != creds["password_hash"]:
        return False

    new_hash = hashlib.sha256(new_pass.encode()).hexdigest()
    creds["password_hash"] = new_hash
    with open(CREDS_FILE, "w") as f:
        json.dump(creds, f)
    return True
