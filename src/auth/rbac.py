"""Role permissions and the FastAPI dependencies that enforce them."""
from dataclasses import dataclass
from typing import Callable, FrozenSet

from fastapi import Depends, HTTPException, Request

SESSION_COOKIE = "aj_session"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_READ = {"data:read"}
_OPERATE = _READ | {"jobs:run", "agent:control", "browser:prefill", "applications:write"}
ROLE_PERMISSIONS = {
    "viewer": frozenset(_READ),
    "operator": frozenset(_OPERATE),
    "admin": frozenset(_OPERATE | {"profile:write", "console:use", "users:manage"}),
}


@dataclass(frozen=True)
class Principal:
    user_id: int
    email: str
    role: str
    is_demo: bool
    csrf_token: str

    @property
    def permissions(self) -> FrozenSet[str]:
        return ROLE_PERMISSIONS.get(self.role, frozenset())

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def current_principal(request: Request) -> Principal:
    token = request.cookies.get(SESSION_COOKIE)
    session = request.app.state.auth.get_session(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="Not signed in.")
    principal = Principal(
        user_id=session["user_id"], email=session["email"], role=session["role"],
        is_demo=bool(session["is_demo"]), csrf_token=session["csrf_token"],
    )
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != principal.csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid.")
    return principal


def require(permission: str) -> Callable[..., Principal]:
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.can(permission):
            raise HTTPException(status_code=403, detail=f"Your role cannot perform '{permission}'.")
        return principal
    return dependency


def workspace_for(request: Request, principal: Principal):
    state = request.app.state
    return state.demo_workspace if principal.is_demo else state.real_workspace
