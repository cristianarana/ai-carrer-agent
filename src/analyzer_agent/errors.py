class AnalysisError(Exception):
    pass


class InvalidJSONError(AnalysisError):
    pass


class AnalysisValidationError(AnalysisError):
    pass


class AnalysisProviderError(AnalysisError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        transient: bool = False,
        retry_after: float | None = None,
    ) -> None:
        self.status_code = status_code
        self.transient = transient
        self.retry_after = retry_after
        super().__init__(message)


class ResumeTooLargeError(AnalysisError):
    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(f"Resume text exceeds the {limit}-char limit ({size} chars)")


class EmptyResumeError(AnalysisError):
    pass