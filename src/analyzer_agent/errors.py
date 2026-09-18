class AnalysisError(Exception):
    pass


class InvalidJSONError(AnalysisError):
    pass


class AnalysisValidationError(AnalysisError):
    pass


class ResumeTooLargeError(AnalysisError):
    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(f"Resume text exceeds the {limit}-char limit ({size} chars)")


class EmptyResumeError(AnalysisError):
    pass