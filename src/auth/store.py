"""SQLite persistence for users, sessions and the audit log."""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.auth.security import hash_password, hash_token, new_token

SESSION_TTL = timedelta(hours=12)
ROLES = ("admin", "operator", "viewer")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin','operator','viewer')),
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    target TEXT,
                    created_at TEXT NOT NULL
                );
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # --- users -------------------------------------------------------------
    def create_user(self, email: str, password: str, role: str, is_demo: bool = False) -> int:
        if role not in ROLES:
            raise ValueError(f"Unknown role: {role}")
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, role, is_demo, created_at) VALUES (?, ?, ?, ?, ?)",
                (email.strip().lower(), hash_password(password), role, int(is_demo), _now().isoformat()),
            )
            return cur.lastrowid

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
            return dict(row) if row else None

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def list_users(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, email, role, is_demo, disabled, created_at FROM users WHERE is_demo = 0 ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_user(self, user_id: int, role: Optional[str] = None, disabled: Optional[bool] = None) -> None:
        if role is not None and role not in ROLES:
            raise ValueError(f"Unknown role: {role}")
        with self._conn() as conn:
            if role is not None:
                conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            if disabled is not None:
                conn.execute("UPDATE users SET disabled = ? WHERE id = ?", (int(disabled), user_id))
                if disabled:
                    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def count_admins(self) -> int:
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_demo = 0 AND disabled = 0"
            ).fetchone()[0]

    def ensure_demo_user(self, role: str) -> int:
        email = f"demo-{role}@autojob.local"
        existing = self.get_user_by_email(email)
        if existing:
            return existing["id"]
        # Demo users can only be entered via /api/auth/demo; the random password is never revealed.
        return self.create_user(email, new_token(), role, is_demo=True)

    # --- sessions ----------------------------------------------------------
    def create_session(self, user_id: int) -> Dict[str, str]:
        token, csrf = new_token(), new_token()
        now = _now()
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, csrf_token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (hash_token(token), user_id, csrf, now.isoformat(), (now + SESSION_TTL).isoformat()),
            )
        return {"token": token, "csrf_token": csrf}

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT s.csrf_token, s.expires_at, u.id AS user_id, u.email, u.role, u.is_demo, u.disabled
                   FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?""",
                (hash_token(token),),
            ).fetchone()
        if not row:
            return None
        session = dict(row)
        if session["disabled"] or datetime.fromisoformat(session["expires_at"]) < _now():
            self.delete_session(token)
            return None
        return session

    def delete_session(self, token: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))

    # --- audit -------------------------------------------------------------
    def audit(self, user_id: Optional[int], action: str, target: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id, action, target, created_at) VALUES (?, ?, ?, ?)",
                (user_id, action, target, _now().isoformat()),
            )

    def list_audit(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT a.id, a.action, a.target, a.created_at, u.email FROM audit_log a
                   LEFT JOIN users u ON u.id = a.user_id ORDER BY a.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
