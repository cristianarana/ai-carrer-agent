from pydantic import BaseModel

from .candidate_profile import CandidateProfile
from .recruitment_report import RecruitmentReport


class CVAnalysis(BaseModel):
    CANDIDATE_PROFILE: CandidateProfile
    RECRUITMENT_REPORT: RecruitmentReport