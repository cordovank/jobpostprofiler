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
    st.set_page_config(
        page_title="Job Post Extractor",
        page_icon="💼",
        layout="centered",
    )
    st.title("🧾 Job Post Extractor")
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
