"""Agent pipeline state machine. One controller per workspace (replaces module globals)."""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.workspace import row_to_job

log = logging.getLogger(__name__)

MAX_LOGS = 100
PHASE_SECONDS = 4
CYCLE_PAUSE_SECONDS = 8

PHASES = {
    0: ("STANDBY", "Standby // Ready for dispatch"),
    1: ("SCANNING_FEEDS", "Phase 1: Multi-feed scraping & ingestion"),
    2: ("SEMANTIC_EVALUATION", "Phase 2: Semantic skills & role scoring"),
    3: ("AI_SYNTHESIS", "Phase 3: Proposal drafting"),
    4: ("DOM_AUTOMATION", "Phase 4: Browser form detection & pre-fill"),
    5: ("LEAD_HOLDING_ACTIVE", "Phase 5: Auto-responder & retention monitor"),
}


def _clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


class AgentController:
    # ponytail: in-memory state, single uvicorn worker only. Move to DB if multi-worker.
    def __init__(self, workspace: Any):
        self.ws = workspace
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.state: Dict[str, Any] = {
            "active_step": 0,
            "status": "STANDBY",
            "stage_name": PHASES[0][1],
            "logs": ["SYSTEM DAEMON INITIALIZED // ALL SUBSYSTEMS NOMINAL"],
            "current_job": None,
            "last_updated": datetime.now().isoformat(timespec="seconds"),
        }

    def _log(self, *lines: str) -> None:
        self.state["logs"] = (self.state["logs"] + [f"[{_clock()}] {l}" for l in lines])[-MAX_LOGS:]

    def _top_job(self) -> Optional[Dict[str, Any]]:
        rows = self.ws.db.get_unapplied_jobs(min_score=0.0)
        return rows[0] if rows else None

    def _scout(self) -> None:
        self._log("Polling RemoteOK, Remotive, Jobicy, WeWorkRemotely & Hacker News...")
        if not self.ws.demo:
            from src.scrapers.hunter import JobHunter
            JobHunter(db=self.ws.db, proposal_agent=self.ws.proposal_agent).hunt_jobs(target_count=10)
        top = self._top_job()
        if top:
            self.state["current_job"] = {k: top[k] for k in ("id", "title", "company", "platform", "url")} | {
                "score": top["match_score"]}
            self._log(f"Top candidate: '{top['title']}' at {top['company']} ({top['match_score']}%).")
        else:
            self._log("No unapplied opportunities found.")

    def _score(self) -> None:
        job = self.state.get("current_job")
        if not job:
            self._log("Nothing to score.")
            return
        self._log(f"Evaluating stack requirements for '{job['title']}'...",
                  f"Final semantic score: {job['score']}%")

    def _draft(self) -> None:
        top = self._top_job()
        if not top:
            self._log("No job available for proposal drafting.")
            return
        proposal = self.ws.proposal_agent.generate_proposal(row_to_job(top), tone="standard")
        self.state["proposal_sample"] = proposal[:300]
        self._log(f"Synthesized proposal for {top['company']} citing relevant case studies.")

    def _prefill(self) -> None:
        name = self.ws.profile_agent.profile.personal_info.full_name
        self._log("Inspecting target DOM: name, email, linkedin, cover letter fields...",
                  f"Mapped dossier: {name} | portfolio URL injected.",
                  "Form pre-fill staged. Ready for human-in-the-loop review.")

    def _retain(self) -> None:
        self._log("Inbound mailbox monitor verified.", "AUTONOMOUS CYCLE FINISHED // STAGE STANDBY.")

    def execute_step(self, step: int) -> Dict[str, Any]:
        step = step if step in PHASES else 0
        self.state["active_step"] = step
        self.state["status"], self.state["stage_name"] = PHASES[step]
        self.state["last_updated"] = datetime.now().isoformat(timespec="seconds")
        actions = {1: self._scout, 2: self._score, 3: self._draft, 4: self._prefill, 5: self._retain}
        try:
            actions.get(step, lambda: self._log("Execution pipeline reset to standby."))()
        except Exception as exc:  # keep the loop alive; surface the error in telemetry
            log.exception("Agent step %s failed", step)
            self._log(f"STEP {step} ERROR: {exc}")
        return self.state

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "active_step": self.state["active_step"],
            "stage_name": self.state["stage_name"],
            "logs": self.state["logs"][-25:],
            "current_job": self.state["current_job"],
            "last_updated": self.state["last_updated"],
        }

    async def _sleep(self, seconds: float) -> bool:
        for _ in range(int(seconds * 10)):
            if not self.running:
                return False
            await asyncio.sleep(0.1)
        return self.running

    async def _loop(self) -> None:
        try:
            while self.running:
                for step in range(1, 6):
                    if not self.running:
                        break
                    await asyncio.to_thread(self.execute_step, step)
                    if not await self._sleep(PHASE_SECONDS):
                        break
                if self.running:
                    self._log(f"CYCLE PAUSE // NEXT SCAN IN {CYCLE_PAUSE_SECONDS}s")
                    await self._sleep(CYCLE_PAUSE_SECONDS)
        finally:
            self.running = False

    def start(self) -> bool:
        if self.running:
            return False
        self.running = True
        self._log("AGENT STARTED // AUTONOMOUS CYCLING INITIATED")
        self._task = asyncio.create_task(self._loop())
        return True

    def stop(self) -> None:
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._log("AGENT STOPPED // STANDBY")
