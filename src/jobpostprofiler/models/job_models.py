"""
JOB POSTING SCHEMAS — PostingExtract and related models.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, ConfigDict, model_validator
from typing import List, Optional, Literal, Annotated, Union


# -------------------------
# Employment models
# -------------------------

class CompanyInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, description="Company name as written in the post.")
    industry: Optional[str] = Field(default=None, description="Industry/sector if explicitly stated.")
    company_size: Optional[str] = Field(default=None, description="Company size if stated. Preserve original wording.")
    headquarters: Optional[str] = Field(default=None, description="HQ location if explicitly mentioned.")
    description: Optional[str] = Field(default=None, description="Short company overview from 'About us' section.")


class RoleDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: Optional[str] = Field(default=None, description="Role title exactly as shown.")
    seniority: Optional[str] = Field(default=None, description="Seniority level if stated. Do not infer.")
    team: Optional[str] = Field(default=None, description="Team/department name if mentioned.")
    location: Optional[str] = Field(default=None, description="Role location(s) as written.")
    workplace_type: Optional[str] = Field(default=None, description="Remote / Hybrid / On-site. Include constraints if stated.")
    employment_type: Optional[str] = Field(default=None, description="Full-time / Part-time / Contract / etc.")
    compensation: Optional[str] = Field(default=None, description="Compensation as stated, with currency.")
    visa_sponsorship: Optional[str] = Field(default=None, description="Visa sponsorship info if stated.")
    interview_stages: List[str] = Field(default_factory=list, description="Interview stages if described.")


class EmploymentDetails(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"description": 
                           "Employment posting details. Contains only: kind, job_id, company, role. No warnings field."
                           }
                           )

    # No warnings field here. Warnings belong in PostingExtract.warnings only.
    kind: Literal["employment"] = "employment"
    job_id: Optional[str] = Field(default=None, description="Internal job ID if present. Do not invent.")
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    role: RoleDetails = Field(default_factory=RoleDetails)


# -------------------------
# Freelance models
# -------------------------

class FreelanceClientInfo(BaseModel):
    model_config = ConfigDict(extra="forbid",)

    location: Optional[str] = Field(default=None, description="Client location as shown on platform.")
    payment_verified: Optional[bool] = Field(default=None, description="Whether platform shows payment verified.")
    total_spend: Optional[str] = Field(default=None, description="Client lifetime spend as shown.")
    hire_rate: Optional[str] = Field(default=None, description="Hire rate as shown.")
    jobs_posted: Optional[str] = Field(default=None, description="Jobs posted count as shown.")


class FreelanceDetails(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"description": 
                           "Freelance posting details. Contains only: kind, title, platform, contract_type, budget, hourly_rate,"
                           "duration, weekly_hours, experience_level, proposals, activity, client, screening_questions. "
                           "No warnings field."
                           }
        )

    # No warnings field here. Warnings belong in PostingExtract.warnings only.
    kind: Literal["freelance"] = "freelance"
    title: Optional[str] = Field(default=None, description="Gig/project title as stated.")
    platform: Optional[str] = Field(default=None, description="Platform name (e.g. Upwork).")
    contract_type: Optional[str] = Field(default=None, description="Fixed-price or hourly, as stated.")
    budget: Optional[str] = Field(default=None, description="Budget/rate range with currency, as stated.")
    hourly_rate: Optional[str] = Field(default=None, description="Hourly rate range if hourly.")
    duration: Optional[str] = Field(default=None, description="Project duration if stated.")
    weekly_hours: Optional[str] = Field(default=None, description="Weekly hours expectation if shown.")
    experience_level: Optional[str] = Field(default=None, description="Entry / Intermediate / Expert if shown.")
    proposals: Optional[str] = Field(default=None, description="Proposal count/range as shown.")
    activity: Optional[str] = Field(default=None, description="Platform activity signals: invites sent, clients interviewing, etc.")
    client: FreelanceClientInfo = Field(default_factory=FreelanceClientInfo)
    screening_questions: List[str] = Field(default_factory=list, description="Platform screening questions if shown.")


# -------------------------
# Internship models
# -------------------------

class InternshipDetails(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"description": 
                           "Internship posting details. Contains: kind, company, role, plus internship-specific fields "
                           "(duration, dates, stipend, mentorship, academic requirements, return offer potential)."
                           }
        )

    # No warnings field here. Warnings belong in PostingExtract.warnings only.
    kind: Literal["internship"] = "internship"
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    role: RoleDetails = Field(default_factory=RoleDetails)
    duration: Optional[str] = Field(default=None, description="Internship duration, e.g. '12 weeks', '3 months', 'Summer 2026'.")
    start_date: Optional[str] = Field(default=None, description="Start date as stated in posting.")
    end_date: Optional[str] = Field(default=None, description="End date as stated in posting.")
    stipend: Optional[str] = Field(default=None, description="Stipend/salary if stated, with currency.")
    housing_provided: Optional[bool] = Field(default=None, description="Whether housing is provided.")
    relocation_assistance: Optional[bool] = Field(default=None, description="Whether relocation assistance is offered.")
    academic_level: Optional[str] = Field(default=None, description="Target academic level, e.g. 'Sophomore', 'Junior', 'Senior', or 'high school'.")
    field_of_study: Optional[str] = Field(default=None, description="Field of study if specified.")
    gpa_requirement: Optional[str] = Field(default=None, description="Minimum GPA if stated.")
    mentorship_provided: Optional[bool] = Field(default=None, description="Whether mentorship/guidance is highlighted.")
    return_offer_potential: Optional[bool] = Field(default=None, description="Whether return offer potential is mentioned.")


# -------------------------
# Skills
# -------------------------

class Skills(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: List[str] = Field(
        default_factory=list,
        description=(
            "Short technology/tool/language labels extracted from REQUIRED content. "
            "1–3 words per label. Examples: 'Python', 'PyTorch', 'RAG', 'Docker', 'SQL'. "
            "Populated by scanning the entire posting — header highlight blocks, "
            "Skills sections, Requirements, and responsibilities bullets. "
            "NEVER full sentences. NEVER empty if any technologies are named in the posting."
        ),
    )
    preferred: List[str] = Field(
        default_factory=list,
        description=(
            "Short technology/tool/language labels extracted from PREFERRED or "
            "qualifier-marked content only. Use when the posting uses: 'preferably', "
            "'ideally', 'a plus', 'is a plus', 'nice to have', 'bonus', 'preferred', "
            "'desired', 'helpful', 'familiarity with', 'exposure to'. "
            "1–3 words per label. Examples: 'Azure', 'C#', 'MLflow', 'LangGraph'. "
            "NEVER duplicate items from skills.required."
        ),
    )


# -------------------------
# Source — extraction metadata
# -------------------------

class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extracted_at: str = Field(description="Extraction date in human-readable format (e.g. '19 Feb 2026').")
    input_type: Literal["url", "text"] = Field(description="Input mode: 'url' or 'text'.")
    url: Optional[str] = Field(default=None, description="URL if input_type is 'url'.")
    file_path: Optional[str] = Field(default=None, description="Normalized file path if input_type is 'text'.")
    source_platform: Optional[str] = Field(default=None, description="Platform identifier if detectable (e.g. 'linkedin', 'upwork', 'wellfound'). For extensibility and platform-specific filtering.")

    @computed_field
    @property
    def ref(self) -> Optional[str]:
        """Canonical source reference. Derived — not set by LLM."""
        return self.url or self.file_path


# -------------------------
# Discriminated union
# -------------------------

PostingDetails = Annotated[
    Union[EmploymentDetails, FreelanceDetails, InternshipDetails],
    Field(discriminator="kind"),
]


# -------------------------
# Top-level envelope
# -------------------------

class PostingExtract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def sanitize_llm_output(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data

        # 1. Coerce null top-level list fields to []
        for field in ("responsibilities", "requirements", "preferred_qualifications", "benefits", "soft_skills", "warnings"):
            if data.get(field) is None:
                data[field] = []

        # 2. Coerce null list fields at correct nested paths
        details = data.get("details")
        if isinstance(details, dict):
            kind = details.get("kind")

            if kind == "employment":
                role = details.get("role")
                if isinstance(role, dict) and role.get("interview_stages") is None:
                    role["interview_stages"] = []

            elif kind == "freelance":
                if details.get("screening_questions") is None:
                    details["screening_questions"] = []

        # 3. Strip warnings leaked into details
        if isinstance(details, dict) and "warnings" in details:
            leaked = details.pop("warnings", [])
            if leaked:
                data["warnings"] = data.get("warnings", []) + [
                    f"[auto-promoted from details] {w}" for w in leaked
                ]

        return data

    source: Source = Field(description="Extraction metadata.")
    details: PostingDetails = Field(
        description=(
            "Type-specific posting details. Must be a single flat object with a top-level 'kind' field. "
            "For employment: kind='employment', with nested 'company' and 'role' objects. "
            "For freelance: kind='freelance', with gig/client fields. "
            "Never wrap as {'employment': {...}} or {'freelance': {...}}."
        )
    )
    responsibilities: List[str] = Field(
        default_factory=list,
        description="Core duties listed in the post. One item per bullet.",
    )
    requirements: List[str] = Field(
        default_factory=list,
        description=(
            "Full-sentence mandatory qualifications from the posting. "
            "Use for: education requirements, years of experience, certifications, "
            "and technical competencies stated as required/must-have. "
            "These are complete readable statements, not short labels. "
            "Example: 'Bachelor degree in Computer Science or related field.' "
            "Example: '3+ years of experience building ML pipelines in Python.' "
            "NEVER place soft skills or behavioral traits here. "
            "NEVER place preferred/plus-qualified items here."
        ),
    )
    preferred_qualifications: List[str] = Field(
        default_factory=list,
        description=(
            "Full-sentence preferred or nice-to-have qualifications from the posting. "
            "Use for: education, experience, or background items marked with "
            "'preferred', 'ideally', 'a plus', 'nice to have', 'bonus', or 'desired'. "
            "These are complete readable statements, not short labels. "
            "Example: 'Master degree preferred.' "
            "Example: '3+ years with RAG systems is a plus.' "
            "Example: 'Prior experience in a regulated industry preferred.' "
            "NEVER duplicate items from requirements[]. "
            "NEVER place short skill labels here — those go in skills.preferred[]."
        ),
    )
    benefits: List[str] = Field(
        default_factory=list,
        description="Benefits and perks if stated.",
    )
    skills: Skills = Field(
        default_factory=Skills,
        description=(
            "Machine-readable skill tag layer. Short labels only (1–3 words). "
            "Distilled from requirements[] → skills.required, "
            "and preferred_qualifications[] → skills.preferred. "
            "Purpose: keyword matching, filtering, and cross-posting comparison. "
            "Not for human reading — use requirements[] and preferred_qualifications[] for that."
        ),
    )
    soft_skills: List[str] = Field(
        default_factory=list,
        description=(
            "Behavioral, interpersonal, and non-technical competencies listed in the posting. "
            "Includes content from 'Soft Skills' sections, communication traits, "
            "collaboration expectations, and problem-solving or adaptability mentions. "
            "Short phrases only. Examples: 'cross-functional collaboration', "
            "'communication clarity', 'adaptability', 'technical mentoring'. "
            "NEVER place these in requirements[], preferred_qualifications[], "
            "or skills.required[]/skills.preferred[]. "
            "Defaults to [] if the posting has no soft skills content."
        ),
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Extraction warnings: missing fields, ambiguous content, blocked pages, etc.",
    )

    @computed_field
    @property
    def posting_kind(self) -> str:
        """Derived from details.kind. Single source of truth."""
        return self.details.kind