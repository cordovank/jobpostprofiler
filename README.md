# JobPostProfiler

> Extract · Evaluate · Track

Give it a job posting URL, paste raw text, or point it at a file — get back structured JSON, a Markdown summary, a QA audit report, and a skill match score. Two LLM calls. Everything else is deterministic Python.

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- An LLM provider: Ollama (local), OpenRouter, or OpenAI

### Install

```bash
git clone https://github.com/cordovank/JobPostProfiler.git
cd JobPostProfiler

cp .env.example .env
# Edit .env — set SELECTED_PROVIDER and the corresponding model/key vars

uv sync
```

### Run — Streamlit UI

```bash
uv run streamlit run src/jobpostprofiler/ui/app.py
```

Paste a URL or full posting text, click **Analyze**, and view the extraction summary, structured JSON, QA report, and skill match score.

### Run — CLI

```bash
uv run -m jobpostprofiler.main
```

Runs the pipeline against the built-in example posting. Useful for verifying model output.

### Run — Tests

```bash
uv run python -m pytest -v 2>&1
```

Unit tests cover all `core/` modules (no LLM required). Integration tests use a mock client.

---

## What It Produces

Each extraction generates:

| Artifact | Description |
|---|---|
| Structured JSON | `PostingExtract` — validated Pydantic model with role, company, skills, requirements, benefits |
| Markdown summary | Human-readable rendering via Jinja2 templates (no LLM) |
| QA report | Pass/fail audit: hallucination check, missing field detection, qualifier violations |
| Skill match score | Weighted coverage against your `my_skills.json` profile (no LLM) |

All artifacts are automatically saved to a local SQLite tracker (`jobs.db`).

---

## Skill Match Scoring

```bash
cp my_skills.example.json my_skills.json
# Edit with your skills, soft skills, and bridgeable skills
```

The pipeline scores every extraction against your profile using alias-aware set intersection — zero LLM calls. Scores appear in the Streamlit Tracker tab and CLI output. Weights: 65% required, 25% preferred, 10% soft skills.

---

## Job Tracker

Every extraction auto-saves to `jobs.db`. Manage your pipeline via CLI or the Streamlit Tracker tab.

**Status flow:** `found → applied → phone_screen → technical → offer | rejected | ghosted`

### CLI Quick Reference

```bash
# View pipeline
python tracker_cli.py status

# Search jobs
python tracker_cli.py search "ML engineer"

# Log an application
python tracker_cli.py apply 3 --resume ML

# Check follow-ups due today
python tracker_cli.py followup

# Export job artifacts to files
python tracker_cli.py export-job 3

# Rescore all jobs with updated my_skills.json
python tracker_cli.py rescore
```

See [docs/cli.md](docs/cli.md) for the full reference.

---

## Provider Configuration

All providers use the OpenAI-compatible chat completions interface. Switching requires only `.env` changes.

```env
# Provider selection: OLLAMA | OPENROUTER | OPENAI
SELECTED_PROVIDER=OLLAMA

# Ollama (local)
OLLAMA_MODEL=qwen2.5:14b

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=mistralai/mistral-7b-instruct

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## Three Posting Types

The pipeline handles employment, freelance, and internship postings with dedicated Pydantic models, classifier signals, and Jinja2 templates for each. Posting kind is determined by a deterministic heuristic before the LLM sees the text.

---

## Architecture at a Glance

```
Input (URL / text / file)
       │
       ▼
[1] Fetch + Normalize          ← Python (requests, BS4, Selenium fallback, Workday API)
       │
       ▼
[2] Classify Posting Kind      ← Python heuristic (signal counting)
       │
       ▼
[3] Extract Structured Fields  ← LLM call #1 → PostingExtract (Pydantic, extra="forbid")
       │
       ▼
[4] Render Markdown            ← Python (Jinja2 templates)
       │
       ▼
[5] QA Audit                   ← LLM call #2 → QAReport (Pydantic)
       │
       ▼
[6] Skill Match                ← Python (alias-aware set intersection)
       │
       ▼
[7] Save to Tracker            ← SQLite (jobs.db)
```

For the full technical deep-dive, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Tech Stack

Python · Pydantic · OpenAI-compatible API · Streamlit · Jinja2 · SQLite · BeautifulSoup · Selenium (optional) · uv

---

## Known Limitations

- JavaScript-heavy pages may fail if Selenium is unavailable or the page requires authentication. Workaround: paste the text directly.
- LLM output quality varies by model — smaller models may hallucinate fields. The QA step catches these but does not auto-correct.
- Exactly 2 LLM calls per run regardless of input length.
- Duplicate detection is URL-based; pasted-text duplicates are not caught.

---

## License

MIT