"""/api/auth/*: login, logout, demo login, current session."""
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from src.auth.rbac import SESSION_COOKIE, Principal, current_principal
from src.auth.security import verify_password
from src.auth.store import SESSION_TTL

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300
# ponytail: per-process limiter; move to the DB if running multiple workers.
_attempts: Dict[str, Deque[float]] = defaultdict(deque)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class DemoRequest(BaseModel):
    role: Literal["admin", "operator", "viewer"]


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _attempts[ip]
    while window and now - window[0] > LOGIN_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a few minutes.")
    window.append(now)


def _set_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), httponly=True,
        samesite="strict", secure=request.url.scheme == "https", path="/",
    )


def _me(principal: Principal) -> dict:
    return {
        "email": principal.email, "role": principal.role, "is_demo": principal.is_demo,
        "permissions": sorted(principal.permissions), "csrf_token": principal.csrf_token,
    }


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response) -> dict:
    _rate_limit(request)
    auth = request.app.state.auth
    user = auth.get_user_by_email(req.email)
    if not user or user["is_demo"] or user["disabled"] or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    session = auth.create_session(user["id"])
    auth.audit(user["id"], "login")
    _set_cookie(request, response, session["token"])
    return {"email": user["email"], "role": user["role"], "csrf_token": session["csrf_token"]}


@router.post("/demo")
def demo_login(req: DemoRequest, request: Request, response: Response) -> dict:
    if not request.app.state.settings.demo_enabled:
        raise HTTPException(status_code=404, detail="Demo mode is disabled.")
    auth = request.app.state.auth
    session = auth.create_session(auth.ensure_demo_user(req.role))
    _set_cookie(request, response, session["token"])
    return {"role": req.role, "is_demo": True, "csrf_token": session["csrf_token"]}


@router.post("/logout")
def logout(request: Request, response: Response, principal: Principal = Depends(current_principal)) -> dict:
    request.app.state.auth.delete_session(request.cookies.get(SESSION_COOKIE, ""))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "signed_out"}


@router.get("/me")
def me(principal: Principal = Depends(current_principal)) -> dict:
    return _me(principal)


@router.get("/config")
def auth_config(request: Request) -> dict:
    """Public: tells the login page whether to show demo cards."""
    return {"demo_enabled": request.app.state.settings.demo_enabled}
