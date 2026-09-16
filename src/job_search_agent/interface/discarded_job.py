from pydantic import BaseModel, Field


class DiscardedJob(BaseModel):
    provider: str
    source_title: str
    reasons: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)