"""
db/store.py

SQLite persistence layer for the job tracker.
Receives a PostingExtract (validated Pydantic model from JobPostProfiler)
and writes it to jobs.db.

No LLM dependencies. Pure Python + sqlite3.
"""

import sqlite3
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# --- Config -----------------------------------------------------------

from jobpostprofiler.config import DB_PATH

VALID_STATUSES = {
    "found",
    "applied",
    "phone_screen",
    "technical",
    "offer",
    "rejected",
    "ghosted",
}

# --- Schema -----------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT,
    url             TEXT,
    title           TEXT,
    company         TEXT,
    location        TEXT,
    remote_policy   TEXT,
    employment_type TEXT,
    salary_range    TEXT,
    required_skills TEXT,       -- JSON array
    preferred_skills TEXT,      -- JSON array
    source_channel  TEXT,       -- wellfound | yc | linkedin | direct | other
    date_found      TEXT,       -- ISO date
    status          TEXT DEFAULT 'found',
    qa_passed       INTEGER,    -- 0 or 1
    qa_issues       TEXT,       -- JSON array
    jd_text         TEXT,       -- normalized posting text (from fetcher)
    match_score     REAL,       -- 0.0–1.0 skill match score
    extract_json    TEXT,       -- full PostingExtract JSON
    markdown_rendered TEXT,     -- precomputed render_markdown() output
    qa_json         TEXT,       -- full QAReport JSON
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id),
    date_applied    TEXT,       -- ISO date
    resume_used     TEXT,       -- 'ML' | 'SWE' | 'custom'
    cover_note      TEXT,
    follow_up_date  TEXT,       -- ISO date
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_company  ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_date     ON jobs(date_found);
"""


# --- Init -------------------------------------------------------------

def _migrate(conn: sqlite3.Connection) -> None:
    """Run idempotent migrations for schema additions."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "match_score" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN match_score REAL")
    if "extract_json" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN extract_json TEXT")
    if "markdown_rendered" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN markdown_rendered TEXT")
    if "qa_json" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN qa_json TEXT")
    if "updated_at" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN updated_at TEXT")
    conn.commit()


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create tables if they don't exist. Return open connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _migrate(conn)
    return conn


# --- Field extraction ------------------------------------------------
#
# PostingExtract.details is a discriminated union:
#   kind="employment"  → details.role.job_title, details.company.name,
#                        details.role.location, details.role.workplace_type,
#                        details.role.employment_type, details.role.compensation
#   kind="internship"  → same nested shape as employment
#   kind="freelance"   → details.title, details.budget / details.hourly_rate,
#                        details.contract_type  (flat, no role/company sub-objects)
#
# This function normalises all three shapes into a flat dict for the DB row.

def _extract_fields(details: dict) -> dict:
    kind = details.get("kind", "employment")

    if kind in ("employment", "internship"):
        role    = details.get("role") or {}
        company = details.get("company") or {}
        return {
            "title":            role.get("job_title"),
            "company":          company.get("name"),
            "location":         role.get("location"),
            "remote_policy":    role.get("workplace_type"),
            "employment_type":  role.get("employment_type"),
            "salary_range":     role.get("compensation"),
        }

    # freelance — flat shape
    return {
        "title":            details.get("title"),
        "company":          None,
        "location":         None,
        "remote_policy":    None,
        "employment_type":  details.get("contract_type"),
        "salary_range":     details.get("budget") or details.get("hourly_rate"),
    }


# --- Insert -----------------------------------------------------------

def save_job_from_extract(
    extract: dict,
    qa_report: dict,
    run_id: str,
    normalized_text: str = "",
    source_channel: str = "other",
    db_path: Path = DB_PATH,
    match_score: float | None = None,
    extract_json: str = "",
    markdown_rendered: str = "",
    qa_json: str = "",
) -> int:
    """
    Insert a job record from a PostingExtract dict (job_extract.json content).
    Returns the new row id.

    Args:
        extract:           PostingExtract.model_dump() result
        qa_report:         QAReport.model_dump() result
        run_id:            Pipeline run_id (correlation key)
        normalized_text:   Contents of normalized_job_post.txt (optional)
        source_channel:    wellfound | yc | linkedin | direct | other
        db_path:           Override for testing
        match_score:       Skill match score (0.0–1.0), or None if unavailable
        extract_json:      Full PostingExtract JSON string
        markdown_rendered: Precomputed markdown summary
        qa_json:           Full QAReport JSON string
    """
    details  = extract.get("details") or {}
    skills   = extract.get("skills") or {}
    source   = extract.get("source") or {}
    fields   = _extract_fields(details)

    row = {
        "run_id":           run_id,
        "url":              source.get("url"),
        "title":            fields["title"],
        "company":          fields["company"],
        "location":         fields["location"],
        "remote_policy":    fields["remote_policy"],
        "employment_type":  fields["employment_type"],
        "salary_range":     fields["salary_range"],
        "required_skills":  json.dumps(skills.get("required") or []),
        "preferred_skills": json.dumps(skills.get("preferred") or []),
        "source_channel":   source_channel,
        "date_found":       date.today().isoformat(),
        "status":           "found",
        "qa_passed":        1 if qa_report.get("passed") else 0,
        "qa_issues":        json.dumps(qa_report.get("issues") or []),
        "match_score":       match_score,
        "jd_text":           normalized_text,
        "extract_json":      extract_json,
        "markdown_rendered": markdown_rendered,
        "qa_json":           qa_json,
        "notes":             None,
    }

    conn    = init_db(db_path)
    cursor  = conn.execute(
        """
        INSERT INTO jobs (
            run_id, url, title, company, location, remote_policy,
            employment_type, salary_range, required_skills, preferred_skills,
            source_channel, date_found, status, qa_passed, qa_issues,
            match_score, jd_text, extract_json, markdown_rendered, qa_json, notes
        ) VALUES (
            :run_id, :url, :title, :company, :location, :remote_policy,
            :employment_type, :salary_range, :required_skills, :preferred_skills,
            :source_channel, :date_found, :status, :qa_passed, :qa_issues,
            :match_score, :jd_text, :extract_json, :markdown_rendered, :qa_json, :notes
        )
        """,
        row,
    )
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    print(f"[tracker] Saved → jobs.id={job_id}  {row['company']} | {row['title']}")
    return job_id



# --- Read -------------------------------------------------------------

def list_jobs(
    status: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> list[dict]:
    conn = init_db(db_path)
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY date_found DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY date_found DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_jobs(query: str, db_path: Path = DB_PATH) -> list[dict]:
    """Search jobs by keyword across title, company, notes, and skills."""
    conn = init_db(db_path)
    like = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM jobs
           WHERE title LIKE ? OR company LIKE ? OR notes LIKE ?
              OR required_skills LIKE ? OR preferred_skills LIKE ?
           ORDER BY date_found DESC""",
        (like, like, like, like, like),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job_by_url(url: str, db_path: Path = DB_PATH) -> Optional[dict]:
    """Return the first job matching the given URL, or None."""
    if not url:
        return None
    conn = init_db(db_path)
    row = conn.execute("SELECT * FROM jobs WHERE url = ?", (url,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_job(job_id: int, db_path: Path = DB_PATH) -> Optional[dict]:
    conn = init_db(db_path)
    row  = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Update -----------------------------------------------------------

def update_status(job_id: int, status: str, db_path: Path = DB_PATH) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Choose from: {VALID_STATUSES}")
    conn = init_db(db_path)
    conn.execute(
        "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(timespec="seconds"), job_id),
    )
    conn.commit()
    conn.close()


def add_application(
    job_id: int,
    resume_used: str,
    cover_note: str = "",
    follow_up_days: int = 7,
    notes: str = "",
    db_path: Path = DB_PATH,
) -> None:
    """Log an application. Also flips jobs.status → 'applied'."""
    applied_date = date.today().isoformat()
    follow_up    = date.fromordinal(date.today().toordinal() + follow_up_days).isoformat()

    conn = init_db(db_path)
    conn.execute(
        """
        INSERT INTO applications (job_id, date_applied, resume_used, cover_note, follow_up_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (job_id, applied_date, resume_used, cover_note, follow_up, notes),
    )
    conn.execute(
        "UPDATE jobs SET status = 'applied', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"), job_id),
    )
    conn.commit()
    conn.close()
    print(f"[tracker] Applied → job_id={job_id}  resume={resume_used}  follow_up={follow_up}")


def update_notes(job_id: int, notes: str, db_path: Path = DB_PATH) -> None:
    conn = init_db(db_path)
    conn.execute(
        "UPDATE jobs SET notes = ?, updated_at = ? WHERE id = ?",
        (notes, datetime.now().isoformat(timespec="seconds"), job_id),
    )
    conn.commit()
    conn.close()


# Columns that can be edited via update_job()
EDITABLE_FIELDS = {
    "title", "company", "location", "remote_policy",
    "employment_type", "salary_range", "status", "notes",
    "source_channel",
}


def update_job(job_id: int, db_path: Path = DB_PATH, **fields) -> bool:
    """Update one or more editable fields on a job record. Returns True if a row was updated."""
    to_set = {k: v for k, v in fields.items() if k in EDITABLE_FIELDS}
    if not to_set:
        return False
    if "status" in to_set and to_set["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{to_set['status']}'. Choose from: {VALID_STATUSES}")
    to_set["updated_at"] = datetime.now().isoformat(timespec="seconds")
    set_clause = ", ".join(f"{col} = ?" for col in to_set)
    values = list(to_set.values()) + [job_id]
    conn = init_db(db_path)
    cursor = conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def delete_job(job_id: int, db_path: Path = DB_PATH) -> bool:
    """Delete a job and its applications. Returns True if a row was deleted."""
    conn = init_db(db_path)
    conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
    cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# --- Export -----------------------------------------------------------

def export_job(job_id: int, dest_dir: Path, db_path: Path = DB_PATH) -> Path:
    """Export a job's artifacts to a directory from DB columns.

    Creates dest_dir/ with normalized_job_post.txt, job_extract.json,
    job_summary.md, quality_report.json, and posting_kind.json.
    Returns dest_dir. Raises ValueError if job not found or artifacts missing.
    """
    job = get_job(job_id, db_path)
    if not job:
        raise ValueError(f"Job id={job_id} not found.")
    if not job.get("extract_json"):
        raise ValueError(
            f"Job id={job_id} has no stored extract_json (legacy row). Cannot export."
        )

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # normalized_job_post.txt
    (dest_dir / "normalized_job_post.txt").write_text(
        job.get("jd_text") or "", encoding="utf-8"
    )
    # job_extract.json
    (dest_dir / "job_extract.json").write_text(
        job["extract_json"], encoding="utf-8"
    )
    # job_summary.md
    (dest_dir / "job_summary.md").write_text(
        job.get("markdown_rendered") or "", encoding="utf-8"
    )
    # quality_report.json
    (dest_dir / "quality_report.json").write_text(
        job.get("qa_json") or "", encoding="utf-8"
    )
    # posting_kind.json — derived from extract_json
    try:
        extract_data = json.loads(job["extract_json"])
        kind = extract_data.get("details", {}).get("kind", "employment")
    except (json.JSONDecodeError, TypeError):
        kind = "employment"
    (dest_dir / "posting_kind.json").write_text(
        json.dumps({"kind": kind, "warnings": []}, indent=2), encoding="utf-8"
    )

    return dest_dir


# --- Follow-up helpers ------------------------------------------------

def due_for_followup(db_path: Path = DB_PATH) -> list[dict]:
    """Return applications whose follow_up_date is today or in the past."""
    today = date.today().isoformat()
    conn  = init_db(db_path)
    rows  = conn.execute(
        """
        SELECT a.*, j.title, j.company, j.url
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.follow_up_date <= ?
          AND j.status = 'applied'
        ORDER BY a.follow_up_date ASC
        """,
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]