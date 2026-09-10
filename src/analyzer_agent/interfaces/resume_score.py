from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    relevance_to_target_positions: float = Field(ge=0, le=10)
    technical_skills: float = Field(ge=0, le=10)
    professional_experience: float = Field(ge=0, le=10)
    achievement_oriented_descriptions: float = Field(ge=0, le=10)
    ats_optimization: float = Field(ge=0, le=10)
    clarity_and_structure: float = Field(ge=0, le=10)
    seniority_positioning: float = Field(ge=0, le=10)


class ResumeScore(BaseModel):
    overall_score: float = Field(ge=1, le=10)
    explanation: str
    breakdown: ScoreBreakdown