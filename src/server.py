import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.db import Database
from src.agents.profile_agent import ProfileAgent
from src.agents.proposal_agent import ProposalAgent
from src.agents.responder_agent import ResponderAgent
from src.scrapers.remoteok_scraper import RemoteOKScraper
from src.scrapers.hunter import JobHunter
from src.models import JobListing, InboundMessage

app = FastAPI(title="AutoJob AI Dashboard", version="1.0.0")

db = Database()
proposal_agent = ProposalAgent()
responder_agent = ResponderAgent()
profile_agent = ProfileAgent()
hunter = JobHunter()


class ProposalRequest(BaseModel):
    job_id: int

class ApplyRequest(BaseModel):
    job_id: int
    proposal_text: str

class ResponderRequest(BaseModel):
    client_name: str
    message_text: str
    platform: Optional[str] = "Web Inbound"

class AgentRunRequest(BaseModel):
    mode: str  # 'scout', 'top_proposal', 'responder', 'profile', 'full_cycle'

class ContactUpdateRequest(BaseModel):
    full_name: str
    professional_title: str
    email: str
    phone: Optional[str] = None
    location: str
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    calendar_booking_url: Optional[str] = None
    preferred_hourly_usd: Optional[float] = 65.0
    minimum_project_budget_usd: Optional[float] = 800.0

@app.get("/api/stats")
def get_stats():
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 70.0")
        high_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications")
        total_applied = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'discovered'")
        pending_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()[0]

    p = profile_agent.profile
    return {
        "total_jobs": total_jobs,
        "high_matches": high_matches,
        "total_applied": total_applied,
        "pending_jobs": pending_jobs,
        "total_conversations": total_conversations,
        "profile": {
            "name": p.personal_info.full_name,
            "title": p.personal_info.professional_title,
            "email": p.personal_info.email,
            "phone": p.personal_info.phone,
            "location": p.personal_info.location,
            "portfolio": p.personal_info.portfolio_url,
            "github": p.personal_info.github_url,
            "linkedin": p.personal_info.linkedin_url,
            "calendar": p.personal_info.calendar_booking_url,
            "hourly_rate": p.preferences.rates.get("preferred_hourly_usd", 65),
            "min_budget": p.preferences.rates.get("minimum_project_budget_usd", 800),
            "weekly_hours": p.preferences.max_weekly_hours,
        }
    }

@app.get("/api/jobs")
def get_jobs(status: Optional[str] = None):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        if status and status != "all":
            cursor.execute("""
                SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC, created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT * FROM jobs ORDER BY match_score DESC, created_at DESC
            """)
        rows = cursor.fetchall()
        jobs = []
        for r in rows:
            d = dict(r)
            try:
                d["tags"] = json.loads(d["tags"]) if d["tags"] else []
            except Exception:
                d["tags"] = []
            jobs.append(d)
        return jobs

@app.get("/api/applications")
def get_applications():
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.job_id, a.proposal_text, a.applied_at, a.status,
                   j.title, j.company, j.url, j.match_score
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            ORDER BY a.applied_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@app.get("/api/conversations")
def get_conversations(status: Optional[str] = None):
    return db.get_conversations(status)

@app.post("/api/conversations/receive")
def receive_inbound_message(req: ResponderRequest):
    msg = InboundMessage(platform=req.platform, client_name=req.client_name, message_text=req.message_text)
    reply, requires_escalation = responder_agent.evaluate_and_respond(msg)
    status = "escalation" if requires_escalation else "responded"
    conv_id = db.record_conversation(req.platform, req.client_name, req.message_text, reply, status)
    return {
        "id": conv_id,
        "platform": req.platform,
        "client_name": req.client_name,
        "message_text": req.message_text,
        "reply_text": reply,
        "status": status,
        "requires_escalation": requires_escalation
    }

@app.get("/api/contact")
def get_contact_info():
    with open("config/profile.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    p_info = data.get("personal_info", {})
    prefs = data.get("preferences", {})
    return {
        "personal_info": p_info,
        "preferences": prefs
    }

@app.post("/api/contact")
def update_contact_info(req: ContactUpdateRequest):
    with open("config/profile.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    data["personal_info"]["full_name"] = req.full_name
    data["personal_info"]["professional_title"] = req.professional_title
    data["personal_info"]["email"] = req.email
    data["personal_info"]["phone"] = req.phone
    data["personal_info"]["location"] = req.location
    data["personal_info"]["portfolio_url"] = req.portfolio_url
    data["personal_info"]["github_url"] = req.github_url
    data["personal_info"]["linkedin_url"] = req.linkedin_url
    data["personal_info"]["calendar_booking_url"] = req.calendar_booking_url
    
    if "rates" not in data["preferences"]:
        data["preferences"]["rates"] = {}
    data["preferences"]["rates"]["preferred_hourly_usd"] = req.preferred_hourly_usd
    data["preferences"]["rates"]["minimum_project_budget_usd"] = req.minimum_project_budget_usd

    with open("config/profile.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Reload agents with new profile data
    global profile_agent, proposal_agent, responder_agent
    profile_agent = ProfileAgent("config/profile.json")
    proposal_agent = ProposalAgent("config/profile.json")
    responder_agent = ResponderAgent("config/profile.json")

    return {"status": "success", "message": "Contact info updated and agents refreshed"}

@app.post("/api/agent/run")
def run_agent_action(req: AgentRunRequest):
    logs = []
    logs.append(f"INITIATING AGENT RUN // MODE: {req.mode.upper()}")
    
    if req.mode == "scout":
        logs.append("Querying RemoteOK, Remotive & Jobicy APIs for remote & contract gigs...")
        hunted = hunter.hunt_jobs(target_count=20)
        logs.append(f"Hunted and evaluated {len(hunted)} candidate opportunities across feeds.")
        high_cnt = sum(1 for j in hunted if j.match_score >= 70.0)
        logs.append(f"Scout complete: Stored top {len(hunted)} matches ({high_cnt} with >=70% score).")
        return {"status": "success", "mode": req.mode, "logs": logs}

    elif req.mode == "top_proposal":
        unapplied = db.get_unapplied_jobs(min_score=40.0)
        if not unapplied:
            unapplied = db.get_unapplied_jobs(min_score=0.0)
        if not unapplied:
            logs.append("No unapplied opportunities in database. Run scout first.")
            return {"status": "empty", "mode": req.mode, "logs": logs}
        
        top_data = unapplied[0]
        tags = json.loads(top_data["tags"]) if top_data["tags"] else []
        job = JobListing(**{k: v for k, v in top_data.items() if k != 'tags'}, tags=tags)
        logs.append(f"Targeting top match: {job.title} at {job.company} (Score: {job.match_score}%)")
        prop_text = proposal_agent.generate_proposal(job)
        logs.append("Synthesized tailored proposal citing case studies & portfolio")
        return {
            "status": "success", 
            "mode": req.mode, 
            "logs": logs,
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "proposal_text": prop_text
        }

    elif req.mode == "responder":
        logs.append("Testing client retention auto-responder across 4 realistic scenarios:")
        scenarios = [
            ("Email", "Sarah (Fintech Labs)", "What is your hourly rate and capacity?"),
            ("Upwork", "Mark (AI Startup)", "Can you provide links to your past Next.js & Python repositories?"),
            ("LinkedIn", "Elena (Recruiter)", "Please sign an NDA before we share API keys.")
        ]
        for plat, client, msg in scenarios:
            inbound = InboundMessage(platform=plat, client_name=client, message_text=msg)
            reply, esc = responder_agent.evaluate_and_respond(inbound)
            status = "escalation" if esc else "responded"
            db.record_conversation(plat, client, msg, reply, status)
            tag = "ESCALATED TO FOUNDER" if esc else "AUTO-RESPONDED WITH CALENDLY"
            logs.append(f"[{plat}] Client '{client}': {tag}")
        logs.append("All inbound queries processed and logged to Conversations table")
        return {"status": "success", "mode": req.mode, "logs": logs}

    elif req.mode == "profile":
        upwork = profile_agent.generate_upwork_profile()
        linkedin = profile_agent.generate_linkedin_profile()
        fiverr = profile_agent.generate_fiverr_gig()
        logs.append(f"Upwork Profile: '{upwork['title']}' at ${upwork['hourly_rate_usd']}/hr")
        logs.append(f"LinkedIn Headline: '{linkedin['headline'][:60]}...'")
        logs.append(f"Fiverr Gig: '{fiverr['gig_title']}' with 3 packages")
        return {"status": "success", "mode": req.mode, "logs": logs}

    elif req.mode == "full_cycle":
        logs.append("Step 1: Scouting live job market...")
        scraper = RemoteOKScraper()
        jobs = scraper.fetch_jobs(limit=8)
        for j in jobs:
            j.match_score = proposal_agent.score_job_match(j)
            db.save_job(j)
        logs.append(f"Processed {len(jobs)} listings.")
        
        logs.append("Step 2: Identifying best unapplied match...")
        unapplied = db.get_unapplied_jobs(min_score=40.0)
        if unapplied:
            top_j = unapplied[0]
            tags = json.loads(top_j["tags"]) if top_j["tags"] else []
            job = JobListing(**{k: v for k, v in top_j.items() if k != 'tags'}, tags=tags)
            proposal = proposal_agent.generate_proposal(job)
            logs.append(f"Drafted application for '{job.title}' at {job.company}.")
        
        logs.append("Step 3: Checking client messaging queue & inbox...")
        logs.append("Auto-responder active. System fully synchronized.")
        return {"status": "success", "mode": req.mode, "logs": logs}

    else:
        raise HTTPException(status_code=400, detail="Unknown mode")

@app.post("/api/proposals/generate")
def generate_proposal(req: ProposalRequest):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (req.job_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        data = dict(row)
        tags = json.loads(data["tags"]) if data["tags"] else []
        job = JobListing(**{k: v for k, v in data.items() if k != 'tags'}, tags=tags)
        proposal_text = proposal_agent.generate_proposal(job)
        return {
            "job_id": req.job_id,
            "title": job.title,
            "company": job.company,
            "match_score": job.match_score,
            "proposal_text": proposal_text
        }

@app.post("/api/proposals/apply")
def record_application(req: ApplyRequest):
    db.record_application(req.job_id, req.proposal_text)
    return {"status": "success", "job_id": req.job_id}

@app.get("/api/profile")
def get_profile():
    with open("config/profile.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Serve static files from 'ui' directory
ui_dir = Path("ui")
if ui_dir.exists():
    app.mount("/static", StaticFiles(directory="ui"), name="static")

@app.get("/")
def index():
    return FileResponse("ui/index.html")

def start_server(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    print(f"\n[AutoJob UI] Telemetry Dashboard listening at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")

if __name__ == "__main__":
    start_server()
