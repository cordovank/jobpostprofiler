"""
tracker_cli.py

Command-line interface for the job tracker.
Drop this file into the root of your JobPostProfiler repo.

Usage:
    python tracker_cli.py status                    # full pipeline view
    python tracker_cli.py status --status found     # filter by status
    python tracker_cli.py apply <job_id> --resume ML
    python tracker_cli.py update <job_id> --status phone_screen
    python tracker_cli.py notes <job_id> "Great team, async culture"
    python tracker_cli.py followup                  # what needs attention
    python tracker_cli.py export                    # weekly Markdown report
    python tracker_cli.py save <output_dir>         # load a run into DB
    python tracker_cli.py save <output_dir> --channel wellfound
    python tracker_cli.py save output/{run_id}/ --channel wellfound
    python tracker_cli.py show <job_id>                     # full detail view
    python tracker_cli.py show <job_id> --full              # include full JD text
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).parent / "src"))

from jobpostprofiler.db.store import (
    DB_PATH,
    add_application,
    due_for_followup,
    get_job,
    init_db,
    list_jobs,
    search_jobs,
    save_job_from_output_dir,
    update_notes,
    update_status,
)

# ── Formatting helpers ────────────────────────────────────────────────

STATUS_EMOJI = {
    "found":        "🔍",
    "applied":      "📤",
    "phone_screen": "📞",
    "technical":    "💻",
    "offer":        "🎉",
    "rejected":     "❌",
    "ghosted":      "👻",
}

def _fmt_row(j: dict) -> str:
    emoji = STATUS_EMOJI.get(j["status"], "•")
    salary = f"  {j['salary_range']}" if j.get("salary_range") else ""
    remote = f"  {j['remote_policy']}" if j.get("remote_policy") else ""
    qa = "✓" if j.get("qa_passed") else "⚠"
    return (
        f"  [{j['id']:>3}] {emoji} {j['status']:<14} "
        f"{(j.get('company') or 'Unknown'):<25} "
        f"{(j.get('title') or 'Unknown'):<35} "
        f"{j.get('date_found','')}{salary}{remote}  QA:{qa}"
    )


# ── Commands ──────────────────────────────────────────────────────────

def cmd_status(args):
    jobs = list_jobs(status=args.status)
    if not jobs:
        print("No jobs found." + (f" (status={args.status})" if args.status else ""))
        return

    # Summary counts
    from collections import Counter
    counts = Counter(j["status"] for j in jobs)
    print(f"\n{'='*90}")
    print(f"  JOB TRACKER  —  {date.today()}  —  {len(jobs)} total")
    print(f"  " + "  ".join(f"{k}:{v}" for k, v in sorted(counts.items())))
    print(f"{'='*90}")
    for j in jobs:
        print(_fmt_row(j))
    print(f"{'='*90}\n")


def cmd_show(args):
    """Display full details for a single job."""
    job = get_job(args.job_id)
    if not job:
        print(f"Job id={args.job_id} not found.")
        return

    emoji = STATUS_EMOJI.get(job["status"], "•")
    print(f"\n{'='*70}")
    print(f"  {emoji} Job #{job['id']}  —  {job.get('title') or 'Unknown'}")
    print(f"{'='*70}")
    print(f"  Company:         {job.get('company') or 'Unknown'}")
    print(f"  Location:        {job.get('location') or 'Not stated'}")
    print(f"  Remote policy:   {job.get('remote_policy') or 'Not stated'}")
    print(f"  Employment type: {job.get('employment_type') or 'Not stated'}")
    print(f"  Salary range:    {job.get('salary_range') or 'Not stated'}")
    print(f"  Status:          {job['status']}")
    print(f"  Date found:      {job.get('date_found', '')}")
    print(f"  Source channel:  {job.get('source_channel', '')}")
    print(f"  QA passed:       {'✓' if job.get('qa_passed') else '⚠'}")

    qa_issues = json.loads(job.get("qa_issues") or "[]")
    if qa_issues:
        print(f"  QA issues:       {', '.join(qa_issues)}")

    req = json.loads(job.get("required_skills") or "[]")
    pref = json.loads(job.get("preferred_skills") or "[]")
    if req:
        print(f"  Required skills: {', '.join(req)}")
    if pref:
        print(f"  Preferred skills:{', '.join(pref)}")

    if job.get("url"):
        print(f"  URL:             {job['url']}")

    if job.get("notes"):
        print(f"\n  Notes: {job['notes']}")

    if args.full and job.get("jd_text"):
        print(f"\n{'─'*70}")
        print("  JD Text:\n")
        for line in job["jd_text"].splitlines():
            print(f"    {line}")
    elif job.get("jd_text"):
        preview = job["jd_text"][:500]
        print(f"\n{'─'*70}")
        print(f"  JD Preview (first 500 chars):\n")
        for line in preview.splitlines():
            print(f"    {line}")
        if len(job["jd_text"]) > 500:
            print(f"\n    ... ({len(job['jd_text'])} chars total — use --full to see all)")

    print(f"{'='*70}\n")


def cmd_search(args):
    """Search jobs by keyword across title, company, notes, and skills."""
    jobs = search_jobs(args.query)
    if not jobs:
        print(f"No jobs matching '{args.query}'.")
        return

    print(f"\n{'='*90}")
    print(f"  SEARCH: '{args.query}'  —  {len(jobs)} result(s)")
    print(f"{'='*90}")
    for j in jobs:
        print(_fmt_row(j))
    print(f"{'='*90}\n")


def cmd_apply(args):
    job = get_job(args.job_id)
    if not job:
        print(f"Job id={args.job_id} not found.")
        return
    add_application(
        job_id=args.job_id,
        resume_used=args.resume,
        cover_note=args.cover or "",
        follow_up_days=args.followup_days,
        notes=args.notes or "",
    )
    print(f"  ✓ Logged application for: {job.get('company')} | {job.get('title')}")


def cmd_update(args):
    job = get_job(args.job_id)
    if not job:
        print(f"Job id={args.job_id} not found.")
        return
    update_status(args.job_id, args.status)
    print(f"  ✓ {job.get('company')} | {job.get('title')}  →  {args.status}")


def cmd_notes(args):
    job = get_job(args.job_id)
    if not job:
        print(f"Job id={args.job_id} not found.")
        return
    update_notes(args.job_id, args.text)
    print(f"  ✓ Notes updated for job_id={args.job_id}")


def cmd_followup(args):
    due = due_for_followup()
    if not due:
        print("\n  ✓ No follow-ups due today.\n")
        return
    print(f"\n{'='*70}")
    print(f"  FOLLOW-UPS DUE  —  {date.today()}")
    print(f"{'='*70}")
    for r in due:
        print(f"  [{r['job_id']:>3}] {r.get('company','?'):<25} {r.get('title','?'):<30}  due:{r['follow_up_date']}")
    print(f"{'='*70}")
    print(f"  Tip: python tracker_cli.py update <id> --status phone_screen\n")


def cmd_export(args):
    """Generate a Markdown pipeline summary for pasting into Claude Project."""
    jobs = list_jobs()
    today = date.today().isoformat()
    lines = [
        f"# Job Tracker Export — {today}\n",
        "## Pipeline Summary\n",
    ]

    from collections import Counter
    counts = Counter(j["status"] for j in jobs)
    lines.append("| Status | Count |")
    lines.append("|---|---|")
    for status, count in sorted(counts.items()):
        lines.append(f"| {status} | {count} |")
    lines.append("")

    lines.append("## Jobs\n")
    lines.append("| ID | Status | Company | Title | Date Found | Channel | Resume |")
    lines.append("|---|---|---|---|---|---|---|")

    # Join applications for resume info
    conn = init_db()
    app_rows = conn.execute("SELECT job_id, resume_used FROM applications").fetchall()
    conn.close()
    resume_map = {r["job_id"]: r["resume_used"] for r in app_rows}

    for j in jobs:
        resume = resume_map.get(j["id"], "—")
        lines.append(
            f"| {j['id']} | {j['status']} | {j.get('company','?')} | "
            f"{j.get('title','?')} | {j.get('date_found','')} | "
            f"{j.get('source_channel','?')} | {resume} |"
        )

    lines.append("")

    # Follow-ups
    due = due_for_followup()
    if due:
        lines.append("## ⚠ Follow-ups Due\n")
        for r in due:
            lines.append(f"- [{r['job_id']}] {r.get('company','?')} | {r.get('title','?')}  (due: {r['follow_up_date']})")
        lines.append("")

    output = "\n".join(lines)

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(output, encoding="utf-8")
        print(f"  ✓ Exported to {out_path}")
    else:
        print(output)


def cmd_save(args):
    """Load a completed pipeline run into the DB."""
    output_dir = Path(args.dir)
    if not output_dir.exists():
        print(f"Directory not found: {output_dir}")
        return
    job_id = save_job_from_output_dir(
        output_dir=output_dir,
        source_channel=args.channel,
    )
    print(f"  ✓ Saved as job_id={job_id}")
    print(f"  → To log an application: python tracker_cli.py apply {job_id} --resume ML")


# ── Argument parser ───────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tracker_cli",
        description="Job Tracker CLI — powered by JobPostProfiler",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Show pipeline")
    p_status.add_argument("--status", choices=[
        "found","applied","phone_screen","technical","offer","rejected","ghosted"
    ], default=None)

    # search
    p_search = sub.add_parser("search", help="Search jobs by keyword")
    p_search.add_argument("query", help="Search term (matches title, company, notes, skills)")

    # show
    p_show = sub.add_parser("show", help="Show full details for a job")
    p_show.add_argument("job_id", type=int)
    p_show.add_argument("--full", action="store_true", help="Show full JD text")

    # apply
    p_apply = sub.add_parser("apply", help="Log an application")
    p_apply.add_argument("job_id", type=int)
    p_apply.add_argument("--resume", required=True, choices=["ML", "SWE", "custom"],
                         help="Which resume variant was used")
    p_apply.add_argument("--cover", default="", help="Short cover note")
    p_apply.add_argument("--followup-days", type=int, default=7,
                         help="Days until follow-up reminder (default: 7)")
    p_apply.add_argument("--notes", default="")

    # update
    p_update = sub.add_parser("update", help="Update job status")
    p_update.add_argument("job_id", type=int)
    p_update.add_argument("--status", required=True, choices=[
        "found","applied","phone_screen","technical","offer","rejected","ghosted"
    ])

    # notes
    p_notes = sub.add_parser("notes", help="Add/replace notes for a job")
    p_notes.add_argument("job_id", type=int)
    p_notes.add_argument("text")

    # followup
    sub.add_parser("followup", help="Show follow-ups due today")

    # export
    p_export = sub.add_parser("export", help="Generate Markdown report")
    p_export.add_argument("--out", default=None, help="Write to file path (default: stdout)")

    # save
    p_save = sub.add_parser("save", help="Load a pipeline run into the DB")
    p_save.add_argument("dir", help="Path to output/{run_id}/ directory")
    p_save.add_argument("--channel", default="other",
                        choices=["wellfound","yc","linkedin","direct","other"])

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "status":   cmd_status,
        "search":   cmd_search,
        "show":     cmd_show,
        "apply":    cmd_apply,
        "update":   cmd_update,
        "notes":    cmd_notes,
        "followup": cmd_followup,
        "export":   cmd_export,
        "save":     cmd_save,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()