import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.auth import routes as auth_routes
from src.server import Settings, create_app

ADMIN = ("admin@test.local", "correct-horse-battery")


@pytest.fixture
def app(tmp_path, monkeypatch):
    profile = tmp_path / "profile.json"
    shutil.copyfile("config/profile.example.json", profile)
    auth_routes._attempts.clear()
    settings = Settings(data_dir=str(tmp_path), profile_path=str(profile), demo_enabled=True,
                        admin_email=ADMIN[0], admin_password=ADMIN[1])
    application = create_app(settings)
    application.state.auth.create_user("op@test.local", "operator-pass-1", "operator")
    application.state.auth.create_user("view@test.local", "viewer-pass-1", "viewer")
    return application


def login(app, email, password) -> TestClient:
    client = TestClient(app)
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
    return client


CREDS = {"admin": ADMIN, "operator": ("op@test.local", "operator-pass-1"),
         "viewer": ("view@test.local", "viewer-pass-1")}

# (method, path, body, roles allowed). Bodies are valid so 2xx/4xx comes from auth, not validation.
ROUTES = [
    ("GET", "/api/stats", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/analytics", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/jobs", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/applications", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/conversations", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/contact", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/agent/status", None, {"admin", "operator", "viewer"}),
    ("GET", "/api/agent/live-process", None, {"admin", "operator", "viewer"}),
    ("POST", "/api/agent/live-process/step", {"step": 0}, {"admin", "operator"}),
    ("POST", "/api/agent/stop", None, {"admin", "operator"}),
    ("POST", "/api/agent/run", {"mode": "responder"}, {"admin", "operator"}),
    ("POST", "/api/agent/run", {"mode": "profile"}, {"admin"}),
    ("POST", "/api/conversations/receive", {"client_name": "A", "message_text": "hi"}, {"admin", "operator"}),
    ("POST", "/api/proposals/apply", {"job_id": 999, "proposal_text": "x"}, {"admin", "operator"}),
    ("POST", "/api/browser/prefill", {"job_id": 999}, {"admin", "operator"}),
    ("POST", "/api/contact", {"full_name": "A", "professional_title": "B", "email": "a@b.co", "location": "X"},
     {"admin"}),
    ("GET", "/api/users", None, {"admin"}),
    ("GET", "/api/users/audit", None, {"admin"}),
]


@pytest.mark.parametrize("method,path,body,allowed", ROUTES)
def test_unauthenticated_requests_get_401(app, method, path, body, allowed):
    res = TestClient(app).request(method, path, json=body)
    assert res.status_code == 401
    assert res.json() == {"success": False, "error": "Not signed in."}


@pytest.mark.parametrize("role", ["admin", "operator", "viewer"])
@pytest.mark.parametrize("method,path,body,allowed", ROUTES)
def test_rbac_matrix(app, role, method, path, body, allowed):
    client = login(app, *CREDS[role])
    res = client.request(method, path, json=body)
    if role in allowed:
        assert res.status_code in (200, 201, 404), res.text  # 404 = fake job id, auth passed
    else:
        assert res.status_code == 403, res.text


def test_every_api_route_is_covered_by_matrix(app):
    public = {"/api/auth/login", "/api/auth/demo", "/api/auth/config", "/api/public/stats",
              "/api/auth/logout", "/api/auth/me", "/api/{rest:path}"}
    unguarded_in_matrix = {"/api/agent/start", "/api/proposals/generate", "/api/users/{user_id}", "/api/users"}
    covered = {path for _, path, _, _ in ROUTES} | public | unguarded_in_matrix
    api_paths = {r.path for r in app.routes if getattr(r, "path", "").startswith("/api")}
    assert api_paths <= covered, f"Routes missing from RBAC matrix: {api_paths - covered}"


def test_mutation_without_csrf_is_rejected(app):
    client = login(app, *ADMIN)
    del client.headers["X-CSRF-Token"]
    assert client.post("/api/agent/stop").status_code == 403


def test_wrong_password_and_rate_limit(app):
    client = TestClient(app)
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": ADMIN[0], "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}).status_code == 429


def test_logout_invalidates_session(app):
    client = login(app, *ADMIN)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_disabled_user_loses_session(app):
    admin = login(app, *ADMIN)
    viewer = login(app, *CREDS["viewer"])
    viewer_id = app.state.auth.get_user_by_email(CREDS["viewer"][0])["id"]
    assert admin.patch(f"/api/users/{viewer_id}", json={"disabled": True}).status_code == 200
    assert viewer.get("/api/stats").status_code == 401


def test_cannot_demote_last_admin(app):
    admin = login(app, *ADMIN)
    admin_id = app.state.auth.get_user_by_email(ADMIN[0])["id"]
    assert admin.patch(f"/api/users/{admin_id}", json={"role": "viewer"}).status_code == 409


def test_contact_rejects_bad_email_and_url(app):
    client = login(app, *ADMIN)
    body = {"full_name": "A", "professional_title": "B", "email": "not-an-email", "location": "X",
            "portfolio_url": "javascript:alert(1)"}
    res = client.post("/api/contact", json=body)
    assert res.status_code == 422
    assert "email" in res.json()["error"] and "portfolio_url" in res.json()["error"]


def test_demo_session_is_isolated_from_real_db(app, tmp_path):
    real_db = tmp_path / "autojob.db"
    before = sqlite3.connect(real_db).execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    client = TestClient(app)
    res = client.post("/api/auth/demo", json={"role": "operator"})
    client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
    assert len(client.get("/api/jobs").json()) == 8  # seeded demo data, not the real DB
    job_id = client.get("/api/jobs").json()[0]["id"]
    prefill = client.post("/api/browser/prefill", json={"job_id": job_id})
    assert prefill.json()["status"] == "simulated"  # no Chromium in demo
    client.post("/api/conversations/receive", json={"client_name": "A", "message_text": "rate?"})
    after = sqlite3.connect(real_db).execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    assert before == after


def test_demo_login_disabled(tmp_path):
    profile = tmp_path / "profile.json"
    shutil.copyfile("config/profile.example.json", profile)
    app = create_app(Settings(data_dir=str(tmp_path), profile_path=str(profile), admin_email=ADMIN[0],
                              admin_password=ADMIN[1]))
    assert TestClient(app).post("/api/auth/demo", json={"role": "admin"}).status_code == 404


def test_startup_fails_without_admin(tmp_path):
    with pytest.raises(RuntimeError, match="AUTOJOB_ADMIN_EMAIL"):
        create_app(Settings(data_dir=str(tmp_path)))


def test_public_stats_has_no_pii(app):
    body = TestClient(app).get("/api/public/stats").json()
    assert set(body) == {"jobs_scanned", "high_matches", "applications", "conversations"}


def test_agent_step_uses_profile_name(app):
    client = login(app, *ADMIN)
    logs = client.post("/api/agent/live-process/step", json={"step": 4}).json()["logs"]
    assert any("Alex Mercer" in line for line in logs)
    assert not any("Pritam" in line for line in logs)
