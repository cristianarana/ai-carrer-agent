from pydantic import BaseModel, field_validator


class CandidateProfile(BaseModel):
    name: str | None = None
    professional_title: str | None = None

    @field_validator("name", "professional_title", mode="before")
    @classmethod
    def _strip_or_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value