'''
UI COMPONENTS
'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import json
from pathlib import Path
import streamlit as st


@dataclass
class UIInput:
    mode: str  # "url" or "text"
    url: str
    text: str


def render_header():
    st.title("💼 Job Post Profiler")
    st.caption("Paste a job URL or the job text → extract structured fields → render a markdown summary.")


def render_input_panel() -> UIInput:
    with st.container(border=True):
        st.subheader("Input")

        mode = st.radio(
            "Choose input type",
            options=["url", "text"],
            horizontal=True,
        )

        url = ""
        text = ""

        if mode == "url":
            url = st.text_input("Job posting URL", placeholder="https://...")
        else:
            text = st.text_area("Job posting text", height=240, placeholder="Paste the full job posting...")

        return UIInput(mode=mode, url=url.strip(), text=text.strip())


def validate_inputs(ui: UIInput) -> Tuple[bool, Optional[str]]:
    if ui.mode == "url":
        if not ui.url:
            return False, "Please provide a URL."
        if not (ui.url.startswith("http://") or ui.url.startswith("https://")):
            return False, "URL must start with http:// or https://"
    else:
        if not ui.text:
            return False, "Please paste the job posting text."
        if len(ui.text) < 200:
            return False, "That text looks too short to be a full job posting. Paste more content."
    return True, None


def read_text_file(path: Path) -> Optional[str]:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


def read_json_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def render_outputs(
    summary_md: Optional[str],
    extract_json: Optional[Dict[str, Any]],
    qa_json: Optional[Dict[str, Any]],
):
    st.subheader("Job Summary")
    if summary_md:
        st.markdown(summary_md)
    else:
        st.info("No summary found yet. Run an extraction to generate job_summary.md")

    with st.expander("Structured JSON (job_extract.json)", expanded=False):
        if extract_json is None:
            st.write("Not found.")
        else:
            st.json(extract_json)

    with st.expander("QA Report (quality_report.json)", expanded=False):
        if qa_json is None:
            st.write("Not found.")
        else:
            st.json(qa_json)


def render_match_score(match_result) -> None:
    """Display skill match score card after extraction."""
    from jobpostprofiler.core.skill_match import MatchResult
    if not isinstance(match_result, MatchResult):
        return

    st.subheader(f"Skill Match: {match_result.overall_score:.0%}")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Required Skills", f"{match_result.required_pct:.0%}")
        if match_result.required_matched:
            st.caption(f"Matched: {', '.join(match_result.required_matched)}")
        if match_result.required_missing:
            st.caption(f"Missing: {', '.join(match_result.required_missing)}")
    with col2:
        st.metric("Preferred Skills", f"{match_result.preferred_pct:.0%}")
        if match_result.preferred_matched:
            st.caption(f"Matched: {', '.join(match_result.preferred_matched)}")
        if match_result.preferred_missing:
            st.caption(f"Missing: {', '.join(match_result.preferred_missing)}")


def render_tracker_tab() -> None:
    """Render the job tracker pipeline view."""
    from jobpostprofiler.db.store import list_jobs, get_job

    jobs = list_jobs()
    if not jobs:
        st.info("No jobs tracked yet. Use the Extractor tab to process a posting.")
        return

    # Status summary metrics
    from collections import Counter
    counts = Counter(j["status"] for j in jobs)
    cols = st.columns(len(counts))
    for col, (status, count) in zip(cols, sorted(counts.items())):
        col.metric(status, count)

    # Jobs table
    display_cols = ["id", "status", "company", "title", "date_found",
                    "salary_range", "match_score", "source_channel"]
    rows = []
    for j in jobs:
        row = {c: j.get(c) for c in display_cols}
        if row.get("match_score") is not None:
            row["match_score"] = f"{row['match_score']:.0%}"
        else:
            row["match_score"] = "—"
        rows.append(row)

    st.dataframe(rows, width='stretch', hide_index=True)

    # Detail view
    job_options = {j["id"]: f"[{j['id']}] {j.get('company', '?')} — {j.get('title', '?')}" for j in jobs}
    selected_id = st.selectbox("View job details", options=list(job_options.keys()),
                               format_func=lambda x: job_options[x])
    if selected_id:
        job = get_job(selected_id)
        if job:
            st.json({k: v for k, v in job.items() if v is not None and k != "jd_text"})
