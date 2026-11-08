import smtplib

import pytest

from src import mailer
from src.textfmt import clean_markdown
from tests.test_auth_rbac import app, login, ADMIN  # noqa: F401  (fixture reuse)


def test_clean_markdown_strips_bold_headings_bullets_and_links():
    raw = "## Plan\n* **Modern Vue:** fast\n- *nice* work\nSee [site](https://x.dev)"
    assert clean_markdown(raw) == "Plan\n• Modern Vue: fast\n• nice work\nSee site (https://x.dev)"


def test_clean_markdown_keeps_plain_text_and_math():
    assert clean_markdown("Rate is 5 * 3 = 15, a*b") == "Rate is 5 * 3 = 15, a*b"


class FakeSMTP:
    sent = []

    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self, **k): pass
    def login(self, u, p): pass
    def send_message(self, msg): FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    from src.api import email as email_api
    email_api._sent.clear()
    FakeSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    for k, v in {"SMTP_HOST": "smtp.test", "SMTP_USER": "me@test.dev", "SMTP_PASSWORD": "pw"}.items():
        monkeypatch.setenv(k, v)
    return FakeSMTP


def _first_job(app):
    with app.state.real_workspace.db._get_connection() as conn:
        conn.execute("INSERT INTO jobs (platform, external_id, title, company, description, url) VALUES ('X','e1','Dev','Corp','d','https://x.dev')")
        return conn.execute("SELECT id FROM jobs").fetchone()[0]


def test_send_email_records_application(app, smtp):
    job_id = _first_job(app)
    client = login(app, *ADMIN)
    res = client.post("/api/email/send", json={"to": "hr@corp.dev", "subject": "Hi\nBcc: x@y.z", "body": "Proposal", "job_id": job_id})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "sent"
    msg = smtp.sent[0]
    assert msg["To"] == "hr@corp.dev" and "\n" not in msg["Subject"] and msg["Bcc"] is None
    assert client.get("/api/applications").json()[0]["job_id"] == job_id


def test_send_email_rejects_bad_address(app, smtp):
    client = login(app, *ADMIN)
    res = client.post("/api/email/send", json={"to": "nope", "subject": "s", "body": "b"})
    assert res.status_code == 422 and not smtp.sent


def test_send_email_unconfigured_returns_503(app, monkeypatch):
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    client = login(app, *ADMIN)
    res = client.post("/api/email/send", json={"to": "a@b.dev", "subject": "s", "body": "b"})
    assert res.status_code == 503 and "SMTP_HOST" in res.json()["error"]


def test_viewer_cannot_send_email(app, smtp):
    client = login(app, "view@test.local", "viewer-pass-1")
    assert client.post("/api/email/send", json={"to": "a@b.dev", "subject": "s", "body": "b"}).status_code == 403


def test_demo_email_is_simulated(app, smtp):
    from fastapi.testclient import TestClient
    client = TestClient(app)
    csrf = client.post("/api/auth/demo", json={"role": "operator"}).json()["csrf_token"]
    res = client.post("/api/email/send", headers={"X-CSRF-Token": csrf}, json={"to": "a@b.dev", "subject": "s", "body": "b"})
    assert res.json()["status"] == "simulated" and not smtp.sent


def test_inbox_auto_reply_is_emailed_but_escalation_is_not(app, smtp):
    client = login(app, *ADMIN)
    ok = client.post("/api/conversations/receive", json={"client_name": "Dana", "message_text": "What is your rate?", "client_email": "dana@acme.dev"})
    esc = client.post("/api/conversations/receive", json={"client_name": "Eve", "message_text": "Please sign an NDA", "client_email": "eve@acme.dev"})
    assert ok.json()["emailed"] == "sent" and esc.json()["emailed"] is None
    assert [m["To"] for m in smtp.sent] == ["dana@acme.dev"]


def test_session_probe_never_401(app):
    from fastapi.testclient import TestClient
    assert TestClient(app).get("/api/auth/session").json() == {"signed_in": False}
    assert login(app, *ADMIN).get("/api/auth/session").json()["role"] == "admin"


def test_smtp_config_requires_all_fields(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "h"); monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    assert mailer.SmtpConfig.from_env() is None


def test_email_rate_limited(app, smtp, monkeypatch):
    from src.api import email as email_api
    monkeypatch.setattr(email_api, "EMAILS_PER_HOUR", 2)
    client = login(app, *ADMIN)
    codes = [client.post("/api/email/send", json={"to": "a@b.dev", "subject": "s", "body": "b"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429] and len(smtp.sent) == 2
