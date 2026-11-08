"""/api/contact: read and edit the candidate dossier."""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from src.auth.rbac import Principal, require, workspace_for

router = APIRouter(prefix="/api", tags=["profile"])

URL_PATTERN = r"^https?://[^\s<>\"']+$"


class ContactUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    professional_title: str = Field(min_length=1, max_length=160)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    phone: Optional[str] = Field(default=None, max_length=40)
    location: str = Field(min_length=1, max_length=120)
    portfolio_url: Optional[str] = Field(default=None, pattern=URL_PATTERN, max_length=500)
    github_url: Optional[str] = Field(default=None, pattern=URL_PATTERN, max_length=500)
    linkedin_url: Optional[str] = Field(default=None, pattern=URL_PATTERN, max_length=500)
    calendar_booking_url: Optional[str] = Field(default=None, pattern=URL_PATTERN, max_length=500)
    preferred_hourly_usd: float = Field(default=65.0, ge=0, le=10000)
    minimum_project_budget_usd: float = Field(default=800.0, ge=0, le=10_000_000)

    @field_validator("phone", "portfolio_url", "github_url", "linkedin_url", "calendar_booking_url", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v


@router.get("/contact")
def get_contact(request: Request, p: Principal = Depends(require("data:read"))) -> dict:
    data = workspace_for(request, p).read_profile()
    return {"personal_info": data.get("personal_info", {}), "preferences": data.get("preferences", {})}


@router.post("/contact")
def update_contact(req: ContactUpdate, request: Request, p: Principal = Depends(require("profile:write"))) -> dict:
    ws = workspace_for(request, p)
    data = ws.read_profile()
    fields = req.model_dump()
    rates = {"preferred_hourly_usd": fields.pop("preferred_hourly_usd"),
             "minimum_project_budget_usd": fields.pop("minimum_project_budget_usd")}
    updated = {
        **data,
        "personal_info": {**data.get("personal_info", {}), **fields},
        "preferences": {**data.get("preferences", {}),
                        "rates": {**data.get("preferences", {}).get("rates", {}), **rates}},
    }
    ws.write_profile(updated)
    request.app.state.auth.audit(p.user_id, "profile:update")
    return {"status": "success", "message": "Dossier saved and agents refreshed."}
