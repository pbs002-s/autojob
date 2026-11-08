"""/api/public/stats: aggregate counts for the landing page. No PII."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/stats")
def public_stats(request: Request) -> dict:
    with request.app.state.real_workspace.db._get_connection() as conn:
        jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 70").fetchone()[0]
        applied = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        convs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    return {"jobs_scanned": jobs, "high_matches": high, "applications": applied, "conversations": convs}
