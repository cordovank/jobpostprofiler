"""
Skill match scoring — pure Python, no I/O, no LLM deps.

Compares a user's skill set against a job's required/preferred skills
using case-insensitive set intersection. Zero LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass

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
    # Soft / cross-cutting
    "rest api":                       "rest apis",
    "restful api":                    "rest apis",
    "rest apis":                      "rest apis",
    "api development":                "rest apis",
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


def compute_match(
    user_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    required_weight: float = 0.7,
    preferred_weight: float = 0.3,
) -> MatchResult:
    """Case-insensitive set intersection scoring.

    Args:
        user_skills:      Skills the user has (from my_skills.json).
        required_skills:  Job's required skills (from PostingExtract).
        preferred_skills: Job's preferred skills (from PostingExtract).
        required_weight:  Weight for required skill coverage (default 0.7).
        preferred_weight: Weight for preferred skill coverage (default 0.3).

    Returns:
        MatchResult with matched/missing lists and scores.
    """
    user_set = {_normalize(s) for s in user_skills}

    req_matched  = [s for s in required_skills  if _normalize(s) in user_set]
    req_missing  = [s for s in required_skills  if _normalize(s) not in user_set]
    pref_matched = [s for s in preferred_skills if _normalize(s) in user_set]
    pref_missing = [s for s in preferred_skills if _normalize(s) not in user_set]

    req_pct = len(req_matched) / len(required_skills) if required_skills else 1.0
    pref_pct = len(pref_matched) / len(preferred_skills) if preferred_skills else 1.0

    overall = req_pct * required_weight + pref_pct * preferred_weight

    return MatchResult(
        required_matched=req_matched,
        required_missing=req_missing,
        preferred_matched=pref_matched,
        preferred_missing=pref_missing,
        required_pct=req_pct,
        preferred_pct=pref_pct,
        overall_score=overall,
    )
