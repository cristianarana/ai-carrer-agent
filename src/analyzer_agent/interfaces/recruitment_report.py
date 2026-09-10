from pydantic import BaseModel
from .job_position import JobPosition
from .ats_keywords import ATSKeywords
from .recruiter_10_sec_test import Recruiter10SecondTest
from .resume_score import ResumeScore
from .how_to_reach_10 import HowToReach10

class RecruitmentReport(BaseModel):
    BEST_FIT_JOB_POSITIONS: list[JobPosition]
    ATS_KEYWORDS: ATSKeywords
    TEN_SECOND_RECRUITER_TEST: Recruiter10SecondTest
    RESUME_SCORE: ResumeScore
    HOW_TO_REACH_10: HowToReach10