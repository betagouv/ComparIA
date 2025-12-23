import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from backend.session import CohortRequest, store_cohorts_redis

logger = logging.getLogger("languia")

app = FastAPI()

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


@app.post("/cohorts", response_class=JSONResponse)
async def define_current_cohorts(request: CohortRequest):
    """
    Route pour définir les cohortes pour une session.

    Args:
        request: La requête FastAPI
        session_hash: Identifiant unique de la session
        cohorts: liste de noms de cohorte comma separated

    Returns:
        JSONResponse: Statut du suivi de cohorte
    """
    logger.info(
        f"[COHORT] Received cohort request: session_hash={request.session_hash}, cohorts={request.cohorts}"
    )

    if not request.session_hash:
        logger.warning("[COHORT] Missing session_hash in request")
        return JSONResponse(
            {
                "success": False,
                "error": "session_hash is required",
                "tracking_info": None,
            },
            status_code=400,
        )

    if request.cohorts:
        cohorts_comma_separated: str = request.cohorts
        success = store_cohorts_redis(request.session_hash, cohorts_comma_separated)
        logger.info(
            f"[COHORT] Stored in Redis: success={success}, session_hash={request.session_hash}, cohorts={cohorts_comma_separated}"
        )
    else:
        logger.warning(
            f"[COHORT] Empty cohorts received for session_hash={request.session_hash}"
        )
        success = False
        cohorts_comma_separated = ""

    return JSONResponse(
        {
            "success": success,
            "session_hash": request.session_hash,
            "tracking_info": cohorts_comma_separated,
        }
    )


@app.post("/frontend_logs", response_class=JSONResponse)
async def frontlog(request: Request):
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


app = SentryAsgiMiddleware(app)
