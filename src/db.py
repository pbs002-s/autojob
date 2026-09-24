import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.models import JobListing

class Database:
    def __init__(self, db_path: str = "data/autojob.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    external_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    company TEXT,
                    url TEXT NOT NULL,
                    description TEXT,
                    budget_or_salary TEXT,
                    location TEXT,
                    tags TEXT,
                    match_score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'discovered',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Applications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    proposal_text TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'submitted',
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)

            # Conversations table (for holding clients)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    last_message_text TEXT,
                    last_reply_text TEXT,
                    status TEXT DEFAULT 'active',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_job(self, job: JobListing) -> bool:
        """Saves a new job listing if it does not already exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO jobs 
                    (platform, external_id, title, company, url, description, budget_or_salary, location, tags, match_score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.platform,
                    job.external_id,
                    job.title,
                    job.company,
                    job.url,
                    job.description,
                    job.budget_or_salary,
                    job.location,
                    json.dumps(job.tags),
                    job.match_score,
                    job.status
                ))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Error saving job: {e}")
                return False

    def get_unapplied_jobs(self, min_score: float = 0.0) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE status = 'discovered' AND match_score >= ? 
                ORDER BY match_score DESC, created_at DESC
            """, (min_score,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_job_status(self, job_id: int, status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
            conn.commit()

    def record_application(self, job_id: int, proposal_text: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO applications (job_id, proposal_text)
                VALUES (?, ?)
            """, (job_id, proposal_text))
            cursor.execute("UPDATE jobs SET status = 'applied' WHERE id = ?", (job_id,))
            conn.commit()

    def record_conversation(self, platform: str, client_name: str, message_text: str, reply_text: str, status: str = 'responded') -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (platform, client_name, last_message_text, last_reply_text, status)
                VALUES (?, ?, ?, ?, ?)
            """, (platform, client_name, message_text, reply_text, status))
            conn.commit()
            return cursor.lastrowid

    def get_conversations(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status and status != 'all':
                cursor.execute("""
                    SELECT * FROM conversations WHERE status = ? ORDER BY updated_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT * FROM conversations ORDER BY updated_at DESC
                """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_conversation_status(self, conv_id: int, status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE conversations SET status = ? WHERE id = ?", (status, conv_id))
            conn.commit()

