from pydantic import BaseModel

class ATSKeywords(BaseModel):
    technical_skills: list[str]
    tools_and_technologies: list[str]
    professional_skills: list[str]
    ai_data_keywords: list[str]