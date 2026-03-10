"""
RENDERER — deterministic Jinja2 markdown rendering. No LLM.

Takes a validated PostingExtract and fills the template. 
Null values become "Not stated".
"""

from __future__ import annotations

from jinja2 import Environment, BaseLoader
from jobpostprofiler.models.job_models import PostingExtract


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

EMPLOYMENT_TEMPLATE = """\
# {{ title_line }}

## Role Details
| Field | Value |
|---|---|
| Job Title | {{ role.job_title or "Not stated" }} |
| Seniority | {{ role.seniority or "Not stated" }} |
| Team | {{ role.team or "Not stated" }} |
| Location | {{ role.location or "Not stated" }} |
| Workplace Type | {{ role.workplace_type or "Not stated" }} |
| Employment Type | {{ role.employment_type or "Not stated" }} |
| Compensation | {{ role.compensation or "Not stated" }} |
| Visa Sponsorship | {{ role.visa_sponsorship or "Not stated" }} |

## Company
| Field | Value |
|---|---|
| Name | {{ company.name or "Not stated" }} |
| Industry | {{ company.industry or "Not stated" }} |
| Size | {{ company.company_size or "Not stated" }} |
| HQ | {{ company.headquarters or "Not stated" }} |

{% if company.description %}
**About:** {{ company.description }}
{% endif %}

## Responsibilities
{% for r in responsibilities %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## Requirements
{% for r in requirements %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## Preferred Qualifications
{% for r in preferred_qualifications %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## Skills
**Required:** {% if skills.required %}{{ skills.required | join(", ") }}{% else %}Not stated{% endif %}

**Preferred:** {% if skills.preferred %}{{ skills.preferred | join(", ") }}{% else %}Not stated{% endif %}

## Benefits
{% for b in benefits %}
- {{ b }}
{% else %}
- Not stated
{% endfor %}

{% if warnings %}
## ⚠️ Extraction Warnings
{% for w in warnings %}
- {{ w }}
{% endfor %}
{% endif %}

---
*Extracted from: {{ source.ref }}*
"""

FREELANCE_TEMPLATE = """\
# {{ title_line }}

## Gig Details
| Field | Value |
|---|---|
| Platform | {{ details.platform or "Not stated" }} |
| Contract Type | {{ details.contract_type or "Not stated" }} |
| Budget | {{ details.budget or "Not stated" }} |
| Hourly Rate | {{ details.hourly_rate or "Not stated" }} |
| Duration | {{ details.duration or "Not stated" }} |
| Weekly Hours | {{ details.weekly_hours or "Not stated" }} |
| Experience Level | {{ details.experience_level or "Not stated" }} |
| Proposals | {{ details.proposals or "Not stated" }} |

## Client Info
| Field | Value |
|---|---|
| Location | {{ details.client.location or "Not stated" }} |
| Payment Verified | {{ details.client.payment_verified if details.client.payment_verified is not none else "Not stated" }} |
| Total Spend | {{ details.client.total_spend or "Not stated" }} |
| Hire Rate | {{ details.client.hire_rate or "Not stated" }} |
| Jobs Posted | {{ details.client.jobs_posted or "Not stated" }} |

## Responsibilities
{% for r in responsibilities %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## Requirements
{% for r in requirements %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## Skills
**Required:** {% if skills.required %}{{ skills.required | join(", ") }}{% else %}Not stated{% endif %}

**Preferred:** {% if skills.preferred %}{{ skills.preferred | join(", ") }}{% else %}Not stated{% endif %}

{% if details.screening_questions %}
## Screening Questions
{% for q in details.screening_questions %}
- {{ q }}
{% endfor %}
{% endif %}

{% if warnings %}
## ⚠️ Extraction Warnings
{% for w in warnings %}
- {{ w }}
{% endfor %}
{% endif %}

---
*Extracted from: {{ source.ref }}*
"""


# ---------------------------------------------------------------------------
# Render entry point
# ---------------------------------------------------------------------------

_env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)


def render_markdown(extract: PostingExtract) -> str:
    """
    Render a markdown summary from a validated PostingExtract.
    Fully deterministic — no LLM call.
    """
    kind = extract.posting_kind
    template_str = EMPLOYMENT_TEMPLATE if kind == "employment" else FREELANCE_TEMPLATE

    if kind == "employment":
        title_parts = [
            extract.details.role.job_title,
            extract.details.company.name,
        ]
        title_line = " @ ".join(p for p in title_parts if p) or "Job Posting"
    else:
        title_line = extract.details.title or "Freelance Posting"
        if extract.details.platform:
            title_line += f" ({extract.details.platform})"

    tmpl = _env.from_string(template_str)
    return tmpl.render(
        title_line=title_line,
        source=extract.source,
        details=extract.details,
        company=extract.details.company if kind == "employment" else None,
        role=extract.details.role if kind == "employment" else None,
        responsibilities=extract.responsibilities,
        requirements=extract.requirements,
        preferred_qualifications=extract.preferred_qualifications,
        benefits=extract.benefits,
        skills=extract.skills,
        warnings=extract.warnings,
    )