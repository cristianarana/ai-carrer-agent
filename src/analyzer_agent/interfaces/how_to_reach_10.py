from pydantic import BaseModel
from .improvement import Improvement

class HowToReach10(BaseModel):
    immediate_actions: list[Improvement]
    technical_enhancements: list[Improvement]
    ats_optimization: list[Improvement]
    professional_and_structural_improvements: list[Improvement]
    long_term_improvements: list[Improvement]