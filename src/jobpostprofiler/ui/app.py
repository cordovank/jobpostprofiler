"""
JOB POST PROFILER — Streamlit UI
Run: streamlit run src/jobpostprofiler/ui/app.py
"""
import threading
import time
import streamlit as st
from uuid import uuid4
from jobpostprofiler.config import AppConfig, validate_config
from jobpostprofiler.core.fetcher import FetchContentError
from jobpostprofiler.pipeline import run_pipeline, PipelineCancelled, PipelineResult
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

render_header()

# ---------------------------------------------------------------------------
# Model selector (sidebar)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.caption("MODEL")
    model_input = st.text_input(
        "LLM model name",
        value=_base_cfg.MODEL_NAME or "",
        help="Override the model from .env. Leave blank to use the default.",
    )
    st.caption(f"Provider: `{_base_cfg.provider}`")
    st.divider()
    st.toggle(
        "Dark mode",
        value=False,
        key="dark_mode",
    )

# ---------------------------------------------------------------------------
# Mode-aware CSS injection
# ---------------------------------------------------------------------------

_dark = st.session_state.get("dark_mode", False)

_LIGHT = {
    "page_bg":          "#F6F3EE",
    "sidebar_bg":       "#EFECEA",
    "text":             "#1C1916",
    "text_muted":       "#8A8278",
    "border":           "rgba(28,25,22,0.09)",
    "pill_bg":          "#E8E4DC",
    "pill_text":        "#5A554E",
    "match_num":        "#2D6E4E",
    "qa_pass_bg":       "#E4EDE7",
    "qa_pass_text":     "#2D6E4E",
    "qa_fail_bg":       "#EDE4E2",
    "qa_fail_text":     "#8B3A3A",
    "dot_found":        "#9A9490",
    "dot_applied":      "#3D6E9E",
    "dot_screen":       "#9E6E2A",
    "dot_offer":        "#2D6E4E",
    "dot_rejected":     "#8B3A3A",
    "dot_ghosted":      "#9A9490",
}

_DARK = {
    "page_bg":          "#141618",
    "sidebar_bg":       "#1C1E20",
    "text":             "#E2E4E6",
    "text_muted":       "#72767A",
    "border":           "rgba(226,228,230,0.08)",
    "pill_bg":          "#1E2124",
    "pill_text":        "#9AA0A6",
    "match_num":        "#6BBF8A",
    "qa_pass_bg":       "rgba(107,191,138,0.13)",
    "qa_pass_text":     "#6BBF8A",
    "qa_fail_bg":       "rgba(192,112,112,0.13)",
    "qa_fail_text":     "#C07878",
    "dot_found":        "#6A6560",
    "dot_applied":      "#5F9EC4",
    "dot_screen":       "#C49040",
    "dot_offer":        "#6BBF8A",
    "dot_rejected":     "#C07878",
    "dot_ghosted":      "#6A6560",
}

_C = _DARK if _dark else _LIGHT

_dark_overrides = f"""
/* ── Dark mode: backgrounds ── */
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background-color: {_C["page_bg"]} !important;
}}
[data-testid="stHeader"] {{
    background-color: {_C["page_bg"]} !important;
}}
[data-testid="stHeader"] button {{
    color: {_C["text_muted"]} !important;
}}
[data-testid="stSidebar"] > div:first-child {{
    background-color: {_C["sidebar_bg"]} !important;
}}

/* ── Dark mode: native Streamlit text ── */
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4,
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] div,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {{
    color: {_C["text"]} !important;
}}

/* ── Dark mode: muted elements ── */
[data-testid="stAppViewContainer"] .stCaption,
[data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: {_C["text_muted"]} !important;
}}

/* ── Dark mode: text inputs and textareas ── */
[data-testid="stAppViewContainer"] input,
[data-testid="stAppViewContainer"] textarea,
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {{
    color: {_C["text"]} !important;
    background-color: {_C["pill_bg"]} !important;
    border-color: {_C["border"]} !important;
}}
[data-testid="stAppViewContainer"] input::placeholder,
[data-testid="stAppViewContainer"] textarea::placeholder,
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {{
    color: {_C["text_muted"]} !important;
    opacity: 1 !important;
}}

/* ── Dark mode: selectbox / dropdown (BaseWeb) ── */
[data-testid="stAppViewContainer"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background-color: {_C["pill_bg"]} !important;
    border-color: {_C["border"]} !important;
    color: {_C["text"]} !important;
}}
[data-testid="stAppViewContainer"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] span {{
    color: {_C["text"]} !important;
}}
/* Dropdown menu (popover) + toolbar menu */
[data-baseweb="popover"],
[data-baseweb="popover"] > div {{
    background-color: {_C["sidebar_bg"]} !important;
}}
[data-baseweb="popover"] li,
[data-baseweb="popover"] a,
[data-baseweb="popover"] span {{
    color: {_C["text"]} !important;
    background-color: transparent !important;
}}
[data-baseweb="popover"] li:hover,
[data-baseweb="popover"] a:hover {{
    background-color: {_C["pill_bg"]} !important;
}}
/* Main menu (three-dot / hamburger) */
[data-testid="stMainMenu"] {{
    color: {_C["text_muted"]} !important;
}}
[data-baseweb="modal"] [data-baseweb="menu"],
[data-baseweb="modal"] ul {{
    background-color: {_C["sidebar_bg"]} !important;
}}
[data-baseweb="modal"] li {{
    color: {_C["text"]} !important;
}}
[data-baseweb="modal"] li:hover {{
    background-color: {_C["pill_bg"]} !important;
}}

/* ── Dark mode: tabs ── */
[data-testid="stAppViewContainer"] button[data-baseweb="tab"] {{
    color: {_C["text_muted"]} !important;
}}
[data-testid="stAppViewContainer"] button[data-baseweb="tab"][aria-selected="true"] {{
    color: {_C["text"]} !important;
}}

/* ── Dark mode: expanders ── */
[data-testid="stExpander"] {{
    border-color: {_C["border"]} !important;
    background-color: {_C["pill_bg"]} !important;
}}
[data-testid="stExpander"] summary {{
    color: {_C["text"]} !important;
    background-color: {_C["pill_bg"]} !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background-color: {_C["pill_bg"]} !important;
}}

/* ── Dark mode: table ── */
[data-testid="stTable"] table {{
    color: {_C["text"]} !important;
    background-color: {_C["pill_bg"]} !important;
}}
[data-testid="stTable"] th {{
    color: {_C["text_muted"]} !important;
    background-color: {_C["sidebar_bg"]} !important;
    border-color: {_C["border"]} !important;
}}
[data-testid="stTable"] td {{
    color: {_C["text"]} !important;
    border-color: {_C["border"]} !important;
}}

/* ── Dark mode: buttons ── */
[data-testid="stAppViewContainer"] button,
[data-testid="stSidebar"] button {{
    color: {_C["text"]} !important;
    border-color: {_C["border"]} !important;
    background-color: {_C["pill_bg"]} !important;
}}
[data-testid="stAppViewContainer"] button[data-testid="baseButton-primary"] {{
    color: white !important;
    background-color: {_C["match_num"]} !important;
    border-color: {_C["match_num"]} !important;
}}

/* ── Dark mode: form container ── */
[data-testid="stForm"] {{
    border-color: {_C["border"]} !important;
}}

/* ── Dark mode: checkbox ── */
[data-testid="stCheckbox"] label span {{
    color: {_C["text"]} !important;
}}

/* ── Dark mode: dividers ── */
[data-testid="stAppViewContainer"] hr,
[data-testid="stSidebar"] hr {{
    border-color: {_C["border"]} !important;
}}
""" if _dark else ""

st.html(f"""
<style>
{_dark_overrides}
.profiler-subtitle {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {_C["text_muted"]};
    margin-top: 2px;
    margin-bottom: 1.5rem;
}}
.section-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: {_C["text_muted"]};
    margin-bottom: 6px;
}}
.skill-pill-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0 12px;
}}
.skill-pill {{
    font-size: 12px;
    padding: 3px 11px;
    border-radius: 20px;
    border: 0.5px solid {_C["border"]};
    background: {_C["pill_bg"]};
    color: {_C["pill_text"]};
}}
.match-strip {{
    display: flex;
    align-items: flex-end;
    gap: 2rem;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
    border-bottom: 0.5px solid {_C["border"]};
    flex-wrap: wrap;
}}
.match-primary {{
    font-size: 36px;
    font-weight: 500;
    line-height: 1;
    color: {_C["match_num"]};
}}
.match-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: {_C["text_muted"]};
    margin-top: 3px;
}}
.match-stat {{ text-align: center; }}
.match-stat-num {{
    font-size: 16px;
    font-weight: 500;
    color: {_C["text"]};
}}
.match-stat-label {{
    font-size: 10px;
    color: {_C["text_muted"]};
    margin-top: 2px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.qa-badge {{
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    align-self: flex-end;
    margin-bottom: 4px;
}}
.qa-pass {{
    background: {_C["qa_pass_bg"]};
    color: {_C["qa_pass_text"]};
}}
.qa-fail {{
    background: {_C["qa_fail_bg"]};
    color: {_C["qa_fail_text"]};
}}
.job-header-title {{
    font-size: 17px;
    font-weight: 500;
    margin: 0 0 3px;
    color: {_C["text"]};
}}
.job-header-meta {{
    font-size: 13px;
    color: {_C["text_muted"]};
    margin: 0 0 1rem;
}}
.status-strip {{
    display: flex;
    gap: 1.5rem;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
    border-bottom: 0.5px solid {_C["border"]};
    flex-wrap: wrap;
}}
.status-stat {{ text-align: center; }}
.status-stat-num {{
    font-size: 18px;
    font-weight: 500;
    line-height: 1;
    color: {_C["text"]};
}}
.status-stat-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {_C["text_muted"]};
    margin-top: 3px;
}}
[data-testid="stExpander"] summary {{
    font-size: 13px !important;
}}
</style>
""")

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
        cancel_event = threading.Event()
        container = {"result": None, "error": None}

        def _run():
            try:
                container["result"] = run_pipeline(
                    url=ui.url if ui.mode == "url" else "",
                    text=ui.text if ui.mode == "text" else "",
                    cfg=cfg,
                    uid=str(uuid4()),
                    force=force,
                    cancel=cancel_event.is_set,
                )
            except Exception as exc:
                container["error"] = exc

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()

        status = st.empty()
        stop_col, _ = st.columns([1, 3])
        stop_holder = stop_col.empty()
        tick = 0

        while worker.is_alive():
            stop_holder.empty()
            if stop_holder.button("Stop analysis", key=f"stop_btn_{tick}"):
                cancel_event.set()
                status.info("Cancelling…")
            else:
                status.info("Fetching and extracting…")
            tick += 1
            time.sleep(0.3)

        status.empty()
        stop_holder.empty()

        if cancel_event.is_set():
            st.warning("Analysis stopped.")
        elif container["error"] is not None:
            exc = container["error"]
            if isinstance(exc, FetchContentError):
                st.error(exc.message)
                st.info("Tip: switch to the **Text** tab and paste the job posting content directly.")
            elif isinstance(exc, PipelineCancelled):
                st.warning("Analysis stopped.")
            else:
                st.error(f"Pipeline failed: {exc}")
        else:
            st.session_state["result"] = container["result"]

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
