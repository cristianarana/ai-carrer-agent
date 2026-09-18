from ..interfaces.ai_analyzer_response import CVAnalysis
from . import (
    ats_keywords_rules,
    best_fit_job_position_rules,
    candidate_profile_rules,
    how_to_reach_10_rules,
    resume_score_rules,
    ten_second_recruiter_test_rules,
)


class CVAnalysisValidator:

    @staticmethod
    def validate(analysis: CVAnalysis) -> None:
        candidate_profile_rules.validate(analysis.CANDIDATE_PROFILE)
        report = analysis.RECRUITMENT_REPORT
        best_fit_job_position_rules.validate(report.BEST_FIT_JOB_POSITIONS)
        ats_keywords_rules.validate(report.ATS_KEYWORDS)
        ten_second_recruiter_test_rules.validate(report.TEN_SECOND_RECRUITER_TEST)
        resume_score_rules.validate(report.RESUME_SCORE)
        how_to_reach_10_rules.validate(report.HOW_TO_REACH_10)
