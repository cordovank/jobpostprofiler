# JobPostProfiler

> **Job posting extraction pipeline.** Give it a URL, paste text, or point it at a file — get back structured JSON, a clean Markdown summary, and a QA audit. Two LLM calls. Everything else is deterministic Python.

---

## Why This Exists

Sourcing and tracking job postings is manual, inconsistent work. Every platform formats postings differently — some as structured HTML, others as flat text, others behind JavaScript walls. Extracting and comparing postings at scale requires more than copy-paste: you need normalized data you can query, filter, and audit.

**JobPostProfiler** solves this by turning any job posting into a validated, schema-governed JSON document with a human-readable Markdown summary — automatically, with transparent quality checks.

The project is also a demonstration of **responsible agentic system design**: the LLM is used precisely where it adds value (structured field extraction and quality auditing), while every other step — fetching, normalizing, classifying, rendering — is pure Python with deterministic, testable behavior.

---

## What It Does (End-to-End)

```
Input (URL / pasted text / file)
       │
       ▼
[1] Fetch + Normalize          ← pure Python (requests, BeautifulSoup, Selenium fallback)
       │
       ▼
[2] Classify Posting Kind      ← pure Python heuristic (employment vs. freelance)
       │
       ▼
[3] Extract Structured Fields  ← LLM call #1 → validated PostingExtract (Pydantic)
       │
       ▼
[4] Render Markdown Summary    ← pure Python (Jinja2 templates, no LLM)
       │
       ▼
[5] QA Audit                   ← LLM call #2 → QAReport (Pydantic)
       │
       ▼
Output: normalized_job_post.txt, posting_kind.json,
        job_extract.json, job_summary.md, quality_report.json
```

Each step has a single, clearly bounded responsibility. The LLM sees clean, normalized input. The LLM produces schema-validated output. All rendering and classification are done by Python — not prompted out of a model.

---

## Architecture

### Design Principles

**Separation of concerns — LLM touches only what Python can't.**
Fetching, deduplication, JS-shell detection, posting classification, and Markdown rendering are all Python. The LLM handles the two tasks that genuinely require language understanding: field extraction from unstructured text, and quality auditing of its own output.

**Schema-first extraction.**
`PostingExtract` is a Pydantic model with `extra="forbid"`. The LLM is given the schema and instructed to produce only schema-valid JSON. The extractor rejects and retries on parse failures, not silently accepts malformed output.

**Evidence-gated extraction — no guessing.**
Prompts are written to require explicit textual evidence for every field. Missing data becomes `null` plus a warning, not an inference. A posting with all-null company fields and no warnings is flagged as an automatic extraction failure.

**Deterministic rendering.**
Markdown output is rendered by Jinja2 from the validated `PostingExtract`. There is no LLM call in the rendering step. The templates are versioned and testable.

**QA as a first-class gate, not an afterthought.**
A second LLM call audits the extraction against the original text, checking for hallucinated fields, missing sections without warnings, and schema violations.

---

### Module Map

```
src/jobpostprofiler/
│
├── core/                  # Pure Python — no LLM, fully testable
│   ├── fetcher.py         # fetch_and_normalize(): HTTP scrape, Selenium fallback, normalization
│   ├── classifier.py      # classify_kind(): signal-based heuristic → "employment" | "freelance"
│   └── renderer.py        # render_markdown(): Jinja2 templates from PostingExtract
│
├── llm/                   # All LLM-touching code, isolated here
│   ├── client.py          # get_client(), structured_call(), plain_call()
│   └── prompts.py         # EXTRACTOR_SYSTEM, QA_SYSTEM, user message templates
│
├── models/                # Pydantic schemas — source of truth for data contracts
│   ├── job_models.py      # PostingExtract, EmploymentDetails, FreelanceDetails, Source, Skills
│   └── qa_models.py       # QAReport
│
├── ui/
│   ├── app.py             # Streamlit entry point
│   └── ui_components.py   # render_header(), render_input_panel(), render_outputs()
│
├── pipeline.py            # run_pipeline() — orchestrates all steps
├── config.py              # AppConfig: provider selection, env vars, validation
└── main.py                # CLI entry point for local testing
```

**Key design invariant:** `core/` has zero LLM dependencies. `llm/` has zero business logic. `models/` has zero I/O. These boundaries are enforced by import structure and testable in isolation.

---

### Data Models

**PostingExtract** (top-level envelope)
```
PostingExtract
├── source: Source                   # extraction metadata (url, timestamp, input_type)
├── details: EmploymentDetails       # discriminated union on details.kind
│       OR  FreelanceDetails
├── responsibilities: List[str]
├── requirements: List[str]
├── preferred_qualifications: List[str]
├── benefits: List[str]
├── skills: Skills                   # required: List[str], preferred: List[str]
└── warnings: List[str]              # extraction warnings — single source of truth
```

`details.kind` is the discriminator. It is set from the classifier output and the LLM is forbidden to override it. Warnings are **only** in the top-level `warnings` list — the model validator auto-promotes any warnings accidentally placed inside `details`.

**QAReport**
```
QAReport
├── passed: bool
├── issues: List[str]
└── missing_fields: List[str]
```

---

### Fetch + Normalize

`fetcher.py` implements a deterministic routing strategy:

1. Pasted text → use directly
2. Local file → `FileReadTool` / `Path.read_text`
3. URL →
   a. Plain HTTP scrape (requests + BeautifulSoup)
   b. JS-shell detection: content too short (<1500 chars), `__next`, `id="root"`, `id="app"`, or JavaScript-required message
   c. If JS signals fire → Selenium headless fallback; prefer Selenium output only if longer AND contains job-like headings (Responsibilities, Qualifications, etc.)

Normalization (always applied after fetch):
- Strip boilerplate (cookie banners, nav menus, privacy policy, copyright footers)
- Deduplicate repeated lines (case-insensitive)
- Collapse multiple blank lines
- Preserve headings and bullet structure
- No summarization — content is cleaned, not compressed

---

### Classifier

`classifier.py` is a pure signal-counting heuristic. It scans normalized text for freelance signals (Upwork, Fiverr, fixed-price, proposals, payment verified, etc.) and employment signals (salary, benefits, apply now, department, ATS platform names, etc.). Employment is the default when signals are ambiguous.

No LLM. No model calls. Fully testable with example strings.

---

### LLM Client

`client.py` provides two call types:

- `structured_call()` — sends schema as reference, requests JSON-only response, validates with Pydantic, strips markdown fences, extracts the last JSON object if the model prepends schema echo. Raises `ValueError` with raw output on validation failure.
- `plain_call()` — raw string output, used for QA and optional markdown writing.

The client is injectable for testing — `run_pipeline()` accepts a `client` argument, making it straightforward to mock LLM calls in integration tests.

---

### Provider Configuration

Three providers supported via `.env`:

| Provider | `SELECTED_PROVIDER` | Required vars |
|---|---|---|
| Ollama (local) | `OLLAMA` | `OLLAMA_MODEL` |
| OpenRouter | `OPENROUTER` | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` |
| OpenAI | `OPENAI` | `OPENAI_API_KEY`, `OPENAI_MODEL` |

All providers use the OpenAI-compatible chat completions interface. Switching providers requires only `.env` changes.

---

## Project Layout

```
JobPostProfiler/
│
├── src/
│   └── jobpostprofiler/
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── fetcher.py
│       │   ├── classifier.py
│       │   └── renderer.py
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── prompts.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── job_models.py
│       │   └── qa_models.py
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   └── ui_components.py
│       │
│       ├── pipeline.py
│       ├── config.py
│       └── main.py
│
├── tests/
│   ├── unit/
│   │   ├── test_fetcher.py          # normalize logic, JS-shell detection, boilerplate stripping
│   │   ├── test_classifier.py       # signal scoring, edge cases
│   │   └── test_renderer.py         # template output correctness, null handling
│   ├── integration/
│   │   ├── test_pipeline.py         # full run with mock LLM client
│   │   └── fixtures/
│   │       ├── sample_employment.txt
│   │       └── sample_freelance.txt
│   └── conftest.py
│
├── output/                          # gitignored — runtime artifacts per run
│   └── {run_id}/
│       ├── normalized_job_post.txt
│       ├── posting_kind.json
│       ├── job_extract.json
│       ├── job_summary.md
│       └── quality_report.json
│
├── .env                             # gitignored
├── .env.example
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Outputs

Each run writes to `output/{run_id}/`:

| File | Description |
|---|---|
| `normalized_job_post.txt` | Cleaned, deduplicated posting text |
| `posting_kind.json` | `{"kind": "employment" \| "freelance", "warnings": []}` |
| `job_extract.json` | Full `PostingExtract` as JSON |
| `job_summary.md` | Human-readable Markdown summary |
| `quality_report.json` | `QAReport`: pass/fail, issues, missing fields |

---

## Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- A running LLM (Ollama locally, or API key for OpenRouter/OpenAI)

### Setup

```bash
git clone <repo>
cd JobPostProfiler

cp .env.example .env
# Edit .env — set SELECTED_PROVIDER and the corresponding model/key vars

uv sync
```

### Option A — Streamlit UI

```bash
uv run streamlit run src/jobpostprofiler/ui/app.py
```

Paste a job URL or the full posting text, click **Run extraction**, and view:
- Rendered Markdown summary
- Full structured JSON (`job_extract.json`)
- QA report (`quality_report.json`)

### Option B — CLI

```bash
python -m jobpostprofiler.main
```

Uses the example posting in `main.py`. Useful for quick local testing and verifying model output.

### Tests

```bash
pytest
```

Unit tests cover `core/` (no LLM required). Integration tests use a mock client and fixture postings.

---

## Environment Variables

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

# Output directory (default: output/)
OUTPUT_DIR=output
```

---

## Engineering Notes

### What uses the LLM (and why)

| Step | LLM? | Reason |
|---|---|---|
| Fetch + normalize | No | Deterministic text cleanup |
| JS-shell detection | No | Signal pattern matching |
| Classify kind | No | Signal counting heuristic |
| Extract fields | **Yes** | Unstructured → structured; requires language understanding |
| Render markdown | No | Jinja2 from validated JSON |
| QA audit | **Yes** | Requires reading comprehension to detect hallucination |

### Failure handling

- **Pydantic `extra="forbid"`** rejects any LLM output with undeclared keys. The extractor logs the raw output and raises on failure.
- **`model_validator(mode="before")`** in `PostingExtract` auto-repairs common LLM output mistakes (null lists coerced to `[]`, warnings leaked into `details` auto-promoted to top-level).
- **`_extract_last_json_object()`** handles models that echo the schema before the extraction JSON.
- **JS-shell fallback** in `fetcher.py` handles JavaScript-rendered pages without requiring the caller to know about rendering strategies.
- **QA auto-fail conditions** catch the most common extraction failure: all-null `company` or `role` fields with no corresponding warnings — which indicates the model didn't read the file, not that the data was missing.

### Testability

- `core/` modules have no LLM dependencies and are unit-testable with plain strings.
- `run_pipeline()` accepts an injectable `client` argument for full integration testing without real LLM calls.
- `PostingExtract.model_validate()` can be called directly in tests to verify schema compliance of any JSON fixture.

### Extending the pipeline

To add a new posting kind (e.g., `internship`):
1. Add a new `InternshipDetails` model in `job_models.py`
2. Update the `PostingDetails` union and discriminator
3. Add signals to `classifier.py`
4. Add a Jinja2 template in `renderer.py`
5. Update extraction prompts if needed

To swap the LLM:
- Change `.env` only. No code changes required for supported providers.

---

## Known Limitations

- **JavaScript-heavy pages** may still fail if Selenium is not available or the page requires authentication.
- **Classifier accuracy** degrades on ambiguous postings (e.g., a contract role on a traditional job board). The LLM extraction step is unaffected since kind is passed explicitly.
- **LLM output quality** varies by model. Smaller models may hallucinate fields or miss structured extraction. The QA step catches these but does not auto-correct them.
- **Rate limits and costs** apply to hosted providers. The pipeline makes exactly 2 LLM calls per run regardless of input length.