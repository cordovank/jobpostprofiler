# HireSignal — Architecture & Technical Reference

> Extended documentation for contributors and technical evaluation. For setup and usage, see [README.md](README.md).

---

## Table of Contents

1. [Why This Exists](#why-this-exists)
2. [Design Philosophy](#design-philosophy)
3. [Pipeline Walkthrough](#pipeline-walkthrough)
4. [Module Map](#module-map)
5. [Data Models](#data-models)
6. [Fetch + Normalize](#fetch--normalize)
7. [Posting Kind Classifier](#posting-kind-classifier)
8. [LLM Client](#llm-client)
9. [Extraction Prompts](#extraction-prompts)
10. [QA Audit](#qa-audit)
11. [Markdown Renderer](#markdown-renderer)
12. [Skill Match Scoring](#skill-match-scoring)
13. [Job Tracker (SQLite)](#job-tracker-sqlite)
14. [Tracker CLI](#tracker-cli)
15. [Streamlit UI](#streamlit-ui)
16. [Provider Configuration](#provider-configuration)
17. [Failure Handling](#failure-handling)
18. [Testability](#testability)
19. [Extending the Pipeline](#extending-the-pipeline)
20. [Known Limitations](#known-limitations)

---

## Why This Exists

Job postings are scattered across platforms, formatted inconsistently, and hidden behind JavaScript walls. Extracting, comparing, and tracking them at scale requires more than copy-paste — it requires normalized, queryable, auditable data.

**HireSignal** turns any job posting into a validated, schema-governed JSON document with a human-readable summary. The LLM is used precisely where it adds value (structured extraction and quality auditing). Every other step — fetching, normalizing, classifying, rendering, scoring — is pure Python with deterministic, testable behavior.

The project demonstrates **responsible agentic system design**: the LLM budget is capped at exactly two calls per posting, every LLM output is schema-validated before use, and a dedicated QA pass audits the extraction against the original text.

---

## Design Philosophy

**Separation of concerns — LLM touches only what Python can't.** Fetching, deduplication, JS-shell detection, posting classification, Markdown rendering, and skill matching are all deterministic Python. The LLM handles the two tasks that genuinely require language understanding: field extraction from unstructured text, and quality auditing of its own output.

**Schema-first extraction.** `PostingExtract` is a Pydantic model with `extra="forbid"`. The LLM is given the full JSON schema as reference and instructed to produce only schema-valid JSON. Parse failures trigger a retry with error feedback — the pipeline does not silently accept malformed output.

**Evidence-gated extraction — no guessing.** Prompts require explicit textual evidence for every field. Missing data becomes `null` plus a warning in the `warnings[]` array, not an inference. A posting with all-null company fields and no warnings is treated as an extraction failure.

**Deterministic rendering.** Markdown output is rendered by Jinja2 from the validated `PostingExtract`. There is no LLM call in the rendering step. Templates are versioned and testable.

**QA as a first-class gate.** A second LLM call audits the extraction against the original text, checking for hallucinated fields, missing sections without warnings, qualifier violations (required vs. preferred), compensation source mismatches, and ignored priority sections.

**Two LLM calls — no more.** The pipeline budget is fixed. All other intelligence is encoded in Python: classifiers, normalizers, renderers, matchers. This keeps costs predictable and behavior auditable.

---

## Pipeline Walkthrough

```
Input (URL / pasted text / local file)
       │
       ▼
[1] Fetch + Normalize            ← fetcher.py (requests, BS4, Selenium fallback, Workday API)
       │
       ├── Content quality guard  ← Raises FetchContentError if URL fetch is unusable
       ├── Duplicate check        ← Skips if URL already in jobs.db (unless force=True)
       │
       ▼
[2] Classify Posting Kind        ← classifier.py (signal-counting heuristic, no LLM)
       │                            Returns: "employment" | "freelance" | "internship"
       ▼
[3] Extract Structured Fields    ← LLM call #1
       │                            Input: normalized text + kind + Source metadata
       │                            Output: PostingExtract (Pydantic, extra="forbid")
       │                            Retry: once with validation error feedback on parse failure
       ▼
[4] Render Markdown              ← renderer.py (Jinja2 templates, no LLM)
       │                            Separate templates for employment, freelance, internship
       ▼
[5] QA Audit                     ← LLM call #2
       │                            Input: original text + extracted JSON
       │                            Output: QAReport (passed, issues, missing_fields)
       ▼
[6] Skill Match                  ← skill_match.py (alias-aware set intersection, no LLM)
       │                            Reads my_skills.json; computes weighted coverage score
       ▼
[7] Save to Tracker              ← store.py (SQLite, WAL mode)
       │                            Stores full extract JSON, QA report, markdown, match score
       ▼
Output: PipelineResult(extract, markdown, qa, run_id, job_id, match_result)
```

The pipeline is orchestrated by `run_pipeline()` in `pipeline.py`. It accepts a `cancel` callback for UI-driven cancellation, an `on_status` callback for progress updates, and a `client` argument for dependency injection in tests.

---

## Module Map

```
src/jobpostprofiler/
│
├── core/                   # Pure Python — zero LLM dependencies, fully testable
│   ├── fetcher.py          # fetch_and_normalize(): HTTP scrape, Selenium fallback,
│   │                       #   Workday API strategy, normalization, JS-shell detection
│   ├── classifier.py       # classify_kind(): signal-based heuristic
│   ├── renderer.py         # render_markdown(): Jinja2 templates per posting kind
│   └── skill_match.py      # compute_match(): alias-aware scoring with fuzzy fallback
│
├── llm/                    # All LLM-touching code, isolated
│   ├── client.py           # get_client(), structured_call(), plain_call()
│   └── prompts.py          # EXTRACTOR_SYSTEM, QA_SYSTEM, user message templates
│
├── models/                 # Pydantic schemas — source of truth for data contracts
│   ├── job_models.py       # PostingExtract, EmploymentDetails, FreelanceDetails,
│   │                       #   InternshipDetails, CompanyInfo, RoleDetails, Skills, Source
│   └── qa_models.py        # QAReport
│
├── db/
│   └── store.py            # SQLite persistence: save, list, search, update, delete,
│                           #   export, follow-up tracking, idempotent migrations
│
├── ui/
│   ├── app.py              # Streamlit entry point (Extract + Tracker tabs)
│   └── ui_components.py    # render_header(), render_input_panel(), render_outputs(),
│                           #   render_match_score(), render_tracker_tab()
│
├── pipeline.py             # run_pipeline() — orchestrates all steps
├── config.py               # AppConfig: provider routing, env vars, user profile cache
└── main.py                 # CLI entry point for local testing
```

**Key design invariant:** `core/` has zero LLM dependencies. `llm/` has zero business logic. `models/` has zero I/O. These boundaries are enforced by import structure and independently testable.

---

## Data Models

### PostingExtract (top-level envelope)

```
PostingExtract
├── source: Source                       # Extraction metadata
│   ├── extracted_at: str                # Human-readable date
│   ├── input_type: "url" | "text"
│   ├── url: Optional[str]
│   ├── file_path: Optional[str]
│   ├── source_platform: Optional[str]   # "linkedin", "wellfound", "greenhouse", etc.
│   └── ref: str (computed)              # url or file_path — derived, not set by LLM
│
├── details: PostingDetails              # Discriminated union on details.kind
│   ├── EmploymentDetails                # kind="employment" → company + role sub-objects
│   ├── FreelanceDetails                 # kind="freelance"  → flat gig/client fields
│   └── InternshipDetails               # kind="internship" → company + role + academic fields
│
├── responsibilities: List[str]          # Core duties, one per bullet
├── requirements: List[str]              # Full-sentence mandatory qualifications
├── preferred_qualifications: List[str]  # Full-sentence nice-to-haves
├── benefits: List[str]
├── skills: Skills
│   ├── required: List[str]              # Short 1–3 word labels for keyword matching
│   └── preferred: List[str]             # Qualifier-marked labels only
├── soft_skills: List[str]               # Behavioral/interpersonal competencies
├── warnings: List[str]                  # Missing fields, ambiguities, extraction notes
└── posting_kind: str (computed)         # Derived from details.kind
```

All models use `extra="forbid"` — the LLM cannot introduce unknown keys. A `model_validator(mode="before")` on `PostingExtract` handles common LLM output issues: coerces null lists to `[]`, strips computed fields the LLM may echo back (`posting_kind`, `ref`), and auto-promotes any warnings accidentally placed inside `details` to the top-level `warnings` array.

### PostingDetails Discriminated Union

The `details` field uses Pydantic's `Field(discriminator="kind")` pattern:

- **EmploymentDetails** — `kind="employment"`, nested `CompanyInfo` and `RoleDetails` sub-objects with fields for title, seniority, location, workplace type, compensation, visa sponsorship, and interview stages.
- **FreelanceDetails** — `kind="freelance"`, flat structure with platform, contract type, budget, hourly rate, duration, client info (spend, hire rate, payment verified), and screening questions.
- **InternshipDetails** — `kind="internship"`, inherits the employment shape plus internship-specific fields: duration, start/end dates, stipend, housing, relocation, academic level, GPA requirement, mentorship, and return offer potential.

### QAReport

```
QAReport
├── passed: bool             # True if extraction meets quality bar
├── issues: List[str]        # Identified problems
└── missing_fields: List[str] # Fields absent from extraction
```

---

## Fetch + Normalize

`fetcher.py` implements a multi-strategy acquisition pipeline:

### Input Routing

Exactly one of `url`, `text`, or `filepath` must be provided. The router delegates to the appropriate method and always applies normalization afterward.

### URL Fetch Strategy

1. **Platform-specific path (Workday):** Parses the Workday URL pattern, calls the Workday JSON API directly (`/wday/cxs/{company}/{site}/job/{path}`), and extracts structured fields (title, location, posted date, description HTML) without scraping. Falls through to generic strategy if the API call fails.

2. **Plain HTTP scrape:** `requests.get()` + BeautifulSoup. Strips `<script>`, `<style>`, `<noscript>`, `<header>`, `<footer>`, `<nav>` tags. Returns text content.

3. **JS-shell detection:** If scraped content is too short (<1,500 chars) or contains signals like `__next`, `id="root"`, `id="app"`, or "you need to enable javascript", the fetcher flags a JS-rendered page.

4. **Selenium fallback:** When JS signals fire, launches headless Chrome. Waits for content stabilization (body text length stable for 2+ consecutive seconds, max 10 seconds). Uses Selenium output only if it is substantially longer (≥3x) than the scrape output.

5. **Content quality guard:** After fetch, `check_content_quality()` raises `FetchContentError` if a URL fetch triggered JS signals but the resulting text has no job-like headings (responsibilities, qualifications, requirements, about). The error message includes a paste-text workaround.

### URL Extraction from Pasted Text

When input is pasted text, the fetcher scans for the first `http://` or `https://` URL and stores it in `FetchResult.url`. This enables source tracking and duplicate detection even for paste-mode inputs.

### Platform Inference

`_infer_platform()` maps URL domains to platform identifiers: adzuna, linkedin, wellfound, greenhouse, lever, ashby, yc, workday, smartrecruiters, icims. Used for source tracking and potential platform-specific rendering.

### Normalization

Applied to all inputs regardless of acquisition method:

- Strip boilerplate lines matching regex patterns (cookie banners, privacy policy, terms of service, navigation, copyright, sign in/up)
- Deduplicate repeated lines (case-insensitive)
- Collapse multiple consecutive blank lines into one
- Preserve headings and bullet structure
- No summarization — content is cleaned, not compressed

---

## Posting Kind Classifier

`classifier.py` is a pure signal-counting heuristic. No LLM, no model calls.

### Signal Sets

- **Freelance signals:** "upwork", "fiverr", "toptal", "freelancer.com", "fixed-price", "hourly contract", "proposals:", "invite sent", "payment verified", etc.
- **Internship signals:** "internship", "intern", "duration:", "graduating", "gpa", "stipend", "housing provided", "return offer", "student", "university", etc.
- **Employment signals:** "apply now", "full-time", "salary", "benefits", "equal opportunity employer", "department:", ATS platform domains (ashby, lever, greenhouse, workday), etc.

### Scoring

Counts matching signals per category. Priority order: freelance > internship > employment (default). Employment wins on ties or when signals are ambiguous.

The classifier output is passed to the LLM as context, not determined by it. This ensures the posting kind is always deterministic and testable.

---

## LLM Client

`client.py` provides a thin wrapper around any OpenAI-compatible API:

### `structured_call()`

The core extraction mechanism:

1. Appends the full Pydantic JSON schema to the system prompt as a reference block.
2. Instructs the model to respond with ONLY the filled JSON instance — no markdown fences, no commentary, no extra keys.
3. Strips markdown fences if the model adds them (`_clean_llm_json()`).
4. Extracts the last valid top-level JSON object using `json.JSONDecoder.raw_decode()` — handles models that echo the schema before the actual extraction.
5. Validates the parsed JSON against the Pydantic model.
6. On validation failure: retries once with the original request, the failed output, and the validation error as feedback.
7. On second failure: raises `ValueError` with both raw outputs for debugging.

Temperature is 0.0 by default — extraction is not a creative task.

### `plain_call()`

Raw string output for cases where structured validation is not needed. Used for QA markdown and any future non-schema tasks.

### Client Injection

`get_client()` returns a cached `OpenAI` instance keyed by `(base_url, api_key)`. `run_pipeline()` accepts an optional `client` argument, making the pipeline fully testable with mock LLM responses.

---

## Extraction Prompts

All prompts live in `prompts.py`, separated from call-site logic for independent iteration.

### Extractor System Prompt

The extraction prompt encodes 11 explicit rules:

1. **Read the full posting first** before extracting anything.
2. **Extract header fields first** — title, company, location, compensation appear as label-value pairs near the top.
3. **Priority/highlight sections** (TOP Skills, Key Skills, Must Have) must be captured in `requirements[]` and `skills.required[]`.
4. **Evidence-gated extraction** — only populate fields with explicit textual support. Missing → null + warning.
5. **Copy exact wording** for string fields. No paraphrasing.
6. **Qualifier rule** — items with "preferably", "a plus", "nice to have", etc. go to `preferred_qualifications[]` and `skills.preferred[]`, never to required fields.
7. **Skills extraction scans the entire document** — not just a "Skills" section. Short 1–3 word labels only.
8. **Soft skills** go to `soft_skills[]`, never to `requirements[]` or `skills.*[]`.
9. **Compensation** — prefer employer-stated range over aggregator estimates.
10. **Preferred qualifications sections** are routed correctly.
11. **Internship-specific fields** are extracted when applicable.

### QA System Prompt

The QA auditor checks 8 specific conditions:

1. Hallucinated fields not supported by the original text.
2. Missing sections present in the posting but absent from the extraction without warnings.
3. Soft skills placed in `requirements[]` instead of `soft_skills[]`.
4. Empty `skills.required[]` when the posting lists technologies.
5. `requirements[]` items that belong in `preferred_qualifications[]` (qualifier blindness).
6. Qualifier-marked items in `requirements[]` or `skills.required[]` flagged as `qualifier_violation`.
7. Compensation source mismatch — aggregator estimate used when an employer-stated range exists.
8. Priority section technologies absent from `skills.required[]` flagged as `priority_section_ignored`.

---

## Markdown Renderer

`renderer.py` uses Jinja2 templates to produce human-readable summaries from validated `PostingExtract` data. Three templates exist:

- **Employment template:** At a Glance table, company description, required/preferred skills, responsibilities, requirements, preferred qualifications, soft skills, benefits, extraction notes, source footer.
- **Freelance template:** Gig details table, client info table, responsibilities, requirements, skills, screening questions.
- **Internship template:** At a Glance table with academic and internship-specific fields, company description, skills, responsibilities, requirements, academic requirements, benefits.

Null values render as "Not stated". Empty lists render as "Not stated" or are omitted. The renderer is fully deterministic — no LLM call.

---

## Skill Match Scoring

`skill_match.py` computes a weighted match score between a user's skill profile (`my_skills.json`) and a job posting's extracted skills. Zero LLM calls.

### Matching Strategy

1. **Alias normalization:** An extensive alias map resolves variations to canonical forms (e.g., "pytorch" / "torch" → "pytorch", "huggingface" / "hf transformers" / "transformers" → "hugging face", "k8s" / "kubernetes" → "kubernetes"). Over 150 aliases covering ML/AI, frameworks, infrastructure, databases, languages, evaluation tools, and dev tooling.

2. **Exact match:** After normalization, checks set membership.

3. **Fuzzy fallback:** If exact match fails, checks bidirectional substring containment between normalized forms. Minimum token length of 3 characters prevents false positives from short tokens like "r", "c", "go".

4. **Deduplication:** Skills are deduplicated through the alias map before scoring, preserving the first occurrence's original casing.

### Scoring

```
overall = (required_pct × 0.65) + (preferred_pct × 0.25) + (soft_pct × 0.10)
```

- `required_pct`: fraction of job's required skills matched
- `preferred_pct`: fraction of job's preferred skills matched
- `soft_pct`: fraction of job's soft skills matched
- When a category is empty, its percentage defaults to 1.0 (no penalty)

### Bridgeable Skills

The UI layer annotates missing skills as "bridgeable" when they appear in the user profile's `bridgeable[]` list. This is a display-only annotation — it does not affect the numeric score.

### `my_skills.json` Format

```json
{
  "skills": ["Python", "PyTorch", "FastAPI", "Docker", ...],
  "soft_skills": ["cross-functional collaboration", "technical documentation", ...],
  "bridgeable": ["MLflow", "LangGraph", "PostgreSQL", ...]
}
```

---

## Job Tracker (SQLite)

`store.py` provides a persistence layer backed by SQLite with WAL journaling.

### Schema

**`jobs` table:** Stores the full pipeline output per posting — `run_id`, URL, title, company, location, remote policy, employment type, salary range, required/preferred skills (JSON arrays), source channel, status, QA pass/fail, QA issues, match score, full JD text, full extract JSON, precomputed markdown, full QA JSON, notes, timestamps.

**`applications` table:** Tracks application events — linked to `jobs.id`, stores date applied, resume variant used (ML/SWE/custom), cover note, follow-up date, and notes.

Indexes on `status`, `company`, and `date_found`.

### Migrations

`_migrate()` runs idempotent `ALTER TABLE` statements on first connection to add columns introduced after the initial schema (`match_score`, `extract_json`, `markdown_rendered`, `qa_json`, `updated_at`).

### Key Operations

- **`save_job_from_extract()`** — Normalizes the discriminated union's nested structure into flat DB columns. Handles employment, freelance, and internship shapes.
- **`get_job_by_url()`** — Enables duplicate detection before LLM calls.
- **`update_job()`** — Editable fields are allowlisted; status changes are validated against the set of valid statuses.
- **`export_job()`** — Reconstructs file artifacts from DB columns: `normalized_job_post.txt`, `job_extract.json`, `job_summary.md`, `quality_report.json`, `posting_kind.json`.
- **`due_for_followup()`** — Joins `applications` and `jobs` to find follow-ups due today or overdue, filtered to `applied` status.

---

## Tracker CLI

`tracker_cli.py` provides a full command-line interface for managing the job search pipeline. A `Makefile` wraps common commands for convenience.

### Make Shortcuts

```bash
make status                     # view tracker board
make search q="ML engineer"     # search by keyword
make show id=3                  # job details
make show-full id=3             # job details + full JD text
make apply id=3 resume=ML       # log application (ML, SWE, or custom)
make followup                   # due follow-ups
make export                     # markdown report
make export-job id=3            # export job artifacts to files
make rescore                    # recompute all match scores
```

### Full Command Reference

| Command | Description |
|---|---|
| `status [--status <value>]` | View pipeline board with summary counts per status |
| `search <query>` | Keyword search across title, company, notes, and skills |
| `show <id> [--full]` | Full detail view for one job (skills breakdown, match score, JD preview) |
| `apply <id> --resume ML\|SWE\|custom` | Log an application, set follow-up date (default 7 days) |
| `update <id> --status <value>` | Move a job to a new status |
| `notes <id> "text"` | Add or replace notes on a job |
| `followup` | Show applications due for follow-up today |
| `export [--out file.md]` | Generate Markdown report of all tracked jobs |
| `export-job <id> [--dest dir/]` | Export a job's artifacts to files |
| `delete <id> [-y]` | Delete a job and its applications (with confirmation) |
| `edit <id> --title/--company/--status/...` | Edit individual fields on a job record |
| `rescore` | Recompute match scores for all jobs using current `my_skills.json` |

### Status Values

`found` · `applied` · `phone_screen` · `technical` · `offer` · `rejected` · `ghosted`

### Source Channels

`wellfound` · `yc` · `linkedin` · `direct` · `other`

---

## Streamlit UI

`app.py` provides a two-tab interface:

### Extract Tab

- Input mode toggle: URL or paste text
- Model override in sidebar (defaults to `.env` value)
- Analyze button runs the full pipeline with progress status updates
- Cancel button (threaded pipeline execution with cancel callback)
- Output rendering: job header, required skills pills, expandable sections (responsibilities, requirements, preferred, raw JSON + QA report), skill match score strip with QA badge, skill gap breakdown with bridgeable annotations
- Dark mode toggle in sidebar with comprehensive CSS injection for all Streamlit components

### Tracker Tab

- Status summary strip showing counts per pipeline stage
- Rescore-all button (recomputes match scores from current `my_skills.json`)
- Sortable dataframe with company, role, status, match score, channel, date, and link columns
- Job selector dropdown for viewing or editing individual jobs
- View/Edit toggle per job: view mode shows full extraction output; edit mode provides fields for status, notes, channel, and a delete action with confirmation

---

## Provider Configuration

Three providers supported via `.env`, all using the OpenAI-compatible chat completions interface:

| Provider | `SELECTED_PROVIDER` | Required Variables |
|---|---|---|
| Ollama (local) | `OLLAMA` | `OLLAMA_MODEL` |
| OpenRouter | `OPENROUTER` | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` |
| OpenAI | `OPENAI` | `OPENAI_API_KEY`, `OPENAI_MODEL` |

`AppConfig` is a frozen dataclass that routes provider selection at init time. `validate_config()` returns warnings for missing keys. Switching providers requires only `.env` changes — no code changes.

---

## Failure Handling

- **`extra="forbid"` on all Pydantic models** — rejects LLM output with undeclared keys.
- **`model_validator(mode="before")` on PostingExtract** — auto-repairs common LLM mistakes: null lists coerced to `[]`, computed fields stripped, warnings leaked into `details` promoted to top-level.
- **`_extract_last_json_object()` using `json.JSONDecoder.raw_decode()`** — correctly handles braces inside string values (unlike depth-counter approaches). Extracts the last valid top-level JSON object when models echo the schema before the extraction.
- **`_clean_llm_json()`** — strips markdown code fences even when the model adds them despite instructions.
- **Structured call retry** — on first parse/validation failure, retries once with the validation error as feedback.
- **JS-shell detection + Selenium fallback** — handles JavaScript-rendered pages without requiring the caller to know about rendering strategies.
- **`FetchContentError`** — raised when URL fetch yields unusable content. Distinguishes between HTTP errors and JS-rendering failures. Includes a paste-text workaround in the error message.
- **Content quality guard** — runs before LLM calls to avoid wasting cost on unextractable content.
- **Duplicate URL detection** — runs before LLM calls to avoid reprocessing.
- **Tracker failure isolation** — DB write failures are caught and logged but never break the pipeline.

---

## Testability

- **`core/` modules** have zero LLM dependencies and are unit-testable with plain strings and fixture files.
- **`run_pipeline()`** accepts an injectable `client` argument for full integration testing without real LLM calls.
- **`PostingExtract.model_validate()`** can be called directly in tests to verify schema compliance of any JSON fixture.
- **`compute_match()`** is pure function with no I/O — testable with any skill lists.
- **`classify_kind()`** is a pure function testable with example strings.
- **`render_markdown()`** takes a `PostingExtract` and returns a string — testable by asserting on template output.

---

## Extending the Pipeline

### Adding a New Posting Kind

1. Add a new details model in `job_models.py` (e.g., `ContractDetails`) with a `kind` literal.
2. Add the new model to the `PostingDetails` union.
3. Add signal patterns to `classifier.py`.
4. Add a Jinja2 template in `renderer.py`.
5. Handle the new `details.kind` in `store.py`'s `_extract_fields()`.
6. Update extraction prompts if needed.

### Swapping the LLM

Change `.env` only. No code changes required for supported providers. Any OpenAI-compatible endpoint works.

### Adding a New Provider

Add a new branch in `AppConfig.__post_init__()` that sets `URL`, `API_KEY`, and `MODEL_NAME` from the appropriate environment variables.

---

## Project Layout

```
HireSignal/
│
├── src/
│   └── jobpostprofiler/
│       ├── core/
│       │   ├── fetcher.py
│       │   ├── classifier.py
│       │   ├── renderer.py
│       │   └── skill_match.py
│       ├── llm/
│       │   ├── client.py
│       │   └── prompts.py
│       ├── models/
│       │   ├── job_models.py
│       │   └── qa_models.py
│       ├── db/
│       │   └── store.py
│       ├── ui/
│       │   ├── app.py
│       │   └── ui_components.py
│       ├── pipeline.py
│       ├── config.py
│       └── main.py
│
├── tests/
│   ├── unit/
│   │   ├── test_fetcher.py
│   │   ├── test_classifier.py
│   │   └── test_renderer.py
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   └── fixtures/
│   └── conftest.py
│
├── tracker_cli.py
├── Makefile
├── docs/
│   └── cli.md
├── my_skills.example.json
├── .env.example
├── .streamlit/config.toml
├── pyproject.toml
├── uv.lock
├── README.md
└── ARCHITECTURE.md
```

`jobs.db`, `my_skills.json`, `.env`, and `output/` are gitignored and local-only.

---

## Known Limitations

- **JavaScript-heavy pages** may fail if Selenium is not installed or the page requires authentication. The Workday API strategy bypasses this for Workday-hosted postings.
- **Classifier accuracy** degrades on ambiguous postings (e.g., a contract role on a traditional job board). The LLM extraction step is unaffected since kind is passed explicitly.
- **LLM output quality** varies by model. Smaller models may hallucinate fields or miss structured extraction. The QA step catches these but does not auto-correct.
- **Rate limits and costs** apply to hosted providers. The pipeline makes exactly 2 LLM calls per run regardless of input length.
- **Duplicate detection** is URL-based only. Identical postings pasted as text are not caught.
- **Skill match scoring** uses alias normalization and fuzzy substring matching, not semantic similarity. Conceptually equivalent skills with no alias entry (e.g., "data wrangling" vs. "data cleaning") will not match.