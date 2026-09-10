from pydantic import BaseModel, Field

VALID_PRIORITIES = {"High", "Medium", "Low"}


class Improvement(BaseModel):
    priority: str = Field(pattern=r"^(High|Medium|Low)$")
    impact: str