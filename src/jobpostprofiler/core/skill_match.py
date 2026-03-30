"""
Skill match scoring — pure Python, no I/O, no LLM deps.

Compares a user's skill set against a job's required/preferred skills
using case-insensitive set intersection. Zero LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass


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
    user_set = {s.lower().strip() for s in user_skills}

    req_matched = [s for s in required_skills if s.lower().strip() in user_set]
    req_missing = [s for s in required_skills if s.lower().strip() not in user_set]
    pref_matched = [s for s in preferred_skills if s.lower().strip() in user_set]
    pref_missing = [s for s in preferred_skills if s.lower().strip() not in user_set]

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
