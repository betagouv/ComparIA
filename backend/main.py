import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from backend.utils.countries import get_country_portal, get_country_portal_count

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
    country_portal = get_country_portal(c)

    return {
        "count": get_country_portal_count(country_portal),
        "objective": OBJECTIVES[country_portal],
    }


@app.post("/frontend_logs")
async def frontend_logs(request: Request):
    """
    Route pour recevoir les logs du frontend (format simplifié).

    Args:
        request: La requête HTTP pour obtenir l'IP client

    Returns:
        JSONResponse: Statut de réception du log
    """
    from backend.logger import FrontendLogRequest

    try:
        body = await request.json()
        log_request = FrontendLogRequest(**body)

        client_ip = request.client.host if request.client else "unknown"

        # Créer un logger pour le frontend
        frontend_logger = logging.getLogger("frontend")

        # Map frontend log level to Python logging levels
        level_map = {
            "debug": frontend_logger.debug,
            "info": frontend_logger.info,
            "warn": frontend_logger.warning,
            "warning": frontend_logger.warning,
            "error": frontend_logger.error,
        }

        log_func = level_map.get(log_request.level.lower(), frontend_logger.info)

        # Données supplémentaires pour le log
        extra_data = {
            "session_hash": log_request.session_hash,
            "client_ip": client_ip,
            "user_agent": log_request.user_agent,
        }

        # Loguer le message avec les métadonnées
        log_func(log_request.message, extra=extra_data)

        return JSONResponse(
            {
                "success": True,
                "log_received": True,
                "session_hash": log_request.session_hash,
            }
        )

    except Exception as e:
        logger.error(f"Error receiving frontend log: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process frontend log: {str(e)}"
        )


# FIXME remove? https://github.com/getsentry/sentry-python/issues/4003
app = SentryAsgiMiddleware(app)
