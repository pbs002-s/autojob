"""/api/agent/*: pipeline status, loop control, manual steps and one-shot runs."""
import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.rbac import Principal, require, workspace_for
from src.models import InboundMessage
from src.workspace import row_to_job

router = APIRouter(prefix="/api/agent", tags=["agent"])

CONSOLE_ONLY_MODES = {"profile", "full_cycle"}
RESPONDER_SCENARIOS = [
    ("Email", "Sarah (Fintech Labs)", "What is your hourly rate and capacity?"),
    ("Upwork", "Mark (AI Startup)", "Can you provide links to your past Next.js & Python repositories?"),
    ("LinkedIn", "Elena (Recruiter)", "Please sign an NDA before we share API keys."),
]


class StepRequest(BaseModel):
    step: int = Field(default=1, ge=0, le=5)


class RunRequest(BaseModel):
    mode: Literal["scout", "top_proposal", "responder", "profile", "full_cycle"]


@router.get("/status")
def status(request: Request, p: Principal = Depends(require("data:read"))) -> dict:
    return workspace_for(request, p).controller.status()


@router.get("/live-process")
def live_process(request: Request, p: Principal = Depends(require("data:read"))) -> dict:
    return workspace_for(request, p).controller.state


@router.post("/start")
async def start(request: Request, p: Principal = Depends(require("agent:control"))) -> dict:
    started = workspace_for(request, p).controller.start()
    request.app.state.auth.audit(p.user_id, "agent:start")
    return {"running": True, "message": "Agent loop started." if started else "Agent loop already running."}


@router.post("/stop")
async def stop(request: Request, p: Principal = Depends(require("agent:control"))) -> dict:
    workspace_for(request, p).controller.stop()
    request.app.state.auth.audit(p.user_id, "agent:stop")
    return {"running": False, "message": "Agent loop stopped."}


@router.post("/live-process/step")
async def step(req: StepRequest, request: Request, p: Principal = Depends(require("agent:control"))) -> dict:
    return await asyncio.to_thread(workspace_for(request, p).controller.execute_step, req.step)


def _scout(ws) -> dict:
    if ws.demo:
        return {"logs": ["Demo mode: feeds simulated, no network calls.", "Re-scored 8 seeded opportunities."]}
    from src.scrapers.hunter import JobHunter
    hunted = JobHunter(db=ws.db, proposal_agent=ws.proposal_agent).hunt_jobs(target_count=20)
    high = sum(1 for j in hunted if j.match_score >= 70.0)
    return {"logs": [f"Hunted {len(hunted)} opportunities across feeds ({high} scored >= 70%)."]}


def _top_proposal(ws) -> dict:
    rows = ws.db.get_unapplied_jobs(min_score=0.0)
    if not rows:
        return {"status": "empty", "logs": ["No unapplied opportunities. Run scout first."]}
    job = row_to_job(rows[0])
    text = ws.proposal_agent.generate_proposal(job)
    return {"logs": [f"Drafted proposal for {job.title} at {job.company} ({job.match_score}%)."],
            "job_id": job.id, "title": job.title, "company": job.company, "proposal_text": text}


def _responder(ws) -> dict:
    logs = []
    for platform, client, msg in RESPONDER_SCENARIOS:
        reply, escalate = ws.responder_agent.evaluate_and_respond(
            InboundMessage(platform=platform, client_name=client, message_text=msg))
        ws.db.record_conversation(platform, client, msg, reply, "escalation" if escalate else "responded")
        logs.append(f"[{platform}] {client}: {'ESCALATED' if escalate else 'AUTO-RESPONDED'}")
    return {"logs": logs}


def _profile(ws) -> dict:
    up = ws.profile_agent.generate_upwork_profile()
    li = ws.profile_agent.generate_linkedin_profile()
    fv = ws.profile_agent.generate_fiverr_gig()
    return {"logs": [f"Upwork: '{up['title']}' at ${up['hourly_rate_usd']}/hr",
                     f"LinkedIn headline: '{li['headline'][:60]}...'",
                     f"Fiverr gig: '{fv['gig_title']}' with 3 packages"]}


def _full_cycle(ws) -> dict:
    logs = _scout(ws)["logs"] + _top_proposal(ws)["logs"] + _responder(ws)["logs"]
    return {"logs": logs + ["Full cycle complete."]}


MODES = {"scout": _scout, "top_proposal": _top_proposal, "responder": _responder,
         "profile": _profile, "full_cycle": _full_cycle}


@router.post("/run")
async def run(req: RunRequest, request: Request, p: Principal = Depends(require("jobs:run"))) -> dict:
    if req.mode in CONSOLE_ONLY_MODES and not p.can("console:use"):
        raise HTTPException(status_code=403, detail="Your role cannot use the runtime console.")
    result = await asyncio.to_thread(MODES[req.mode], workspace_for(request, p))
    request.app.state.auth.audit(p.user_id, f"agent:run:{req.mode}")
    return {"status": "success", "mode": req.mode, **result}
