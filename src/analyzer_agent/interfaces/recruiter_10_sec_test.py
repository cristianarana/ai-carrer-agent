from pydantic import BaseModel

class Recruiter10SecondTest(BaseModel):
    positive: list[str]
    unclear_or_weak: list[str]
    could_cause_rejection: list[str]