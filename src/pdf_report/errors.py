class ReportError(Exception):
    pass


class MissingReportDataError(ReportError):
    pass


class InvalidOutputPathError(ReportError):
    pass


class PDFRenderError(ReportError):
    pass


class InvalidPDFOutputError(ReportError):
    pass