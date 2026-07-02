from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of readiness score components."""
    completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Data completeness (0-1)")
    freshness: float = Field(default=0.0, ge=0.0, le=1.0, description="Data freshness (0-1)")
    size: float = Field(default=0.0, ge=0.0, le=1.0, description="Dataset size (0-1)")
    documentation: float = Field(default=0.0, ge=0.0, le=1.0, description="Documentation quality (0-1)")
    license: float = Field(default=0.0, ge=0.0, le=1.0, description="License clarity (0-1)")


class ReadinessScore(BaseModel):
    """Readiness score for a dataset (0-100 scale). Grade auto-computed from total."""
    total: float = Field(default=0.0, ge=0.0, le=100.0, description="Total score (0-100)")
    grade: str = Field(default="F", description="Auto-computed: A>=80, B>=60, C>=40, D>=20, F<20")
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    @model_validator(mode="after")
    def compute_grade(self) -> "ReadinessScore":
        if self.total >= 80:
            self.grade = "A"
        elif self.total >= 60:
            self.grade = "B"
        elif self.total >= 40:
            self.grade = "C"
        elif self.total >= 20:
            self.grade = "D"
        else:
            self.grade = "F"
        return self


class RelevanceScore(BaseModel):
    """Relevance score for a dataset against a query."""
    cosine_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Embedding cosine similarity")
    keyword_match: float = Field(default=0.0, ge=0.0, le=1.0, description="Keyword match score")
    domain_match: float = Field(default=0.0, ge=0.0, le=1.0, description="Domain category match")
    final_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Weighted final relevance score")
