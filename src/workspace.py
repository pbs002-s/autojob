"""A workspace bundles the DB, profile and agents a session operates on.

Real sessions use data/autojob.db + config/profile.json. Demo sessions use a
seeded, disposable copy so visitors never see or modify real data.
"""
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from src.agents.profile_agent import ProfileAgent
from src.agents.proposal_agent import ProposalAgent
from src.agents.responder_agent import ResponderAgent
from src.db import Database
from src.models import JobListing

EXAMPLE_PROFILE = Path("config/profile.example.json")


class Workspace:
    def __init__(self, db_path: str, profile_path: str, demo: bool = False):
        self.db_path = db_path
        self.profile_path = profile_path
        self.demo = demo
        self.db = Database(db_path)
        self.reload_agents()
        from src.agent_state import AgentController  # local import: controller needs a workspace
        self.controller = AgentController(self)

    def reload_agents(self) -> None:
        self.profile_agent = ProfileAgent(self.profile_path)
        self.proposal_agent = ProposalAgent(self.profile_path)
        self.responder_agent = ResponderAgent(self.profile_path)
        if self.demo:
            # Demo never calls Gemini; the agents fall back to offline templates.
            self.proposal_agent.api_key = None
            self.responder_agent.api_key = None

    def read_profile(self) -> Dict[str, Any]:
        path = Path(self.profile_path)
        if not path.exists():
            path = EXAMPLE_PROFILE
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_profile(self, data: Dict[str, Any]) -> None:
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.reload_agents()

    def job_by_id(self, job_id: int) -> JobListing:
        with self.db._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return row_to_job(dict(row)) if row else None


def row_to_job(data: Dict[str, Any]) -> JobListing:
    tags = data.get("tags")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            tags = []
    return JobListing(**{k: v for k, v in data.items() if k != "tags"}, tags=tags or [])


# --- demo seed ---------------------------------------------------------------
DEMO_JOBS: List[Dict[str, Any]] = [
    {"platform": "RemoteOK", "title": "Senior Full-Stack Engineer (Next.js / FastAPI)", "company": "Lumen Labs",
     "budget_or_salary": "$90k - $140k", "location": "Worldwide (Remote)",
     "tags": ["next.js", "python", "fastapi", "postgresql", "react"], "match_score": 92.4, "status": "discovered"},
    {"platform": "Remotive", "title": "AI Automation Engineer", "company": "Northwind AI",
     "budget_or_salary": "$70/hr", "location": "Americas / EU (Contract)",
     "tags": ["python", "playwright", "llm", "automation"], "match_score": 88.1, "status": "discovered"},
    {"platform": "Hacker News (YC)", "title": "Founding Engineer", "company": "Parcelbird (YC W26)",
     "budget_or_salary": "Competitive / Equity", "location": "Remote (Full-Time)",
     "tags": ["YC", "typescript", "node.js", "fullstack"], "match_score": 81.0, "status": "applied"},
    {"platform": "WeWorkRemotely", "title": "React Developer — Design Systems", "company": "Halcyon Studio",
     "budget_or_salary": "$5k fixed", "location": "Remote Worldwide",
     "tags": ["react", "typescript", "storybook", "css"], "match_score": 76.5, "status": "discovered"},
    {"platform": "Jobicy", "title": "Web Scraping Specialist", "company": "Datalane",
     "budget_or_salary": "$45/hr", "location": "Remote (Part-Time)",
     "tags": ["scraping", "python", "playwright"], "match_score": 73.2, "status": "applied"},
    {"platform": "RemoteOK", "title": "Backend Engineer, Payments", "company": "Fernpay",
     "budget_or_salary": "$110k - $150k", "location": "EU (Remote)",
     "tags": ["go", "postgresql", "payments"], "match_score": 54.0, "status": "discovered"},
    {"platform": "Remotive", "title": "Shopify Theme Developer", "company": "Copper & Co",
     "budget_or_salary": "$2.5k fixed", "location": "Worldwide (Contract)",
     "tags": ["shopify", "liquid", "css"], "match_score": 47.8, "status": "discovered"},
    {"platform": "WeWorkRemotely", "title": "Data Engineer (dbt / Airflow)", "company": "Orbital Analytics",
     "budget_or_salary": None, "location": "US only",
     "tags": ["dbt", "airflow", "sql"], "match_score": 31.5, "status": "rejected"},
]

DEMO_CONVERSATIONS = [
    ("Email", "Sarah (Fintech Labs)", "What is your hourly rate and capacity this month?",
     "Hi Sarah — thanks for reaching out! My rate is $65/hr and I have ~25 hrs/week open. Grab a slot here to scope it.", "responded"),
    ("Upwork", "Mark (AI Startup)", "Can you share past Next.js & Python repos?",
     "Hi Mark — absolutely. Two relevant case studies are linked below; happy to walk through them on a quick call.", "responded"),
    ("LinkedIn", "Elena (Recruiter)", "Please sign an NDA before we share API keys.",
     "Hi Elena — thanks! I've flagged this for a personal review and will get back within a few hours.", "escalation"),
]


def seed_demo(db_path: str, profile_path: str) -> None:
    """(Re)create the demo DB and profile from canned data."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(db_path).unlink(missing_ok=True)
    shutil.copyfile(EXAMPLE_PROFILE, profile_path)
    db = Database(db_path)
    for i, job in enumerate(DEMO_JOBS):
        db.save_job(JobListing(
            external_id=f"demo_{i}", url="https://example.com/jobs/demo",
            description=f"{job['title']} at {job['company']}. Remote-first team looking for a pragmatic builder.",
            **job,
        ))
    with sqlite3.connect(db_path) as conn:
        applied = conn.execute("SELECT id FROM jobs WHERE status = 'applied'").fetchall()
        for (job_id,) in applied:
            conn.execute("INSERT INTO applications (job_id, proposal_text) VALUES (?, ?)",
                         (job_id, "Demo proposal — tailored pitch with two case studies and a booking link."))
    for platform, client, msg, reply, status in DEMO_CONVERSATIONS:
        db.record_conversation(platform, client, msg, reply, status)
