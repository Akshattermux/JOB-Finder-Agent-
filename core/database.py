import os
import aiosqlite
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from core.models import Job, JobStatus, JobEvaluation, TailoredApplication


def compute_job_hash(url: str, title: str, company: str) -> str:
    """Generate a unique hash for deduplication."""
    raw = f"{url.strip().lower()}|{title.strip().lower()}|{company.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Initialize tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    source TEXT DEFAULT 'direct',
                    job_hash TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL DEFAULT 'DISCOVERED',
                    score INTEGER,
                    evaluation_json TEXT,
                    cover_letter TEXT,
                    answers_json TEXT,
                    applied_at TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(status);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_job_hash ON jobs(job_hash);")
            await db.commit()

    async def save_job(self, title: str, company: str, location: str, url: str, description: str, source: str = "direct") -> Optional[Job]:
        """Save a new job posting if it doesn't already exist."""
        job_hash = compute_job_hash(url, title, company)
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("""
                    INSERT INTO jobs (title, company, location, url, description, source, job_hash, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, company, location, url, description, source, job_hash, JobStatus.DISCOVERED.value, now))
                await db.commit()
                job_id = cursor.lastrowid
                return Job(
                    id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    description=description,
                    source=source,
                    job_hash=job_hash,
                    status=JobStatus.DISCOVERED,
                    created_at=now
                )
            except aiosqlite.IntegrityError:
                # Job already exists (duplicate URL or job_hash)
                return None

    async def get_jobs_by_status(self, status: JobStatus, limit: int = 50) -> List[Job]:
        """Retrieve jobs matching a given status."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM jobs WHERE status = ? ORDER BY id ASC LIMIT ?
            """, (status.value, limit)) as cursor:
                rows = await cursor.fetchall()
                return [Job(**dict(row)) for row in rows]

    async def get_job_by_id(self, job_id: int) -> Optional[Job]:
        """Retrieve a single job by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                return Job(**dict(row)) if row else None

    async def get_all_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Job]:
        """Retrieve jobs, optionally filtered by status, ordered by ID descending."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                query = "SELECT * FROM jobs WHERE status = ? ORDER BY id DESC LIMIT ?"
                params = (status.value, limit)
            else:
                query = "SELECT * FROM jobs ORDER BY id DESC LIMIT ?"
                params = (limit,)
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [Job(**dict(row)) for row in rows]


    async def update_job_evaluation(self, job_id: int, evaluation: JobEvaluation):
        """Update job with evaluation score and JSON."""
        status = JobStatus.EVALUATED if evaluation.apply else JobStatus.SKIPPED
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE jobs 
                SET score = ?, evaluation_json = ?, status = ?
                WHERE id = ?
            """, (evaluation.score, evaluation.model_dump_json(), status.value, job_id))
            await db.commit()

    async def update_job_tailored(self, job_id: int, cover_letter: str, answers: List[Any]):
        """Update job with tailored cover letter and screening QA."""
        answers_json = json.dumps([a.model_dump() if hasattr(a, 'model_dump') else a for a in answers])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE jobs 
                SET cover_letter = ?, answers_json = ?, status = ?
                WHERE id = ?
            """, (cover_letter, answers_json, JobStatus.TAILORED.value, job_id))
            await db.commit()

    async def update_job_status(self, job_id: int, status: JobStatus, notes: Optional[str] = None):
        """Update job status and optional notes."""
        applied_at = datetime.utcnow().isoformat() if status == JobStatus.APPLIED else None
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE jobs 
                SET status = ?, notes = ?, applied_at = COALESCE(?, applied_at)
                WHERE id = ?
            """, (status.value, notes, applied_at, job_id))
            await db.commit()

    async def get_pipeline_stats(self) -> Dict[str, int]:
        """Get summary count of jobs grouped by status."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status") as cursor:
                rows = await cursor.fetchall()
                stats = {s.value: 0 for s in JobStatus}
                for status, count in rows:
                    stats[status] = count
                return stats
