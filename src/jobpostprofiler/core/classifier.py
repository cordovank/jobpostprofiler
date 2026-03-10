"""
POSTING KIND CLASSIFIER — deterministic heuristic, no LLM.
Returns "employment" or "freelance".
"""

from __future__ import annotations

_FREELANCE_SIGNALS = [
    "upwork", "fiverr", "toptal", "freelancer.com",
    "fixed-price", "fixed price", "hourly contract",
    "proposals:", "invite sent", "clients interviewing",
    "payment verified",
]

_EMPLOYMENT_SIGNALS = [
    "apply now", "apply for this job", "full-time", "full time",
    "part-time", "part time", "salary", "benefits",
    "equal opportunity employer", "department:", "team:",
    "ashby", "lever.co", "greenhouse.io", "workday",
]


def classify_kind(text: str) -> str:
    """
    Returns 'freelance' or 'employment' based on signal counts.
    Employment is the default when signals are ambiguous.
    """
    lower = text.lower()

    freelance_score = sum(1 for sig in _FREELANCE_SIGNALS if sig in lower)
    employment_score = sum(1 for sig in _EMPLOYMENT_SIGNALS if sig in lower)

    return "freelance" if freelance_score > employment_score else "employment"