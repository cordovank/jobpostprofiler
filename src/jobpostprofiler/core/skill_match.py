"""
Skill match scoring — pure Python, no I/O, no LLM deps.

Compares a user's skill set against a job's required/preferred skills
using case-insensitive set intersection. Zero LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_ALIASES: dict[str, str] = {
    # ML / AI
    "machine learning":               "ml",
    "ml":                             "ml",
    "deep learning":                  "dl",
    "dl":                             "dl",
    "natural language processing":    "nlp",
    "nlp":                            "nlp",
    "large language model":           "llm",
    "large language models":          "llm",
    "llms":                           "llm",
    "llm":                            "llm",
    "retrieval-augmented generation": "rag",
    "retrieval augmented generation": "rag",
    "rag":                            "rag",
    "reinforcement learning":         "rl",
    "rl":                             "rl",
    "computer vision":                "cv",
    "cv":                             "cv",
    # Frameworks / libraries
    "huggingface":                    "hugging face",
    "hugging face":                   "hugging face",
    "hf transformers":                "hugging face",
    "transformers":                   "hugging face",
    "sklearn":                        "scikit-learn",
    "scikit-learn":                   "scikit-learn",
    "scikit learn":                   "scikit-learn",
    "pytorch":                        "pytorch",
    "torch":                          "pytorch",
    "tensorflow":                     "tensorflow",
    "tf":                             "tensorflow",
    "langchain":                      "langchain",
    "lang chain":                     "langchain",
    "langgraph":                      "langgraph",
    "openai":                         "openai api",
    "openai api":                     "openai api",
    # Infrastructure / serving
    "fastapi":                        "fastapi",
    "fast api":                       "fastapi",
    "docker":                         "docker",
    "containerization":               "docker",
    "kubernetes":                     "kubernetes",
    "k8s":                            "kubernetes",
    "aws":                            "aws",
    "amazon web services":            "aws",
    "gcp":                            "gcp",
    "google cloud":                   "gcp",
    "azure":                          "azure",
    "microsoft azure":                "azure",
    # Databases / retrieval
    "vector database":                "vector databases",
    "vector db":                      "vector databases",
    "vector databases":               "vector databases",
    "faiss":                          "faiss",
    "pinecone":                       "pinecone",
    "chroma":                         "chromadb",
    "chromadb":                       "chromadb",
    "weaviate":                       "weaviate",
    "bm25":                           "bm25",
    "elasticsearch":                  "elasticsearch",
    "postgres":                       "postgresql",
    "postgresql":                     "postgresql",
    # Experiment tracking / MLOps
    "weights & biases":               "wandb",
    "weights and biases":             "wandb",
    "wandb":                          "wandb",
    "mlflow":                         "mlflow",
    "ml flow":                        "mlflow",
    "dvc":                            "dvc",
    "sagemaker":                      "sagemaker",
    "amazon sagemaker":               "sagemaker",
    # Languages
    "python3":                        "python",
    "python":                         "python",
    "javascript":                     "javascript",
    "js":                             "javascript",
    "typescript":                     "typescript",
    "ts":                             "typescript",
    "react.js":                       "react",
    "reactjs":                        "react",
    "react":                          "react",
    # Evaluation
    "ragas":                          "ragas",
    "bleu":                           "bleu",
    "rouge":                          "rouge",
    "mrr":                            "mrr",
    # ML / AI (additional)
    "generative ai":                  "generative ai",
    "gen ai":                         "generative ai",
    "genai":                          "generative ai",
    # Frameworks / libraries (additional)
    "hugging face transformers":      "hugging face",
    "huggingface transformers":       "hugging face",
    "sentence transformers":          "sentence transformers",
    "sentence-transformers":          "sentence transformers",
    "spring boot":                    "spring",
    "spring":                         "spring",
    "spring framework":               "spring",
    # Infrastructure / serving (additional)
    "containerisation":               "docker",
    "containers":                     "docker",
    "selenium":                       "selenium",
    "selenium webdriver":             "selenium",
    # Databases / retrieval (additional)
    "sqlite":                         "sqlite",
    "sqlite3":                        "sqlite",
    # Languages (additional)
    "python 3":                       "python",
    "java":                           "java",
    "c++":                            "c++",
    "cpp":                            "c++",
    "r":                              "r",
    # Build / tooling
    "jinja":                          "jinja2",
    "jinja2":                         "jinja2",
    "junit":                          "junit",
    "junit5":                         "junit",
    "cucumber":                       "cucumber",
    "postman":                        "postman",
    "swagger":                        "swagger",
    "openapi":                        "swagger",
    "jira":                           "jira",
    "confluence":                     "confluence",
    "jenkins":                        "jenkins",
    "maven":                          "maven",
    "gradle":                         "maven",
    "bitbucket":                      "bitbucket",
    "linux":                          "linux",
    "unix":                           "linux",
    "ubuntu":                         "linux",
    "matplotlib":                     "matplotlib",
    "uv":                             "uv",
    # Soft / cross-cutting
    "rest api":                       "rest apis",
    "restful api":                    "rest apis",
    "rest apis":                      "rest apis",
    "api development":                "rest apis",
    "api design":                     "rest apis",
    "api engineering":                "rest apis",
    "microservices":                  "microservices",
    "micro services":                 "microservices",
    "ci/cd":                          "ci/cd",
    "ci cd":                          "ci/cd",
    "continuous integration":         "ci/cd",
    "etl":                            "etl",
    "data pipelines":                 "data pipelines",
    "data pipeline":                  "data pipelines",
    "prompt engineering":             "prompt engineering",
    "structured outputs":             "structured outputs",
    "structured output":              "structured outputs",
    "embedding models":               "embedding models",
    "embeddings":                     "embedding models",
    "vector search":                  "vector databases",
    "vector store":                   "vector databases",
    "vector stores":                  "vector databases",
    "agentic":                        "agentic ai",
    "agentic ai":                     "agentic ai",
    "ai agents":                      "agentic ai",
    "agent framework":                "agentic ai",
    "crewai":                         "crewai",
    "crew ai":                        "crewai",
    "ollama":                         "ollama",
    "gradio":                         "gradio",
    "streamlit":                      "streamlit",
    "numpy":                          "numpy",
    "pandas":                         "pandas",
    "jupyter":                        "jupyter",
    "jupyter notebook":               "jupyter",
    "jupyter notebooks":              "jupyter",
    "kafka":                          "kafka",
    "apache kafka":                   "kafka",
    "cloudflare":                     "cloudflare workers",
    "cloudflare workers":             "cloudflare workers",
    "github pages":                   "github pages",
    "hugging face spaces":            "hugging face spaces",
    "hf spaces":                      "hugging face spaces",
    "pydantic":                       "pydantic",
    "sql":                            "sql",
    "git":                            "git",
    "version control":                "git",
    "agile":                          "agile",
    "scrum":                          "agile",
}


def _normalize(skill: str) -> str:
    """Lowercase, strip, then resolve through alias map.
    Unknown skills pass through unchanged."""
    key = skill.lower().strip()
    return _ALIASES.get(key, key)


# Minimum token length to allow substring matching.
# Prevents "r", "c", "go" from matching everything.
_MIN_FUZZY_LEN = 3


def _fuzzy_in(skill: str, user_set: set[str], user_list: list[str]) -> bool:
    """Substring containment fallback after alias miss.

    Returns True if:
      - normalized skill is a substring of any user skill, OR
      - any user skill is a substring of the normalized skill
    Only triggers when both sides are >= _MIN_FUZZY_LEN chars.
    """
    normed = _normalize(skill)
    if len(normed) < _MIN_FUZZY_LEN:
        return False
    for u in user_list:
        u_normed = _normalize(u)
        if len(u_normed) < _MIN_FUZZY_LEN:
            continue
        if normed in u_normed or u_normed in normed:
            return True
    return False


@dataclass
class MatchResult:
    """Result of comparing user skills against a job posting."""
    required_matched: list[str]
    required_missing: list[str]
    preferred_matched: list[str]
    preferred_missing: list[str]
    required_pct: float      # 0.0 – 1.0
    preferred_pct: float     # 0.0 – 1.0
    overall_score: float     # 0.0 – 1.0, weighted
    # --- Soft skill dimension ---
    soft_matched: list[str] = field(default_factory=list)
    soft_missing: list[str] = field(default_factory=list)
    soft_pct: float = 1.0   # default 1.0 = no penalty when JD has no soft skills


def _dedup_skills(skills: list[str]) -> list[str]:
    """Normalize through alias map and deduplicate, preserving first occurrence's original casing."""
    seen: dict[str, str] = {}  # canonical → original
    for s in skills:
        canonical = _normalize(s)
        if canonical not in seen:
            seen[canonical] = s
    return list(seen.values())


def compute_match(
    user_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    required_weight: float = 0.65,
    preferred_weight: float = 0.25,
    *,
    user_soft_skills: list[str] | None = None,
    job_soft_skills: list[str] | None = None,
    soft_weight: float = 0.10,
) -> MatchResult:
    """Case-insensitive set intersection scoring with substring fallback.

    Args:
        user_skills:      Skills the user has (from my_skills.json).
        required_skills:  Job's required skills (from PostingExtract).
        preferred_skills: Job's preferred skills (from PostingExtract).
        required_weight:  Weight for required skill coverage (default 0.65).
        preferred_weight: Weight for preferred skill coverage (default 0.25).
        user_soft_skills: User's soft skills (from my_skills.json).
        job_soft_skills:  Job's soft skills (from PostingExtract).
        soft_weight:      Weight for soft skill coverage (default 0.10).

    Returns:
        MatchResult with matched/missing lists and scores.
    """
    required_skills = _dedup_skills(required_skills)
    preferred_skills = _dedup_skills(preferred_skills)

    user_set = {_normalize(s) for s in user_skills}

    # Pre-compute normalized user list for fuzzy fallback
    user_list_normalized = list(user_skills)

    def _is_match(skill: str) -> bool:
        """Exact alias match first, substring fallback second."""
        if _normalize(skill) in user_set:
            return True
        return _fuzzy_in(skill, user_set, user_list_normalized)

    req_matched  = [s for s in required_skills  if _is_match(s)]
    req_missing  = [s for s in required_skills  if not _is_match(s)]
    pref_matched = [s for s in preferred_skills if _is_match(s)]
    pref_missing = [s for s in preferred_skills if not _is_match(s)]

    req_pct = len(req_matched) / len(required_skills) if required_skills else 1.0
    pref_pct = len(pref_matched) / len(preferred_skills) if preferred_skills else 1.0

    # --- Soft skill matching ---
    _user_soft = user_soft_skills or []
    _job_soft = job_soft_skills or []
    _job_soft_deduped = _dedup_skills(_job_soft)

    user_soft_set = {_normalize(s) for s in _user_soft}
    soft_matched = [s for s in _job_soft_deduped if _normalize(s) in user_soft_set
                    or _fuzzy_in(s, user_soft_set, _user_soft)]
    soft_missing = [s for s in _job_soft_deduped if s not in soft_matched]
    soft_pct = len(soft_matched) / len(_job_soft_deduped) if _job_soft_deduped else 1.0

    overall = req_pct * required_weight + pref_pct * preferred_weight + soft_pct * soft_weight

    return MatchResult(
        required_matched=req_matched,
        required_missing=req_missing,
        preferred_matched=pref_matched,
        preferred_missing=pref_missing,
        required_pct=req_pct,
        preferred_pct=pref_pct,
        overall_score=overall,
        soft_matched=soft_matched,
        soft_missing=soft_missing,
        soft_pct=soft_pct,
    )
