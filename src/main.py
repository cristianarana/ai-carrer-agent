from fastapi import FastAPI

from controller import router as api_router
from core.config import load_settings
from core.exceptions import register_exception_handlers
from core.logging import setup_logging
from middelware.logging import RequestLoggingMiddleware
from services.carrer_agent import CareerAgentService

setup_logging(level=load_settings().log_level)


def create_app(*, career_service: CareerAgentService | None = None) -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="AI Career Agent API",
        description=(
            "Automatiza el análisis de curriculum, la búsqueda de "
            "oportunidades laborales y la generación de un informe PDF."
        ),
        version="0.1.0",
    )
    app.state.career_service = career_service or CareerAgentService(settings=settings)
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api", tags=["pipeline"])
    return app


app = create_app()