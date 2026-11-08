"""/api/conversations: inbound messages and the responder simulator."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.api.email import deliver
from src.auth.rbac import Principal, require, workspace_for
from src.models import InboundMessage

router = APIRouter(prefix="/api/conversations", tags=["inbox"])


class InboundRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=120)
    message_text: str = Field(min_length=1, max_length=5000)
    platform: str = Field(default="Web Inbound", max_length=60)
    client_email: str = Field(default="", max_length=254)


@router.get("")
def conversations(request: Request, status: Optional[str] = None,
                  p: Principal = Depends(require("data:read"))) -> list:
    return workspace_for(request, p).db.get_conversations(status)


@router.post("/receive")
async def receive(req: InboundRequest, request: Request, p: Principal = Depends(require("jobs:run"))) -> dict:
    ws = workspace_for(request, p)
    msg = InboundMessage(platform=req.platform, client_name=req.client_name, message_text=req.message_text)
    reply, escalate = await asyncio.to_thread(ws.responder_agent.evaluate_and_respond, msg)
    status = "escalation" if escalate else "responded"
    conv_id = ws.db.record_conversation(req.platform, req.client_name, req.message_text, reply, status)
    # Escalations wait for a human; only routine auto-replies go out by email.
    emailed = None
    if req.client_email.strip() and not escalate:
        emailed = await asyncio.to_thread(deliver, request, p, req.client_email, "Re: your message", reply)
    return {"emailed": emailed, "id": conv_id, "platform": req.platform, "client_name": req.client_name,
            "message_text": req.message_text, "reply_text": reply, "status": status}
