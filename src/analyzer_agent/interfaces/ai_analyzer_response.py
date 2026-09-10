from pydantic import BaseModel, Field
from .recruitment_report import RecruitmentReport

class CVAnalysis(BaseModel):
    RECRUITMENT_REPORT: RecruitmentReport

