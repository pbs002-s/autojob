"""/api/users: admin user management and audit log."""
import sqlite3
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.rbac import Principal, require
from src.auth.security import MIN_PASSWORD_LENGTH

router = APIRouter(prefix="/api/users", tags=["users"])
Role = Literal["admin", "operator", "viewer"]


class CreateUser(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    role: Role


class UpdateUser(BaseModel):
    role: Optional[Role] = None
    disabled: Optional[bool] = None


def _block_demo(p: Principal) -> None:
    if p.is_demo:
        raise HTTPException(status_code=403, detail="User management is read-only in demo mode.")


@router.get("")
def list_users(request: Request, p: Principal = Depends(require("users:manage"))) -> list:
    if p.is_demo:
        return [{"id": 0, "email": "you@demo", "role": p.role, "is_demo": 1, "disabled": 0, "created_at": ""}]
    return request.app.state.auth.list_users()


@router.post("", status_code=201)
def create_user(req: CreateUser, request: Request, p: Principal = Depends(require("users:manage"))) -> dict:
    _block_demo(p)
    auth = request.app.state.auth
    try:
        user_id = auth.create_user(req.email, req.password, req.role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A user with that email already exists.")
    auth.audit(p.user_id, "user:create", req.email)
    return {"id": user_id, "email": req.email.lower(), "role": req.role}


@router.patch("/{user_id}")
def update_user(user_id: int, req: UpdateUser, request: Request,
                p: Principal = Depends(require("users:manage"))) -> dict:
    _block_demo(p)
    auth = request.app.state.auth
    target = auth.get_user(user_id)
    if not target or target["is_demo"]:
        raise HTTPException(status_code=404, detail="User not found.")
    demoting_last_admin = target["role"] == "admin" and (req.role not in (None, "admin") or req.disabled) \
        and auth.count_admins() <= 1
    if demoting_last_admin:
        raise HTTPException(status_code=409, detail="Cannot demote or disable the last admin.")
    auth.update_user(user_id, role=req.role, disabled=req.disabled)
    auth.audit(p.user_id, "user:update", f"{target['email']} role={req.role} disabled={req.disabled}")
    return {"status": "success"}


@router.get("/audit")
def audit_log(request: Request, p: Principal = Depends(require("users:manage"))) -> list:
    return [] if p.is_demo else request.app.state.auth.list_audit()
