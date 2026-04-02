"""
CLI ENTRY POINT — for local testing without the Streamlit UI.
Usage: python -m jobpostprofiler.main
"""
from jobpostprofiler.config import AppConfig, validate_config
from jobpostprofiler.pipeline import run_pipeline

EXAMPLE_TEXT = """
Applied Scientist- AI/ML Intern
Location: Remote, United States
Employment Type: Full time
Compensation: $45 – $55 per hour

About Us
Wealth.com is the industry's leading estate planning platform...

Key Responsibilities
- Work with complex datasets to build ETL pipelines
- Finetune and integrate LLMs such as OpenAI/Gemini/MistralAI
- Train and deploy large-scale NLP and CV models
- Design scalable Q&A RAG frameworks

Required Qualifications
- Bachelor's, Master's or PhD in CS or related field
- Experience building RAG pipelines with LLMs

Preferred Qualifications
- Master's or PhD preferred
- 1+ year experience productionizing ML models
"""

def main():
    cfg = AppConfig()

    for w in validate_config(cfg):
        print(f"[WARN] {w}")

    print("Running pipeline...")
    result = run_pipeline(text=EXAMPLE_TEXT, cfg=cfg)
    
    print(f"\nRun ID: {result.run_id}")
    print(f"Job ID: {result.job_id}")
    print(f"QA passed: {result.qa.passed}")

    if result.qa.issues:
        print("QA issues:")
        for issue in result.qa.issues:
            print(f"  - {issue}")

    print("\n--- Markdown Summary ---")
    print(result.markdown)


if __name__ == "__main__":
    main()
