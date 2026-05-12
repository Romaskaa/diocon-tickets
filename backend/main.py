import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.logging import configure_logging
from src.core.redis import redis_client
from src.core.settings import settings
from src.crm.router import router as counterparty_router
from src.iam.routers import router as iam_router
from src.media.router import router as media_router
from src.products.router import router as product_router
from src.projects.router import router as project_router
from src.proofreading.router import router as proofreading_router
from src.shared.domain.exceptions import AppError
from src.shared.infra.middlewares import LoggingMiddleware
from src.shared.utils.cli import run_cli_command
from src.tickets.router import router as tickets_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Настройка логирования
    configure_logging(log_level="INFO")

    # Проверка доступности Redis
    await redis_client.ping()

    # Выполнение необходимых команд для запуска приложения
    await run_cli_command(sys.executable, "-m", "alembic", "upgrade", "head")
    await run_cli_command(sys.executable, "-m", "cli", "create-first-admin")
    await run_cli_command(sys.executable, "-m", "cli", "init-s3-buckets")
    yield


app = FastAPI(
    title="Ticket management system",
    description="REST API тикет-системы компании **ДИО-Консалт**",
    version="0.1.0",
    lifespan=lifespan,
)

# Prometheus мониторинг
Instrumentator(
    should_group_status_codes=True,
    should_group_untemplated=True,
    excluded_handlers=["/health", "/metrics"]
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

router = APIRouter(prefix="/api/v1")

router.include_router(iam_router)
router.include_router(counterparty_router)
router.include_router(media_router)
router.include_router(tickets_router)
router.include_router(proofreading_router)
router.include_router(product_router)
router.include_router(project_router)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)


@app.exception_handler(ValueError)
def value_exception_handler(request: Request, exc: ValueError) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "status": status.HTTP_400_BAD_REQUEST,
                "details": {},
            }
        }
    )


@app.exception_handler(AppError)
def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "public_message": exc.public_message,
                "status": exc.status_code,
                "details": exc.details,
            }
        }
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=settings.app.port)  # noqa: S104
