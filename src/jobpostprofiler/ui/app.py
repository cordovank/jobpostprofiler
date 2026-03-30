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
    UIInput,
)


cfg = AppConfig()


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Job Post Profiler",
    page_icon="💼",
    layout="centered",
)

render_header()

for w in validate_config(cfg):
    st.warning(w)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

ui: UIInput = render_input_panel()
ok, err = validate_inputs(ui)

cols = st.columns([1, 1, 1, 1])
with cols[0]:
    run_btn = st.button("Run extraction", type="primary", disabled=not ok)
with cols[1]:
    force = st.checkbox("Force re-process", help="Skip duplicate URL check")
with cols[2]:
    st.button("Clear", on_click=lambda: st.session_state.clear())

if err and not ok:
    st.warning(err)


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

if run_btn and ok:
    with st.spinner("Fetching, extracting, auditing..."):
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
            # st.success(f"Done. Run ID: `{result.run_id}`")
            st.success(f"Done. Run ID: `{run_id}`")
        except Exception as e:
            OUTPUT_DIR = Path("output") / Path(run_id)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            ERROR_PATH = OUTPUT_DIR / "error.txt"
            with open (file=ERROR_PATH, mode="x") as file:
                file.write(f"{e}")
            st.error(f"Pipeline failed: {e}")


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

result: PipelineResult | None = st.session_state.get("result")

if result:
    render_outputs(
        summary_md=result.markdown,
        extract_json=result.extract.model_dump(),
        qa_json=result.qa.model_dump(),
    )
