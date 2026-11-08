"""/api/email/*: send a proposal or reply by email (SMTP from .env)."""
import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.rbac import Principal, require, workspace_for
from src.mailer import EMAIL_RE, MailError, SmtpConfig, send_email

router = APIRouter(prefix="/api/email", tags=["email"])
log = logging.getLogger(__name__)

EMAILS_PER_HOUR = 30
# ponytail: per-process limiter, like login; move to the DB if running multiple workers.
_sent: Dict[int, Deque[float]] = defaultdict(deque)


def _rate_limit(user_id: int) -> None:
    now, window = time.monotonic(), _sent[user_id]
    while window and now - window[0] > 3600:
        window.popleft()
    if len(window) >= EMAILS_PER_HOUR:
        raise HTTPException(status_code=429, detail=f"Email limit reached ({EMAILS_PER_HOUR}/hour). Try again later.")
    window.append(now)


class SendRequest(BaseModel):
    to: str = Field(min_length=3, max_length=254)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    job_id: Optional[int] = None  # when set, the send also records the application


@router.get("/status")
def status(request: Request, p: Principal = Depends(require("data:read"))) -> dict:
    cfg = SmtpConfig.from_env()
    demo = workspace_for(request, p).demo
    return {"configured": bool(cfg) or demo, "simulated": demo, "sender": "demo" if demo else (cfg.sender if cfg else "")}


def deliver(request: Request, p: Principal, to: str, subject: str, body: str) -> str:
    """Send (or simulate in demo). Returns 'sent' or 'simulated'. Raises HTTPException on failure."""
    if not EMAIL_RE.match(to.strip()):
        raise HTTPException(status_code=422, detail="Recipient email address looks invalid.")
    ws = workspace_for(request, p)
    _rate_limit(p.user_id)
    request.app.state.auth.audit(p.user_id, "email:send", to)
    if ws.demo:
        return "simulated"
    cfg = SmtpConfig.from_env()
    if not cfg:
        raise HTTPException(status_code=503, detail="Email is not set up. Add SMTP_HOST, SMTP_USER and SMTP_PASSWORD to .env.")
    reply_to = ws.profile_agent.profile.personal_info.email
    try:
        send_email(cfg, to.strip(), subject, body, reply_to=reply_to)
    except MailError as e:
        log.warning("email send failed to %s: %s", to, e.__cause__)
        raise HTTPException(status_code=502, detail=str(e))
    return "sent"


@router.post("/send")
async def send(req: SendRequest, request: Request, p: Principal = Depends(require("applications:write"))) -> dict:
    ws = workspace_for(request, p)
    if req.job_id is not None and not ws.job_by_id(req.job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    result = await asyncio.to_thread(deliver, request, p, req.to, req.subject, req.body)
    if req.job_id is not None:
        ws.db.record_application(req.job_id, req.body)
    return {"status": result, "to": req.to, "job_id": req.job_id}
