"""Identify the logged-in user from the Next.js `token` cookie (same JWT secret)."""
from __future__ import annotations

import jwt
from fastapi import HTTPException, Request

from .config import settings


def current_user_id(request: Request) -> str | None:
    token = request.cookies.get("token")
    if not token or not settings.jwt_secret:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    uid = payload.get("id")
    return str(uid) if uid else None


def require_user(request: Request) -> str:
    uid = current_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    return uid
