from pydantic import BaseModel

from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis
from analyzer_agent.interfaces.candidate_profile import CandidateProfile
from job_search_agent.interface.job_match import JobSearchOutcome


class ReportData(BaseModel):
    candidate: CandidateProfile
    analysis: CVAnalysis
    job_search: JobSearchOutcome