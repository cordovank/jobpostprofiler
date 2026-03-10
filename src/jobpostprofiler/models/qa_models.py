"""QA report schema."""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class QAReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(description="True if extraction meets quality bar.")
    issues: list[str] = Field(default_factory=list, description="List of identified issues.")
    missing_fields: list[str] = Field(default_factory=list, description="Fields missing from extraction.")