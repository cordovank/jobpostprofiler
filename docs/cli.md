# CLI Reference

JobPostProfiler has two CLI entry points:

1. **Pipeline CLI** (`python -m jobpostprofiler.main`) — runs the extraction pipeline
2. **Tracker CLI** (`python tracker_cli.py`) — manages the job search pipeline

All commands are run from the repo root.

---

## Pipeline CLI

```bash
uv run -m jobpostprofiler.main
```

Runs the full extraction pipeline on the example posting hardcoded in `main.py`. Useful for verifying that your provider config works. Output is written to `output/{run_id}/`.

For real use, prefer the Streamlit UI:

```bash
uv run streamlit run src/jobpostprofiler/ui/app.py
```

---

## Tracker CLI

The tracker CLI manages jobs stored in `jobs.db` (SQLite, auto-created at repo root on first use).

### `status` — View the pipeline

Show all tracked jobs with status counts.

```bash
python tracker_cli.py status
```

```
==========================================================================================
  JOB TRACKER  —  2026-03-30  —  5 total
  applied:2  found:3
==========================================================================================
  [  5] 🔍 found          Acme Corp                 ML Engineer                          2026-03-30  $150k-$200k  Remote  QA:✓  Match:85%
  [  4] 📤 applied         Beta Inc                  Data Scientist                       2026-03-28  $120k-$160k  Hybrid  QA:✓  Match:70%
  ...
==========================================================================================
```

Filter by status:

```bash
python tracker_cli.py status --status applied
```

Valid statuses: `found`, `applied`, `phone_screen`, `technical`, `offer`, `rejected`, `ghosted`.

---

### `show` — Job detail view

Display all stored fields for a single job, including skills, match score breakdown, QA status, and a preview of the JD text.

```bash
python tracker_cli.py show 5
```

```
======================================================================
  🔍 Job #5  —  ML Engineer
======================================================================
  Company:         Acme Corp
  Location:        Remote, US
  Remote policy:   Remote
  Employment type: Full-time
  Salary range:    $150k-$200k
  Status:          found
  Date found:      2026-03-30
  Source channel:   linkedin
  QA passed:       ✓
  Required skills: Python, PyTorch, SQL, Docker
  Preferred skills:Kubernetes, Spark

  Skill Match:     85%
    Required:      3/4  Python, PyTorch, SQL
    Missing:       Docker
    Preferred:     1/2  Spark
    Missing:       Kubernetes
  URL:             https://example.com/jobs/ml-engineer

──────────────────────────────────────────────────────────────────────
  JD Preview (first 500 chars):

    ML Engineer — Acme Corp
    Location: Remote, US
    ...

    ... (2400 chars total — use --full to see all)
======================================================================
```

Show the full JD text:

```bash
python tracker_cli.py show 5 --full
```

---

### `search` — Find jobs by keyword

Search across title, company, notes, required skills, and preferred skills. Case-insensitive.

```bash
python tracker_cli.py search Python
```

```
==========================================================================================
  SEARCH: 'Python'  —  3 result(s)
==========================================================================================
  [  5] 🔍 found          Acme Corp                 ML Engineer                          ...
  [  4] 📤 applied         Beta Inc                  Data Scientist                       ...
  [  2] 🔍 found          Gamma LLC                 Backend Engineer                     ...
==========================================================================================
```

```bash
python tracker_cli.py search "Acme Corp"
python tracker_cli.py search PyTorch
python tracker_cli.py search "async culture"    # searches notes too
```

---

### `apply` — Log an application

Record that you applied for a job. Automatically sets status to `applied` and creates a follow-up reminder.

```bash
python tracker_cli.py apply 5 --resume ML
```

```
[tracker] Applied → job_id=5  resume=ML  follow_up=2026-04-06
  ✓ Logged application for: Acme Corp | ML Engineer
```

Options:

```bash
python tracker_cli.py apply 5 --resume SWE --cover "Referred by Jane" --followup-days 10 --notes "Strong match"
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--resume` | Yes | — | Resume variant: `ML`, `SWE`, or `custom` |
| `--cover` | No | `""` | Short cover note |
| `--followup-days` | No | `7` | Days until follow-up reminder |
| `--notes` | No | `""` | Application-specific notes |

---

### `update` — Change job status

Move a job through the pipeline.

```bash
python tracker_cli.py update 5 --status phone_screen
```

```
  ✓ Acme Corp | ML Engineer  →  phone_screen
```

Status flow:

```
found → applied → phone_screen → technical → offer
                                            → rejected
                                            → ghosted
```

---

### `notes` — Add notes to a job

Save or replace notes on a job. Notes are visible in `show` and searchable via `search`.

```bash
python tracker_cli.py notes 5 "Great team, fully async, strong ML infra"
```

```
  ✓ Notes updated for job_id=5
```

---

### `followup` — Check what needs attention

Show applications whose follow-up date has arrived. Only shows jobs still in `applied` status.

```bash
python tracker_cli.py followup
```

```
======================================================================
  FOLLOW-UPS DUE  —  2026-04-06
======================================================================
  [  5] Acme Corp                 ML Engineer                     due:2026-04-06
  [  3] Delta Corp                Senior SWE                      due:2026-04-04
======================================================================
  Tip: python tracker_cli.py update <id> --status phone_screen
```

If nothing is due:

```
  ✓ No follow-ups due today.
```

---

### `export` — Generate Markdown report

Produce a Markdown summary of the full pipeline. Useful for pasting into a Claude Project or sharing with a mentor.

Print to stdout:

```bash
python tracker_cli.py export
```

Write to file:

```bash
python tracker_cli.py export --out weekly_report.md
```

Output includes:
- Status count table
- All jobs with ID, status, company, title, date found, source channel, and resume used
- Follow-ups due section (if any)

---

### `save` — Load a pipeline run into the DB

Manually import a previous pipeline run from its output directory. Useful for runs completed before the tracker was added, or for re-importing.

```bash
python tracker_cli.py save output/20260330_143000
```

```
[tracker] Saved → jobs.id=6  Acme Corp | ML Engineer
  ✓ Saved as job_id=6
  → To log an application: python tracker_cli.py apply 6 --resume ML
```

Tag the source channel:

```bash
python tracker_cli.py save output/20260330_143000 --channel wellfound
```

Valid channels: `wellfound`, `yc`, `linkedin`, `direct`, `other` (default).

---

## Skill Match Scoring

When `my_skills.json` exists at repo root, the pipeline computes a match score for every extraction. No LLM calls — pure Python set intersection on already-extracted skills.

### Setup

```bash
cp my_skills.example.json my_skills.json
```

Edit `my_skills.json`:

```json
{
  "skills": ["Python", "SQL", "PyTorch", "Docker", "AWS", "FastAPI", "pandas"]
}
```

### How scoring works

| Metric | Formula |
|---|---|
| `required_pct` | (matched required skills) / (total required skills) |
| `preferred_pct` | (matched preferred skills) / (total preferred skills) |
| `overall_score` | 0.7 x required_pct + 0.3 x preferred_pct |

- Matching is case-insensitive and whitespace-tolerant
- If a job has no required skills, `required_pct` defaults to 1.0
- If a job has no preferred skills, `preferred_pct` defaults to 1.0
- Score is stored in `jobs.match_score` and shown in `status`, `show`, and the Streamlit Tracker tab

### Where scores appear

- **`status`** — appended to each row as `Match:85%`
- **`show <id>`** — full breakdown showing matched/missing skills for each category
- **Streamlit UI** — Extractor tab shows score card after extraction; Tracker tab shows score column in the jobs table

---

## Duplicate URL Detection

The pipeline checks `jobs.db` for an existing row with the same URL before making LLM calls. If a duplicate is found:

- **Pipeline**: raises `ValueError` with the existing job ID
- **Streamlit UI**: shows the error; use the "Force re-process" checkbox to override
- **`save` command**: always inserts (no duplicate check on manual save)

This prevents wasted LLM calls when re-processing the same posting.
