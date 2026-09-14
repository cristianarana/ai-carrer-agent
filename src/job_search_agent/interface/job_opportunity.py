from pydantic import BaseModel, field_validator


class JobOpportunity(BaseModel):
    title: str
    description: str
    requirements: list[str]
    location: str
    company: str
    salary_range: str | None = None
    employment_type: str | None = None
    posted_date: str | None = None
    company_url: str | None = None
    apply_url: str | None = None

    _REQUIRED_NON_EMPTY = ("title", "description", "location", "company")

    @field_validator(*_REQUIRED_NON_EMPTY, mode="before")
    @classmethod
    def _strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator(*_REQUIRED_NON_EMPTY, mode="after")
    @classmethod
    def _not_empty(cls, value):
        if not value:
            raise ValueError("cannot be empty")
        return value

    @field_validator("requirements", mode="before")
    @classmethod
    def _coerce_requirements(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            raise ValueError("requirements must be a list of strings")
        return value

    @field_validator("company_url", "apply_url", mode="after")
    @classmethod
    def _valid_url(cls, value):
        if value is None:
            return None
        if not value:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("must be a valid http(s) URL")
        return value