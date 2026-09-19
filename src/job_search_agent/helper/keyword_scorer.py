import re
from typing import Any

from analyzer_agent.interfaces.ats_keywords import ATSKeywords
from analyzer_agent.interfaces.job_position import JobPosition
from core.config import Settings, load_settings
from job_search_agent.interface.job_opportunity import JobOpportunity
from .match_scorer import MatchScorer

_FieldWeights = dict[str, float]


class KeywordScorer:
    _CATEGORY_ORDER = (
        "technical_skills",
        "tools_and_technologies",
        "ai_data_keywords",
        "professional_skills",
    )
    _FIELD_ORDER = ("title", "requirements", "description")

    _CATEGORY_WEIGHTS: dict[str, float] = {
        "technical_skills": 1.0,
        "tools_and_technologies": 0.8,
        "ai_data_keywords": 1.0,
        "professional_skills": 0.6,
    }

    _FIELD_WEIGHTS: dict[str, float] = {
        "title": 1.0,
        "requirements": 1.0,
        "description": 1.0,
        "company": 0.0,
        "location": 0.0,
    }

    _MAX_RANK = 20

    _TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.\-]*")

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        category_weights: dict[str, float] | list[float] | None = None,
        field_weights: dict[str, float] | list[float] | None = None,
        keyword_weight: float | None = None,
        rank_weight: float | None = None,
        max_rank: int | None = None,
    ) -> None:
        cfg = settings or load_settings()
        self._category_weights = self._build_category_weights(
            category_weights if category_weights is not None else cfg.search_category_weights
        )
        self._field_weights = self._build_field_weights(
            field_weights if field_weights is not None else cfg.search_field_weights
        )
        self._keyword_weight = (
            keyword_weight
            if keyword_weight is not None
            else cfg.search_keyword_weight
        )
        self._rank_weight = (
            rank_weight if rank_weight is not None else cfg.search_rank_weight
        )
        self._max_rank = max_rank if max_rank is not None else cfg.search_max_rank

    def _build_category_weights(
        self, value: dict[str, float] | list[float] | None
    ) -> dict[str, float]:
        if isinstance(value, dict):
            return {name: float(weight) for name, weight in value.items()}
        weights = list(value or [])
        return {
            name: (
                float(weights[i])
                if i < len(weights)
                else self._CATEGORY_WEIGHTS.get(name, 0.0)
            )
            for i, name in enumerate(self._CATEGORY_ORDER)
        }

    def _build_field_weights(
        self, value: dict[str, float] | list[float] | None
    ) -> dict[str, float]:
        result = dict(self._FIELD_WEIGHTS)
        if isinstance(value, dict):
            result.update({name: float(weight) for name, weight in value.items()})
            return result
        weights = list(value or [])
        for i, name in enumerate(self._FIELD_ORDER):
            result[name] = (
                float(weights[i]) if i < len(weights) else self._FIELD_WEIGHTS[name]
            )
        return result

    def score(
        self, *, job: JobOpportunity, position: JobPosition, keywords: ATSKeywords
    ) -> float:
        return self._keyword_weight * self._keyword_match(
            job, keywords
        ) + self._rank_weight * self._rank_value(position)

    def _rank_value(self, position: JobPosition) -> float:
        if self._max_rank <= 0:
            return 0.0
        return (1 + self._max_rank - position.rank) / self._max_rank

    def _keyword_match(self, job: JobOpportunity, keywords: ATSKeywords) -> float:
        fields = self._tokenized_fields(job)
        found = total = 0.0
        for category, cat_weight in self._category_weights.items():
            for keyword in getattr(keywords, category):
                total += cat_weight
                found += cat_weight * self._best_with(
                    self._field_weights, keyword, fields
                )
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
    def _best_field_weight(
        cls, keyword: str, fields: dict[str, list[list[str]]]
    ) -> float:
        return cls._best_with(cls._FIELD_WEIGHTS, keyword, fields)

    @classmethod
    def _best_with(
        cls,
        field_weights: _FieldWeights,
        keyword: str,
        fields: dict[str, list[list[str]]],
    ) -> float:
        ktokens = cls._tokenize(keyword)
        if not ktokens:
            return 0.0
        best = 0.0
        for field, weight in field_weights.items():
            if weight > 0.0 and cls._in_sequences(ktokens, fields[field]):
                best = max(best, weight)
        return best

    @classmethod
    def _rank_match(cls, position: JobPosition) -> float:
        rank = cls._MAX_RANK if cls._MAX_RANK > 0 else 20
        return (1 + rank - position.rank) / rank

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