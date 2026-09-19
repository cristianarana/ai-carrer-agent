import io
import logging
from pathlib import Path

from .errors import FileReadError, FileTooLargeError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def get_extension(filename: str | None) -> str:
    if not filename:
        raise UnsupportedFileTypeError("El archivo subido no tiene nombre.")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Tipo de archivo no permitido: '{ext or 'desconocido'}'. "
            f"Permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    return ext


def check_size(content: bytes, max_bytes: int) -> None:
    if len(content) > max_bytes:
        raise FileTooLargeError(
            f"El archivo excede el límite de {max_bytes} bytes ({len(content)} bytes)."
        )


def extract_resume_text(*, filename: str, content: bytes) -> str:
    ext = get_extension(filename)
    try:
        if ext == ".pdf":
            return _extract_pdf(content)
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FileReadError("El archivo de texto no pudo decodificarse como UTF-8.") from exc
    except Exception as exc:
        logger.exception("Failed to read resume file %s", filename)
        raise FileReadError(f"No se pudo leer el archivo del curriculum: {exc}") from exc


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    parts = [page.extract_text() for page in reader.pages]
    return "\n".join(part or "" for part in parts)