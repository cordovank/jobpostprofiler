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

## At a Glance
| Field | Value |
|---|---|
| Role | {{ role.job_title or "Not stated" }} |
| Seniority | {{ role.seniority or "Not stated" }} |
| Location | {{ role.location or "Not stated" }} |
| Workplace | {{ role.workplace_type or "Not stated" }} |
| Employment Type | {{ role.employment_type or "Not stated" }} |
| Compensation | {{ role.compensation or "Not stated" }} |
{% if role.visa_sponsorship %}
| Visa Sponsorship | {{ role.visa_sponsorship }} |
{% endif %}

{% if company.description %}
## About {{ company.name or "the Company" }}
{{ company.description }}
{% if company.industry or company.company_size or company.headquarters %}
*{% if company.industry %}Industry: {{ company.industry }}{% endif %}{% if company.company_size %}  · Size: {{ company.company_size }}{% endif %}{% if company.headquarters %}  · HQ: {{ company.headquarters }}{% endif %}*
{% endif %}
{% endif %}

## Required Skills
{% if skills.required %}
{{ skills.required | join(" · ") }}
{% else %}
Not specified
{% endif %}

{% if skills.preferred %}
## Preferred Skills
{{ skills.preferred | join(" · ") }}
{% endif %}

## What You'll Do
{% for r in responsibilities %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## What They're Looking For

### Must Have
{% for r in requirements %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

{% if preferred_qualifications %}
### Nice to Have
{% for r in preferred_qualifications %}
- {{ r }}
{% endfor %}
{% endif %}

{% if soft_skills %}
## Soft Skills
{% for s in soft_skills %}
- {{ s }}
{% endfor %}
{% endif %}

{% if benefits %}
## Benefits
{% for b in benefits %}
- {{ b }}
{% endfor %}
{% endif %}

{% if warnings %}
## Extraction Notes
The following fields were absent from the posting:
{% for w in warnings %}
- {{ w }}
{% endfor %}
{% endif %}

---
*Source: {{ source.ref }}  ·  Extracted: {{ source.extracted_at }}*
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
## Extraction Notes
The following fields were absent from the posting:
{% for w in warnings %}
- {{ w }}
{% endfor %}
{% endif %}

---
*Source: {{ source.ref }}  ·  Extracted: {{ source.extracted_at }}*
"""

INTERNSHIP_TEMPLATE = """\
# {{ title_line }}  [Internship]

## At a Glance
| Field | Value |
|---|---|
| Role | {{ role.job_title or "Not stated" }} |
{% if details.academic_level %}
| Academic Level | {{ details.academic_level }} |
{% endif %}
| Location | {{ role.location or "Not stated" }} |
{% if role.workplace_type %}
| Workplace | {{ role.workplace_type }} |
{% endif %}
{% if details.duration %}
| Duration | {{ details.duration }} |
{% endif %}
{% if details.start_date %}
| Start Date | {{ details.start_date }} |
{% endif %}
{% if details.end_date %}
| End Date | {{ details.end_date }} |
{% endif %}
| Compensation / Stipend | {{ role.compensation or details.stipend or "Not stated" }} |
{% if details.housing_provided is not none %}
| Housing | {{ details.housing_provided }} |
{% endif %}
{% if details.relocation_assistance is not none %}
| Relocation | {{ details.relocation_assistance }} |
{% endif %}
{% if details.mentorship_provided is not none %}
| Mentorship | {{ details.mentorship_provided }} |
{% endif %}
{% if details.return_offer_potential is not none %}
| Return Offer Potential | {{ details.return_offer_potential }} |
{% endif %}

{% if company.description %}
## About {{ company.name or "the Company" }}
{{ company.description }}
{% if company.industry or company.company_size or company.headquarters %}
*{% if company.industry %}Industry: {{ company.industry }}{% endif %}{% if company.company_size %}  · Size: {{ company.company_size }}{% endif %}{% if company.headquarters %}  · HQ: {{ company.headquarters }}{% endif %}*
{% endif %}
{% endif %}

## Required Skills
{% if skills.required %}
{{ skills.required | join(" · ") }}
{% else %}
Not specified
{% endif %}

{% if skills.preferred %}
## Preferred Skills
{{ skills.preferred | join(" · ") }}
{% endif %}

## What You'll Do
{% for r in responsibilities %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

## What They're Looking For

### Must Have
{% for r in requirements %}
- {{ r }}
{% else %}
- Not stated
{% endfor %}

{% if preferred_qualifications %}
### Nice to Have
{% for r in preferred_qualifications %}
- {{ r }}
{% endfor %}
{% endif %}

{% if soft_skills %}
## Soft Skills
{% for s in soft_skills %}
- {{ s }}
{% endfor %}
{% endif %}

{% if details.academic_level or details.field_of_study or details.gpa_requirement %}
## Academic Requirements
{% if details.academic_level %}
- Academic Level: {{ details.academic_level }}
{% endif %}
{% if details.field_of_study %}
- Field of Study: {{ details.field_of_study }}
{% endif %}
{% if details.gpa_requirement %}
- GPA Requirement: {{ details.gpa_requirement }}
{% endif %}
{% endif %}

{% if benefits %}
## Benefits
{% for b in benefits %}
- {{ b }}
{% endfor %}
{% endif %}

{% if warnings %}
## Extraction Notes
The following fields were absent from the posting:
{% for w in warnings %}
- {{ w }}
{% endfor %}
{% endif %}

---
*Source: {{ source.ref }}  ·  Extracted: {{ source.extracted_at }}*
"""


# ---------------------------------------------------------------------------
# Render entry point
# ---------------------------------------------------------------------------

_env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)

_EMPLOYMENT_TMPL = _env.from_string(EMPLOYMENT_TEMPLATE)
_FREELANCE_TMPL = _env.from_string(FREELANCE_TEMPLATE)
_INTERNSHIP_TMPL = _env.from_string(INTERNSHIP_TEMPLATE)


def render_markdown(extract: PostingExtract) -> str:
    """
    Render a markdown summary from a validated PostingExtract.
    Fully deterministic — no LLM call.
    """
    kind = extract.posting_kind
    
    if kind == "employment":
        tmpl = _EMPLOYMENT_TMPL
        title_parts = [
            extract.details.role.job_title,
            extract.details.company.name,
        ]
        title_line = " @ ".join(p for p in title_parts if p) or "Job Posting"
    elif kind == "internship":
        tmpl = _INTERNSHIP_TMPL
        title_parts = [
            extract.details.role.job_title or "Internship",
            extract.details.company.name,
        ]
        title_line = " @ ".join(p for p in title_parts if p) or "Internship Posting"
    else:
        tmpl = _FREELANCE_TMPL
        title_line = extract.details.title or "Freelance Posting"
        if extract.details.platform:
            title_line += f" ({extract.details.platform})"

    return tmpl.render(
        title_line=title_line,
        source=extract.source,
        details=extract.details,
        company=extract.details.company if kind in ("employment", "internship") else None,
        role=extract.details.role if kind in ("employment", "internship") else None,
        responsibilities=extract.responsibilities,
        requirements=extract.requirements,
        preferred_qualifications=extract.preferred_qualifications,
        benefits=extract.benefits,
        skills=extract.skills,
        soft_skills=extract.soft_skills,
        warnings=extract.warnings,
    )