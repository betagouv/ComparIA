from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.arena.router import router as arena_router
from backend.config import settings
from backend.llms.router import router as models_router
from backend.logger import configure_logger, configure_uvicorn_logging
from backend.sentry import init_sentry
from backend.utils.countries import get_vote_count

app = FastAPI()

logger = configure_logger()
configure_uvicorn_logging()
# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)

logger.info("[startup] init_sentry")
init_sentry()
logger.info("[startup] init_sentry done")

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8008",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("[startup] Instrumentator")
# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
logger.info("[startup] Instrumentator done")

logger.info("[startup] include_router models")
app.include_router(models_router)
logger.info("[startup] include_router arena")
app.include_router(arena_router)
logger.info("[startup] routers done")


@app.get("/counter")
async def get_counter():
    return {
        "count": await get_vote_count(),
        "objective": settings.VOTES_OBJECTIVE,
    }
