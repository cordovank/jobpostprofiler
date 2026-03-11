"""
POSTING KIND CLASSIFIER — deterministic heuristic, no LLM.
Returns "employment", "freelance", or "internship".
"""

from __future__ import annotations

_FREELANCE_SIGNALS = [
    "upwork", "fiverr", "toptal", "freelancer.com",
    "fixed-price", "fixed price", "hourly contract",
    "proposals:", "invite sent", "clients interviewing",
    "payment verified",
]

_INTERNSHIP_SIGNALS = [
    "internship", "intern", "summer internship", "fall internship", "spring internship",
    "duration:", "weeks", "graduating", "gpa", "academic",
    "mentorship", "stipend", "housing provided", "relocation",
    "return offer", "student", "college", "university",
]

_EMPLOYMENT_SIGNALS = [
    "apply now", "apply for this job", "full-time", "full time",
    "part-time", "part time", "salary", "benefits",
    "equal opportunity employer", "department:", "team:",
    "ashby", "lever.co", "greenhouse.io", "workday",
]


def classify_kind(text: str) -> str:
    """
    Returns 'employment', 'freelance', or 'internship' based on signal counts.
    Employment is the default when signals are ambiguous.
    """
    lower = text.lower()

    freelance_score = sum(1 for sig in _FREELANCE_SIGNALS if sig in lower)
    internship_score = sum(1 for sig in _INTERNSHIP_SIGNALS if sig in lower)
    employment_score = sum(1 for sig in _EMPLOYMENT_SIGNALS if sig in lower)

    # Priority: freelance > internship > employment (default)
    if freelance_score > internship_score and freelance_score > employment_score:
        return "freelance"
    elif internship_score > employment_score:
        return "internship"
    else:
        return "employment"