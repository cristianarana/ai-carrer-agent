from pydantic import BaseModel

class JobPosition(BaseModel):
    position: str
    rank: int
    match_explanation: str