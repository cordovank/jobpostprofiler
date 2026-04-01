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
    st.title("Profiler")
    st.html('<p class="profiler-subtitle">Extract · Evaluate · Track</p>')


def render_input_panel() -> UIInput:
    # Segmented mode toggle
    mode = st.radio(
        "Input type",
        options=["URL", "Paste text"],
        horizontal=True,
        label_visibility="collapsed",
    )
    mode_key = "url" if mode == "URL" else "text"

    url = ""
    text = ""

    if mode_key == "url":
        url = st.text_input(
            "Job posting URL",
            placeholder="https://wellfound.com/...",
            label_visibility="collapsed",
        )
    else:
        text = st.text_area(
            "Job posting text",
            height=200,
            placeholder="Paste the full job posting here…",
            label_visibility="collapsed",
        )

    return UIInput(mode=mode_key, url=url.strip(), text=text.strip())


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
    if not extract_json:
        st.info("No extraction yet. Paste a job posting and click Analyze.")
        return

    details = extract_json.get("details", {})
    role     = details.get("role", {}) if isinstance(details, dict) else {}
    company  = details.get("company", {}) if isinstance(details, dict) else {}
    skills   = extract_json.get("skills", {})

    title    = role.get("job_title") or extract_json.get("title") or "Unknown role"
    co_name  = company.get("name") or "Unknown company"
    location = role.get("location") or "Location not stated"
    emp_type = role.get("employment_type") or ""
    comp     = role.get("compensation") or ""

    meta_parts = [p for p in [co_name, location, emp_type, comp] if p]
    meta_str   = "  ·  ".join(meta_parts)

    # Job header
    st.html(f"""
    <p class="job-header-title">{title}</p>
    <p class="job-header-meta">{meta_str}</p>
    """)

    # Required skills pills
    req_skills = skills.get("required", []) if isinstance(skills, dict) else []
    if req_skills:
        st.html('<p class="section-label">Required skills</p>')
        pills_html = "".join(
            f'<span class="skill-pill">{s}</span>' for s in req_skills
        )
        st.html(f'<div class="skill-pill-row">{pills_html}</div>')

    # Expandable sections
    responsibilities = extract_json.get("responsibilities", [])
    requirements     = extract_json.get("requirements", [])
    preferred        = extract_json.get("preferred_qualifications", [])
    pref_skills      = skills.get("preferred", []) if isinstance(skills, dict) else []

    with st.expander(f"Responsibilities  ({len(responsibilities)})", expanded=False):
        if responsibilities:
            for item in responsibilities:
                st.markdown(f"- {item}")
        else:
            st.caption("None extracted.")

    with st.expander(f"Requirements  ({len(requirements)})", expanded=False):
        if requirements:
            for item in requirements:
                st.markdown(f"- {item}")
        else:
            st.caption("None extracted.")

    with st.expander(f"Preferred  ({len(preferred) + len(pref_skills)})", expanded=False):
        if preferred:
            for item in preferred:
                st.markdown(f"- {item}")
        if pref_skills:
            st.caption("Preferred skills: " + ", ".join(pref_skills))
        if not preferred and not pref_skills:
            st.caption("None extracted.")

    with st.expander("Extracted data", expanded=False):
        st.json(extract_json)
        if qa_json:
            st.divider()
            st.caption("QA report")
            st.json(qa_json)


def render_match_score(match_result, qa_json: Optional[Dict] = None) -> None:
    """Display skill match score strip with QA badge."""
    from jobpostprofiler.core.skill_match import MatchResult
    if not isinstance(match_result, MatchResult):
        return

    overall  = f"{match_result.overall_score:.0%}"
    req_pct  = f"{match_result.required_pct:.0%}"
    pref_pct = f"{match_result.preferred_pct:.0%}"

    qa_passed = qa_json.get("passed", True) if qa_json else True
    qa_label  = "Audit passed" if qa_passed else "Audit issues"
    qa_class  = "qa-badge qa-pass" if qa_passed else "qa-badge qa-fail"

    st.html(f"""
    <div class="match-strip">
        <div>
            <div class="match-primary">{overall}</div>
            <div class="match-label">Skill match</div>
        </div>
        <div class="match-stat">
            <div class="match-stat-num">{req_pct}</div>
            <div class="match-stat-label">required</div>
        </div>
        <div class="match-stat">
            <div class="match-stat-num">{pref_pct}</div>
            <div class="match-stat-label">preferred</div>
        </div>
        <span class="{qa_class}">{qa_label}</span>
    </div>
    """)

    # Bridgeable gap display — only rendered when annotation is present
    req_bridgeable  = getattr(match_result, "_req_bridgeable",  [])
    pref_bridgeable = getattr(match_result, "_pref_bridgeable", [])
    req_true_gap    = [s for s in match_result.required_missing
                       if s not in req_bridgeable]
    pref_true_gap   = [s for s in match_result.preferred_missing
                       if s not in pref_bridgeable]

    has_any_gap = (req_bridgeable or pref_bridgeable
                   or req_true_gap or pref_true_gap)

    if has_any_gap:
        with st.expander("Skill gap breakdown", expanded=False):
            if req_true_gap:
                st.caption("Required — not in profile")
                st.markdown(
                    "  ".join(f"`{s}`" for s in req_true_gap) or "—"
                )
            if req_bridgeable:
                st.caption("Required — bridgeable ⚡")
                st.markdown(
                    "  ".join(f"`{s}`" for s in req_bridgeable) or "—"
                )
            if pref_true_gap:
                st.caption("Preferred — not in profile")
                st.markdown(
                    "  ".join(f"`{s}`" for s in pref_true_gap) or "—"
                )
            if pref_bridgeable:
                st.caption("Preferred — bridgeable ⚡")
                st.markdown(
                    "  ".join(f"`{s}`" for s in pref_bridgeable) or "—"
                )


def render_tracker_tab() -> None:
    """Render the job tracker pipeline view."""
    from jobpostprofiler.db.store import (
        list_jobs, get_job, update_job, delete_job, VALID_STATUSES
    )
    from collections import Counter

    jobs = list_jobs()
    if not jobs:
        st.caption("No jobs tracked yet. Use the Extract tab to analyze a posting.")
        return

    # ── Status summary strip ──────────────────────────────────────────────
    _dark = st.session_state.get("dark_mode", False)

    _STATUS_COLORS = {
        "found":        "#6A6560" if _dark else "#9A9490",
        "applied":      "#5F9EC4" if _dark else "#3D6E9E",
        "phone_screen": "#C49040" if _dark else "#9E6E2A",
        "technical":    "#C49040" if _dark else "#9E6E2A",
        "offer":        "#6BBF8A" if _dark else "#2D6E4E",
        "rejected":     "#C07878" if _dark else "#8B3A3A",
        "ghosted":      "#6A6560" if _dark else "#9A9490",
    }
    counts = Counter(j["status"] for j in jobs)

    # Render in canonical pipeline order; show 0 for missing statuses
    pipeline_order = ["found", "applied", "phone_screen", "technical",
                      "offer", "rejected", "ghosted"]
    strip_items = ""
    for status in pipeline_order:
        count = counts.get(status, 0)
        label = status.replace("_", " ")
        color = _STATUS_COLORS.get(status, "")
        strip_items += f"""
        <div class="status-stat">
            <div class="status-stat-num" style="color:{color} !important;">{count}</div>
            <div class="status-stat-label">{label}</div>
        </div>"""
    st.html(f'<div class="status-strip">{strip_items}</div>')

    # ── Jobs table ────────────────────────────────────────────────────────
    import pandas as pd

    display_rows = []
    for j in jobs:
        status = j.get("status", "found")
        match = f"{j['match_score']:.0%}" if j.get("match_score") is not None else "—"
        display_rows.append({
            "Company":  j.get("company") or "—",
            "Role":     j.get("title") or "—",
            "Status":   status.replace("_", " "),
            "Match":    match,
            "Added":    j.get("date_found") or "—",
        })

    df = pd.DataFrame(display_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Row selector ──────────────────────────────────────────────────────
    job_options = {
        j["id"]: f"{j.get('company') or '?'}  —  {j.get('title') or '?'}"
        for j in jobs
    }
    st.html('<div style="margin-top:6px;"></div>')
    selected_id = st.selectbox(
        "Select a job to edit",
        options=list(job_options.keys()),
        format_func=lambda x: job_options[x],
        index=None,
        placeholder="Select a job to view or edit…",
        label_visibility="collapsed",
    )

    if not selected_id:
        return

    job = get_job(selected_id)
    if not job:
        return

    # ── Edit panel ────────────────────────────────────────────────────────
    st.html('<div style="margin-top:0.5rem;"></div>')

    statuses = sorted(VALID_STATUSES)
    channels = ["builtin", "dice", "direct", "hiringcafe", "indeed", "linkedin", "towardsaijobs", "upwork", "wellfound", "yc", "other"]

    with st.form(key=f"edit_{selected_id}"):
        col1, col2 = st.columns(2)
        with col1:
            new_title   = st.text_input("Role",     value=job.get("title") or "")
            new_company = st.text_input("Company",  value=job.get("company") or "")
            new_loc     = st.text_input("Location", value=job.get("location") or "")
            new_salary  = st.text_input("Salary",   value=job.get("salary_range") or "")
        with col2:
            curr_status_idx = statuses.index(job["status"]) if job["status"] in statuses else 0
            new_status  = st.selectbox("Status",  options=statuses, index=curr_status_idx)
            curr_ch_idx = channels.index(job.get("source_channel") or "other")
            new_channel = st.selectbox("Channel", options=channels, index=curr_ch_idx)
            new_remote  = st.text_input("Remote policy", value=job.get("remote_policy") or "")
            new_emp     = st.text_input("Employment type", value=job.get("employment_type") or "")

        new_notes = st.text_area("Notes", value=job.get("notes") or "", height=80)

        save_col, del_col = st.columns([3, 1])
        with save_col:
            saved = st.form_submit_button("Save changes")
        with del_col:
            deleted = st.form_submit_button(
                "Delete",
                type="secondary",
                help="Permanently delete this job record.",
            )

    if saved:
        fields: dict = {}
        mapping = [
            ("title",           new_title,   job.get("title") or ""),
            ("company",         new_company, job.get("company") or ""),
            ("location",        new_loc,     job.get("location") or ""),
            ("salary_range",    new_salary,  job.get("salary_range") or ""),
            ("status",          new_status,  job["status"]),
            ("source_channel",  new_channel, job.get("source_channel") or "other"),
            ("remote_policy",   new_remote,  job.get("remote_policy") or ""),
            ("employment_type", new_emp,     job.get("employment_type") or ""),
            ("notes",           new_notes,   job.get("notes") or ""),
        ]
        for key, new_val, old_val in mapping:
            if new_val != old_val:
                fields[key] = new_val
        if fields:
            update_job(selected_id, **fields)
            st.success(f"Updated: {', '.join(fields.keys())}")
            st.rerun()
        else:
            st.caption("No changes detected.")

    if deleted:
        delete_job(selected_id)
        st.caption(f"Deleted job #{selected_id}.")
        st.rerun()
