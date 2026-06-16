"""
Go Farm Work - Authentication Module
Handles JWT (email/password) + Google OAuth session tokens.
"""
import os
import uuid
import bcrypt
import jwt
import requests
from datetime import datetime, timezone, timedelta
from werkzeug.exceptions import Unauthorized
from typing import Optional
from functools import wraps
from flask import request, g, current_app, jsonify
from pydantic import ValidationError

JWT_SECRET = os.environ.get("JWT_SECRET", "gofarmwork-fallback-dev")
JWT_ALGO = "HS256"
GOOGLE_AUTH_URL = os.environ.get(
    "GOOGLE_AUTH_URL",
    "https://api.gofarmwork.com/auth/v1/env/oauth/session-data",
)

# ---------- Password utilities ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

# ---------- JWT ----------
def create_jwt(user_id: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp()),
        "kind": "jwt",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except Exception:
        return None

# ---------- Google Auth ----------
def exchange_google_session(session_id: str) -> dict:
    resp = requests.get(
        GOOGLE_AUTH_URL, headers={"X-Session-ID": session_id}, timeout=15.0
    )
    if resp.status_code != 200:
        raise Unauthorized("Invalid Google session")
    return resp.json()

# ---------- Auth extraction ----------
def get_current_user(db) -> dict:
    """
    Extract user from either:
    - Cookie `session_token` (Google Auth)
    - Authorization: Bearer <token> (JWT or session_token)
    """
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise Unauthorized("Not authenticated")

    # Try JWT first
    payload = decode_jwt(token)
    if payload and payload.get("sub"):
        user = db.users.find_one({"user_id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise Unauthorized("User not found")
        return user

    # Try Google session token
    session = db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise Unauthorized("Invalid session")

    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise Unauthorized("Session expired")

    user = db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise Unauthorized("User not found")
    return user

def new_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"

def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

# ---------- Flask Decorators ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        db = current_app.db
        g.current_user = get_current_user(db)
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        db = current_app.db
        user = get_current_user(db)
        if user.get("role") != "admin":
            from werkzeug.exceptions import Forbidden
            raise Forbidden("Admin only")
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def validate_schema(schema_class):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                data = request.get_json() or {}
            except Exception:
                return jsonify({"detail": "Invalid JSON"}), 400
            try:
                body = schema_class(**data)
            except ValidationError as e:
                return jsonify({"detail": e.errors()}), 422
            return f(body, *args, **kwargs)
        return decorated
    return decorator
