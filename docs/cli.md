# CLI Reference

HireSignal has two CLI entry points:

1. **Pipeline CLI** (`make cli`) — runs the extraction pipeline
2. **Tracker CLI** (`make status`, `make search`, etc.) — manages the job search pipeline

All commands are run from the repo root. The `Makefile` wraps common commands for convenience; the full `tracker_cli.py` syntax is shown below each shortcut.

---

## Pipeline CLI

```bash
make cli
# equivalent: uv run -m jobpostprofiler.main
```

Runs the full extraction pipeline on the example posting hardcoded in `main.py`. Useful for verifying that your provider config works.

For real use, prefer the Streamlit UI:

```bash
make run
# equivalent: uv run streamlit run src/jobpostprofiler/ui/app.py
```

---

## Tracker CLI

The tracker CLI manages jobs stored in `jobs.db` (SQLite, auto-created at repo root on first use).

### `status` — View the pipeline

Show all tracked jobs with status counts.

```bash
make status
# equivalent: uv run python tracker_cli.py status
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
uv run python tracker_cli.py status --status applied
```

Valid statuses: `found`, `applied`, `phone_screen`, `technical`, `offer`, `rejected`, `ghosted`.

---

### `show` — Job detail view

Display all stored fields for a single job, including skills, match score breakdown, QA status, and a preview of the JD text.

```bash
make show id=5
# equivalent: uv run python tracker_cli.py show 5
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
make show-full id=5
# equivalent: uv run python tracker_cli.py show 5 --full
```

---

### `search` — Find jobs by keyword

Search across title, company, notes, required skills, and preferred skills. Case-insensitive.

```bash
make search q=Python
# equivalent: uv run python tracker_cli.py search Python
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

Multi-word queries:

```bash
make search q="Acme Corp"
uv run python tracker_cli.py search "async culture"    # searches notes too
```

---

### `apply` — Log an application

Record that you applied for a job. Automatically sets status to `applied` and creates a follow-up reminder.

```bash
make apply id=5 resume=ML
# equivalent: uv run python tracker_cli.py apply 5 --resume ML
```

```
[tracker] Applied → job_id=5  resume=ML  follow_up=2026-04-06
  ✓ Logged application for: Acme Corp | ML Engineer
```

Full options (use the direct command for flags beyond id and resume):

```bash
uv run python tracker_cli.py apply 5 --resume SWE --cover "Referred by Jane" --followup-days 10 --notes "Strong match"
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
uv run python tracker_cli.py update 5 --status phone_screen
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
uv run python tracker_cli.py notes 5 "Great team, fully async, strong ML infra"
```

```
  ✓ Notes updated for job_id=5
```

---

### `edit` — Edit fields on a job record

Update individual fields without rerunning the pipeline.

```bash
uv run python tracker_cli.py edit 5 --company "Acme AI" --status applied --channel wellfound
```

```
  ✓ Updated job_id=5:
    company → Acme AI
    status → applied
    source_channel → wellfound
```

Editable fields: `--title`, `--company`, `--location`, `--remote-policy`, `--employment-type`, `--salary`, `--status`, `--notes`, `--channel`.

Valid channels: `wellfound`, `yc`, `linkedin`, `direct`, `other`.

---

### `followup` — Check what needs attention

Show applications whose follow-up date has arrived. Only shows jobs still in `applied` status.

```bash
make followup
# equivalent: uv run python tracker_cli.py followup
```

```
======================================================================
  FOLLOW-UPS DUE  —  2026-04-06
======================================================================
  [  5] Acme Corp                 ML Engineer                     due:2026-04-06
  [  3] Delta Corp                Senior SWE                      due:2026-04-04
======================================================================
  Tip: uv run python tracker_cli.py update <id> --status phone_screen
```

If nothing is due:

```
  ✓ No follow-ups due today.
```

---

### `export` — Generate Markdown report

Produce a Markdown summary of the full pipeline. Useful for pasting into a Claude Project or sharing with a mentor.

```bash
make export
# equivalent: uv run python tracker_cli.py export
```

Write to file:

```bash
uv run python tracker_cli.py export --out weekly_report.md
```

Output includes status count table, all jobs with ID, status, company, title, date found, source channel, and resume used, plus a follow-ups due section (if any).

---

### `export-job` — Export a job's artifacts to files

Reconstruct the pipeline output files from the database for a single job.

```bash
make export-job id=5
# equivalent: uv run python tracker_cli.py export-job 5
```

```
  ✓ Exported job_id=5 → export/5/
```

Creates a directory with: `normalized_job_post.txt`, `job_extract.json`, `job_summary.md`, `quality_report.json`, `posting_kind.json`.

Custom destination:

```bash
uv run python tracker_cli.py export-job 5 --dest ./my-exports/acme/
```

---

### `delete` — Remove a job record

Delete a job and its associated applications. Prompts for confirmation by default.

```bash
uv run python tracker_cli.py delete 5
```

```
  Delete [5] Acme Corp | ML Engineer? (y/N): y
  ✓ Deleted job_id=5  (Acme Corp | ML Engineer)
```

Skip confirmation:

```bash
uv run python tracker_cli.py delete 5 -y
```

---

### `rescore` — Recompute all match scores

Update `match_score` for every job in the database using the current `my_skills.json`. Safe to run multiple times. Jobs with no skills data are skipped. Only touches the `match_score` column.

```bash
make rescore
# equivalent: uv run python tracker_cli.py rescore
```

```
  ✓ Re-scored  : 12 job(s)
  — Skipped    : 2 job(s) (no skills data)
```

Run this after updating `my_skills.json` to refresh scores across all tracked jobs.

---

## Skill Match Scoring

When `my_skills.json` exists at repo root, the pipeline computes a match score for every extraction. No LLM calls — pure Python set intersection with alias normalization on already-extracted skills.

### Setup

```bash
cp my_skills.example.json my_skills.json
```

Edit `my_skills.json`:

```json
{
  "skills": ["Python", "SQL", "PyTorch", "Docker", "AWS", "FastAPI", "pandas"],
  "soft_skills": ["cross-functional collaboration", "technical documentation", "stakeholder communication"],
  "bridgeable": ["MLflow", "LangGraph", "PostgreSQL", "Kubernetes"]
}
```

- **`skills`** — your technical skills, matched against `skills.required[]` and `skills.preferred[]`
- **`soft_skills`** — behavioral/interpersonal skills, matched against `soft_skills[]`
- **`bridgeable`** — skills you don't have yet but could learn quickly; shown as "bridgeable ⚡" in the UI gap breakdown (does not affect the numeric score)

### How scoring works

| Component | Weight | Formula |
|---|---|---|
| Required skills | 65% | (matched required) / (total required) |
| Preferred skills | 25% | (matched preferred) / (total preferred) |
| Soft skills | 10% | (matched soft skills) / (total soft skills) |

```
overall_score = (required_pct × 0.65) + (preferred_pct × 0.25) + (soft_pct × 0.10)
```

- Matching is case-insensitive with alias normalization (e.g., "pytorch" / "torch" → same canonical form) and substring fuzzy fallback for tokens ≥3 characters
- If a job has no required skills, `required_pct` defaults to 1.0 (no penalty)
- If a job has no preferred skills, `preferred_pct` defaults to 1.0
- If a job has no soft skills, `soft_pct` defaults to 1.0
- Score is stored in `jobs.match_score` and shown in `status`, `show`, and the Streamlit Tracker tab

### Where scores appear

- **`status`** — appended to each row as `Match:85%`
- **`show <id>`** — full breakdown showing matched/missing skills per category
- **Streamlit UI** — Extractor tab shows score card after extraction; Tracker tab shows score column in the jobs table
- **`rescore`** — bulk-updates all scores when your profile changes

---

## Make Shortcuts Reference

| Shortcut | Equivalent |
|---|---|
| `make run` | `uv run streamlit run src/jobpostprofiler/ui/app.py` |
| `make cli` | `uv run -m jobpostprofiler.main` |
| `make test` | `uv run python -m pytest -v` |
| `make status` | `uv run python tracker_cli.py status` |
| `make search q="..."` | `uv run python tracker_cli.py search "..."` |
| `make show id=N` | `uv run python tracker_cli.py show N` |
| `make show-full id=N` | `uv run python tracker_cli.py show N --full` |
| `make apply id=N resume=ML` | `uv run python tracker_cli.py apply N --resume ML` |
| `make followup` | `uv run python tracker_cli.py followup` |
| `make export` | `uv run python tracker_cli.py export` |
| `make export-job id=N` | `uv run python tracker_cli.py export-job N` |
| `make rescore` | `uv run python tracker_cli.py rescore` |

For commands with additional flags (`update`, `notes`, `edit`, `delete`), use the full `uv run python tracker_cli.py` syntax.

---

## Duplicate URL Detection

The pipeline checks `jobs.db` for an existing row with the same URL before making LLM calls. If a duplicate is found:

- **Pipeline**: raises `ValueError` with the existing job ID
- **Streamlit UI**: shows the error; use the "Force re-process" checkbox to override
- **CLI/direct calls**: pass `force=True` to `run_pipeline()` to override

This prevents wasted LLM calls when re-processing the same posting.