import re

from analyzer_agent.interfaces.ats_keywords import ATSKeywords
from analyzer_agent.interfaces.job_position import JobPosition
from job_search_agent.interface.job_opportunity import JobOpportunity
from .match_scorer import MatchScorer


class KeywordScorer:
    _CATEGORY_WEIGHTS = {
        "technical_skills": 1.0,
        "tools_and_technologies": 0.8,
        "ai_data_keywords": 1.0,
        "professional_skills": 0.6,
    }

    _FIELD_WEIGHTS = {
        "title": 1.0,
        "requirements": 1.0,
        "description": 1.0,
        "company": 0.0,
        "location": 0.0,
    }

    _TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.\-]*")

    def score(
        self, *, job: JobOpportunity, position: JobPosition, keywords: ATSKeywords
    ) -> float:
        return 0.65 * self._keyword_match(job, keywords) + 0.35 * self._rank_match(position)

    def _keyword_match(self, job: JobOpportunity, keywords: ATSKeywords) -> float:
        fields = self._tokenized_fields(job)
        found = total = 0.0
        for category, cat_weight in self._CATEGORY_WEIGHTS.items():
            for keyword in getattr(keywords, category):
                total += cat_weight
                found += cat_weight * self._best_field_weight(keyword, fields)
        return found / total if total else 0.0

    @classmethod
    def _tokenized_fields(cls, job: JobOpportunity) -> dict[str, list[list[str]]]:
        return {
            "title": [cls._tokenize(job.title)],
            "company": [cls._tokenize(job.company)],
            "location": [cls._tokenize(job.location)],
            "requirements": [cls._tokenize(r) for r in job.requirements],
            "description": [cls._tokenize(job.description)],
        }

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        return cls._TOKEN_RE.findall(text.lower())

    @classmethod
    def _best_field_weight(cls, keyword: str, fields) -> float:
        ktokens = cls._tokenize(keyword)
        if not ktokens:
            return 0.0
        best = 0.0
        for field, weight in cls._FIELD_WEIGHTS.items():
            if weight > 0.0 and cls._in_sequences(ktokens, fields[field]):
                best = max(best, weight)
        return best

    @classmethod
    def _in_sequences(cls, ktokens: list[str], sequences: list[list[str]]) -> bool:
        single = len(ktokens) == 1
        found_phrase = False
        for seq in sequences:
            if single:
                if ktokens[0] in seq:
                    return True
            elif cls._is_phrase(ktokens, seq):
                found_phrase = True

        pool = set()
        for seq in sequences:
            pool.update(seq)
        return found_phrase or all(k in pool for k in ktokens)

    @staticmethod
    def _is_phrase(ktokens: list[str], seq: list[str]) -> bool:
        n = len(ktokens)
        return any(seq[i : i + n] == ktokens for i in range(len(seq) - n + 1))

    @staticmethod
    def _rank_match(position: JobPosition) -> float:
        return (21 - position.rank) / 20