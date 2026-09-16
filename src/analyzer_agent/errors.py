class AnalysisError(Exception):
    pass


class InvalidJSONError(AnalysisError):
    pass


class AnalysisValidationError(AnalysisError):
    pass