import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from backend.arena.router import router as arena_router
from backend.config import OBJECTIVES, settings
from backend.language_models.router import router as models_router
from backend.logger import (
    configure_frontend_logger,
    configure_logger,
    configure_uvicorn_logging,
)
from backend.sentry import init_sentry
from backend.utils.countries import get_country_code, get_country_portal_count

app = FastAPI()

logger = configure_logger()
configure_uvicorn_logging()
configure_frontend_logger()
# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)

init_sentry()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router)
app.include_router(arena_router)


@app.get("/counter")
async def get_counter(c: str | None = None):
    country_code = get_country_code(c)

    return {
        "count": get_country_portal_count(country_code),
        "objective": OBJECTIVES[country_code],
    }


# FIXME remove? https://github.com/getsentry/sentry-python/issues/4003
app = SentryAsgiMiddleware(app)
