"""
JOB POST PROFILER — Streamlit UI
Run: streamlit run src/jobpostprofiler/ui/app.py
"""
import streamlit as st
from uuid import uuid4
from pathlib import Path
from jobpostprofiler.config import AppConfig, validate_config
from jobpostprofiler.pipeline import run_pipeline, PipelineResult
from jobpostprofiler.ui.ui_components import (
    render_header,
    render_input_panel,
    validate_inputs,
    render_outputs,
    render_match_score,
    render_tracker_tab,
    UIInput,
)


_base_cfg = AppConfig()


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Profiler",
    page_icon=None,
    layout="centered",
)

st.html("""
<style>
/* ── Typography ── */
[data-testid="stAppViewContainer"] h1 {
    font-size: 22px;
    font-weight: 400;
    letter-spacing: 0.01em;
    margin-bottom: 2px;
}

/* ── Subtitle line ── */
.profiler-subtitle {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-color);
    opacity: 0.45;
    margin-top: 2px;
    margin-bottom: 1.5rem;
}

/* ── Section labels (used above inputs and metric strips) ── */
.section-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    opacity: 0.5;
    margin-bottom: 6px;
}

/* ── Skill pills ── */
.skill-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0 12px;
}
.skill-pill {
    font-size: 12px;
    padding: 3px 11px;
    border-radius: 20px;
    border: 0.5px solid rgba(128,128,128,0.25);
    background: rgba(128,128,128,0.07);
}

/* ── Match score strip ── */
.match-strip {
    display: flex;
    align-items: flex-end;
    gap: 2rem;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
    border-bottom: 0.5px solid rgba(128,128,128,0.15);
    flex-wrap: wrap;
}
.match-primary {
    font-size: 36px;
    font-weight: 500;
    line-height: 1;
}
.match-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    opacity: 0.45;
    margin-top: 3px;
}
.match-stat { text-align: center; }
.match-stat-num { font-size: 16px; font-weight: 500; }
.match-stat-label {
    font-size: 10px;
    opacity: 0.45;
    margin-top: 2px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── QA badge ── */
.qa-badge {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    align-self: flex-end;
    margin-bottom: 4px;
}
.qa-pass {
    background: rgba(34,197,94,0.12);
    color: #16a34a;
}
.qa-fail {
    background: rgba(239,68,68,0.12);
    color: #dc2626;
}

/* ── Job header ── */
.job-header-title {
    font-size: 17px;
    font-weight: 500;
    margin: 0 0 3px;
}
.job-header-meta {
    font-size: 13px;
    opacity: 0.55;
    margin: 0 0 1rem;
}

/* ── Status summary strip ── */
.status-strip {
    display: flex;
    gap: 1.5rem;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
    border-bottom: 0.5px solid rgba(128,128,128,0.15);
    flex-wrap: wrap;
}
.status-stat { text-align: center; }
.status-stat-num {
    font-size: 18px;
    font-weight: 500;
    line-height: 1;
}
.status-stat-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    opacity: 0.45;
    margin-top: 3px;
}

/* ── Status dot colors ── */
.dot-found       { color: #9ca3af; }
.dot-applied     { color: #3b82f6; }
.dot-phone-screen { color: #f59e0b; }
.dot-technical   { color: #f59e0b; }
.dot-offer       { color: #22c55e; }
.dot-rejected    { color: #ef4444; }
.dot-ghosted     { color: #9ca3af; }

/* ── Delete link ── */
.delete-link {
    background: none;
    border: none;
    padding: 0;
    font-size: 12px;
    color: #dc2626;
    cursor: pointer;
    text-decoration: underline;
    text-underline-offset: 3px;
}

/* ── Hide Streamlit default padding/decoration on expanders ── */
[data-testid="stExpander"] summary {
    font-size: 13px !important;
}
</style>
""")

render_header()

# ---------------------------------------------------------------------------
# Model selector (sidebar)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Model")
    model_input = st.text_input(
        "LLM model name",
        value=_base_cfg.MODEL_NAME or "",
        help="Override the model from .env. Leave blank to use the default.",
    )
    st.caption(f"Provider: `{_base_cfg.provider}`")

# Build effective config — override model only if user changed it
_override = model_input.strip() if model_input.strip() != (_base_cfg.MODEL_NAME or "") else None
cfg = AppConfig(model_override=_override) if _override else _base_cfg

for w in validate_config(cfg):
    st.warning(w)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_extract, tab_tracker = st.tabs(["Extract", "Track"])


# ---------------------------------------------------------------------------
# Extract tab
# ---------------------------------------------------------------------------

with tab_extract:
    ui: UIInput = render_input_panel()
    ok, err = validate_inputs(ui)

    # Primary action row: Analyze button only
    with st.expander("Options", expanded=False):
        force = st.checkbox(
            "Re-run even if this URL is already tracked",
            value=False,
        )

    analyze_btn = st.button(
        "Analyze",
        type="primary",
        disabled=not ok,
    )

    if err and not ok:
        st.caption(err)

    if analyze_btn and ok:
        with st.spinner("Fetching and extracting…"):
            run_id = str(uuid4())
            try:
                result: PipelineResult = run_pipeline(
                    url=ui.url if ui.mode == "url" else "",
                    text=ui.text if ui.mode == "text" else "",
                    cfg=cfg,
                    uid=run_id,
                    force=force,
                )
                st.session_state["result"] = result
            except Exception as e:
                OUTPUT_DIR = Path("output") / Path(run_id)
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                (OUTPUT_DIR / "error.txt").write_text(str(e), encoding="utf-8")
                st.error(f"Pipeline failed: {e}")

    result: PipelineResult | None = st.session_state.get("result")

    if result:
        render_match_score(
            result.match_result,
            qa_json=result.qa.model_dump() if result.qa else None,
        )
        render_outputs(
            summary_md=result.markdown,
            extract_json=result.extract.model_dump(),
            qa_json=result.qa.model_dump() if result.qa else None,
        )


# ---------------------------------------------------------------------------
# Track tab
# ---------------------------------------------------------------------------

with tab_tracker:
    render_tracker_tab()
