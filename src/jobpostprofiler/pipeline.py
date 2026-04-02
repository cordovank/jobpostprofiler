"""
PIPELINE — Two LLM calls:
  1. structured_call() → PostingExtract  (extraction)
  2. structured_call() → QAReport        (quality audit)

Everything else is deterministic Python:
  - fetch + normalize  (fetcher.py)
  - classify kind      (classifier.py)
  - render markdown    (renderer.py)
  - write output files (here)
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jobpostprofiler.config import AppConfig
from jobpostprofiler.core.fetcher import fetch_and_normalize, FetchResult, check_content_quality, FetchContentError
from jobpostprofiler.core.classifier import classify_kind
from jobpostprofiler.core.renderer import render_markdown
from jobpostprofiler.core.skill_match import compute_match, MatchResult
from jobpostprofiler.llm.client import get_client, structured_call
from jobpostprofiler.llm.prompts import EXTRACTOR_SYSTEM, EXTRACTOR_USER_TEMPLATE, QA_SYSTEM, QA_USER_TEMPLATE
from jobpostprofiler.models.job_models import PostingExtract, Source
from jobpostprofiler.models.qa_models import QAReport


@dataclass
class PipelineResult:
    extract: PostingExtract
    markdown: str
    qa: QAReport
    run_id: str
    job_id: int | None = None
    match_result: MatchResult | None = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run_pipeline(
    *,
    url: str = "",
    text: str = "",
    filepath: str = "",
    cfg: AppConfig | None = None,
    client=None,
    uid: str | None = None,
    force: bool = False,
) -> PipelineResult:
    """
    Full pipeline: fetch → classify → extract → render → qa → write.
    Returns PipelineResult with all artifacts.
    """
    cfg = cfg or AppConfig()
    run_id = uid or datetime.now().strftime("%Y%m%d_%H%M%S")

    client = client or get_client(base_url=cfg.URL, api_key=cfg.API_KEY)

    # ------------------------------------------------------------------
    # Step 1: Fetch + Normalize
    # ------------------------------------------------------------------
    fetch_result: FetchResult = fetch_and_normalize(url=url, text=text, filepath=filepath)

    # ------------------------------------------------------------------
    # Content quality guard (before LLM calls to avoid wasted cost)
    # ------------------------------------------------------------------
    check_content_quality(fetch_result)

    # ------------------------------------------------------------------
    # Duplicate check (before LLM calls to avoid wasted cost)
    # ------------------------------------------------------------------
    if not force and fetch_result.url:
        try:
            from jobpostprofiler.db.store import get_job_by_url
            existing = get_job_by_url(fetch_result.url)
            if existing:
                raise ValueError(
                    f"Duplicate: job_id={existing['id']} "
                    f"({existing.get('company') or 'Unknown'} | {existing.get('title') or 'Unknown'}) "
                    f"already has this URL. Pass force=True to re-process."
                )
        except ValueError:
            raise
        except Exception:
            pass  # DB access failure should not block the pipeline

    # ------------------------------------------------------------------
    # Step 2: Classify posting kind (pure Python heuristic)
    # ------------------------------------------------------------------
    kind = classify_kind(fetch_result.text)

    # ------------------------------------------------------------------
    # Step 3: Extract structured fields — LLM call #1
    # ------------------------------------------------------------------
    extracted_at = datetime.now().strftime("%d %b %Y").lstrip("0")
    source = Source(
        extracted_at=extracted_at,
        input_type=fetch_result.input_type if fetch_result.input_type in ("url", "text") else "text",
        url=fetch_result.url,
        file_path=fetch_result.file_path or f"db://jobs/{run_id}",
        source_platform=fetch_result.source_platform,
    )

    user_msg = EXTRACTOR_USER_TEMPLATE.format(
        kind=kind, 
        text=fetch_result.text
    )
    # Exclude computed field 'ref' so the LLM doesn't echo it back
    source_json = source.model_dump_json(indent=2, exclude={"ref"})
    user_msg += f"\n\nSource metadata:\n{source_json}"

    extract: PostingExtract = structured_call(
        client=client, 
        model=cfg.MODEL_NAME,
        system_prompt=EXTRACTOR_SYSTEM, 
        user_message=user_msg,
        output_type=PostingExtract, 
        temperature=0.0,
    )

    # ------------------------------------------------------------------
    # Step 4: Render markdown (pure Python / Jinja2)
    # ------------------------------------------------------------------
    markdown = render_markdown(extract)

    # ------------------------------------------------------------------
    # Step 5: QA audit — LLM call #2
    # ------------------------------------------------------------------
    qa_msg = QA_USER_TEMPLATE.format(
        text=fetch_result.text, 
        extract_json=extract.model_dump_json(indent=2)
    )
    
    qa: QAReport = structured_call(
        client=client, 
        model=cfg.MODEL_NAME,
        system_prompt=QA_SYSTEM, 
        user_message=qa_msg,
        output_type=QAReport, 
        temperature=0.0,
    )

    # ------------------------------------------------------------------
    # Step 6: Skill match (pure Python, no LLM call)
    # ------------------------------------------------------------------
    match_result: MatchResult | None = None
    skills_path = Path(__file__).resolve().parents[2] / "my_skills.json"
    if skills_path.exists():
        user_profile = json.loads(skills_path.read_text(encoding="utf-8"))
        user_skills  = user_profile.get("skills", [])
        bridgeable   = {s.lower().strip() for s in user_profile.get("bridgeable", [])}
        if user_skills:
            match_result = compute_match(
                user_skills=user_skills,
                required_skills=extract.skills.required,
                preferred_skills=extract.skills.preferred,
            )
            # Annotate which missing skills are bridgeable.
            # These are private attributes — not part of the MatchResult
            # dataclass contract — used only by the UI rendering layer.
            match_result._req_bridgeable  = [
                s for s in match_result.required_missing
                if s.lower().strip() in bridgeable
            ]
            match_result._pref_bridgeable = [
                s for s in match_result.preferred_missing
                if s.lower().strip() in bridgeable
            ]

    # ------------------------------------------------------------------
    # Step 7: Add tracker
    # ------------------------------------------------------------------
    job_id: int | None = None
    try:
        from jobpostprofiler.db.store import save_job_from_extract
        job_id = save_job_from_extract(
            extract=extract.model_dump(),
            qa_report=qa.model_dump(),
            run_id=run_id,
            normalized_text=fetch_result.text,
            source_channel=os.getenv("SOURCE_CHANNEL", "other"),
            match_score=match_result.overall_score if match_result else None,
            extract_json=extract.model_dump_json(indent=2),
            markdown_rendered=markdown,
            qa_json=qa.model_dump_json(indent=2),
        )
    except Exception as _tracker_err:
        # Tracker failure never breaks the pipeline
        print(f"[tracker] Warning: could not save to DB — {_tracker_err}")

    return PipelineResult(
        extract=extract,
        markdown=markdown,
        qa=qa,
        run_id=run_id,
        job_id=job_id,
        match_result=match_result,
    )


