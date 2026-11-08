"""Jobs, applications, proposals, browser prefill and analytics."""
import asyncio
import json
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.rbac import Principal, require, workspace_for
from src.workspace import row_to_job

router = APIRouter(prefix="/api", tags=["jobs"])
HIGH_MATCH = 70.0


class ProposalRequest(BaseModel):
    job_id: int
    tone: str = Field(default="standard", pattern="^(standard|concise|technical|friendly)$")


class PrefillRequest(BaseModel):
    job_id: int
    proposal_text: str = Field(default="", max_length=20000)


class ApplyRequest(BaseModel):
    job_id: int
    proposal_text: str = Field(min_length=1, max_length=20000)


def _require_job(ws, job_id: int):
    job = ws.job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _all_jobs(ws) -> list:
    with ws.db._get_connection() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY match_score DESC, created_at DESC").fetchall()
    jobs = []
    for r in rows:
        d = dict(r)
        try:
            d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        except json.JSONDecodeError:
            d["tags"] = []
        jobs.append(d)
    return jobs


@router.get("/stats")
def stats(request: Request, p: Principal = Depends(require("data:read"))) -> dict:
    ws = workspace_for(request, p)
    jobs = _all_jobs(ws)
    with ws.db._get_connection() as conn:
        applied = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        convs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    info = ws.profile_agent.profile.personal_info
    rates = ws.profile_agent.profile.preferences.rates
    return {
        "total_jobs": len(jobs),
        "high_matches": sum(1 for j in jobs if j["match_score"] >= HIGH_MATCH),
        "total_applied": applied,
        "pending_jobs": sum(1 for j in jobs if j["status"] == "discovered"),
        "total_conversations": convs,
        "profile": {"name": info.full_name, "title": info.professional_title,
                    "hourly_rate": rates.get("preferred_hourly_usd", 65)},
    }


@router.get("/analytics")
def analytics(request: Request, p: Principal = Depends(require("data:read"))) -> dict:
    ws = workspace_for(request, p)
    jobs = _all_jobs(ws)
    with ws.db._get_connection() as conn:
        per_day = conn.execute(
            "SELECT date(applied_at) d, COUNT(*) c FROM applications GROUP BY d ORDER BY d DESC LIMIT 14"
        ).fetchall()
        conv = conn.execute("SELECT status, COUNT(*) FROM conversations GROUP BY status").fetchall()
    scores = [j["match_score"] or 0 for j in jobs]
    tags = Counter(t.lower().strip() for j in jobs for t in j["tags"])
    return {
        "applications_per_day": [{"label": r[0], "value": r[1]} for r in reversed(per_day)],
        "jobs_per_platform": [{"label": k, "value": v} for k, v in Counter(j["platform"] for j in jobs).most_common()],
        "status_split": [{"label": k, "value": v} for k, v in Counter(j["status"] for j in jobs).most_common()],
        "score_buckets": [{"label": f"{b}-{b + 19}", "value": sum(1 for s in scores if b <= s < b + 20)}
                          for b in range(0, 100, 20)],
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "top_tags": [{"label": k, "value": v} for k, v in tags.most_common(10)],
        "conversation_split": [{"label": r[0], "value": r[1]} for r in conv],
    }


@router.get("/jobs")
def jobs(request: Request, status: Optional[str] = None, q: Optional[str] = None,
         platform: Optional[str] = None, p: Principal = Depends(require("data:read"))) -> list:
    result = _all_jobs(workspace_for(request, p))
    if status == "high":
        result = [j for j in result if j["match_score"] >= HIGH_MATCH]
    elif status and status != "all":
        result = [j for j in result if j["status"] == status]
    if platform and platform != "all":
        result = [j for j in result if j["platform"] == platform]
    if q and q.strip():
        needle = q.strip().lower()
        result = [j for j in result if needle in " ".join(
            [j["title"], j["company"] or "", j["description"] or "", " ".join(j["tags"])]).lower()]
    return result


@router.get("/applications")
def applications(request: Request, p: Principal = Depends(require("data:read"))) -> list:
    with workspace_for(request, p).db._get_connection() as conn:
        rows = conn.execute("""
            SELECT a.id, a.job_id, a.proposal_text, a.applied_at, a.status,
                   j.title, j.company, j.url, j.match_score, j.platform
            FROM applications a JOIN jobs j ON a.job_id = j.id ORDER BY a.applied_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


@router.post("/proposals/generate")
async def generate_proposal(req: ProposalRequest, request: Request,
                            p: Principal = Depends(require("jobs:run"))) -> dict:
    ws = workspace_for(request, p)
    job = _require_job(ws, req.job_id)
    text = await asyncio.to_thread(ws.proposal_agent.generate_proposal, job, req.tone)
    return {"job_id": job.id, "title": job.title, "company": job.company,
            "match_score": job.match_score, "tone": req.tone, "proposal_text": text}


@router.post("/browser/prefill")
async def browser_prefill(req: PrefillRequest, request: Request,
                          p: Principal = Depends(require("browser:prefill"))) -> dict:
    ws = workspace_for(request, p)
    job = _require_job(ws, req.job_id)
    request.app.state.auth.audit(p.user_id, "browser:prefill", job.url)
    if ws.demo:
        return {"status": "simulated", "message": "Demo mode: no browser launched.", "url": job.url,
                "filled_fields": ["name", "email", "linkedin", "cover_letter"]}
    from src.browser.runner import JobApplicationAssistant
    return await JobApplicationAssistant(profile_path=ws.profile_path).auto_prefill_job(job.url, req.proposal_text)


@router.post("/proposals/apply")
def record_application(req: ApplyRequest, request: Request,
                       p: Principal = Depends(require("applications:write"))) -> dict:
    ws = workspace_for(request, p)
    _require_job(ws, req.job_id)
    ws.db.record_application(req.job_id, req.proposal_text)
    request.app.state.auth.audit(p.user_id, "application:record", str(req.job_id))
    return {"status": "success", "job_id": req.job_id}
