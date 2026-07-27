from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.admin.router import router as admin_router
from backend.arena.router import router as arena_router
from backend.auth.middleware import anonymous_middleware, auth_middleware
from backend.auth.router import router as auth_router
from backend.config import settings
from backend.llms.router import router as models_router
from backend.logger import configure_logger, configure_uvicorn_logging
from backend.sentry import init_sentry
from backend.settings.router import router as settings_router
from backend.utils.countries import get_vote_count
from utils.database.settings import get_app_settings
from utils.storage.redis import get_maintenance_mode


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.COMPARIA_DB_URI and settings.ADMIN_EMAILS:
        from utils.database.actions.seed import seed_admins

        await seed_admins()
    yield


app = FastAPI(lifespan=lifespan)

logger = configure_logger()
configure_uvicorn_logging()
# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)

init_sentry()


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

app.middleware("http")(auth_middleware)
app.middleware("http")(anonymous_middleware)

# Registered last so it wraps the auth/anonymous middlewares (Starlette builds
# the stack with the last-registered middleware outermost), otherwise auth_middleware
# short-circuits CORS preflight/401 responses before CORS headers are added.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(models_router)
app.include_router(arena_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(settings_router)


@app.get("/counter")
async def get_counter():
    app_settings = await get_app_settings()
    return {
        "count": await get_vote_count(),
        "objective": app_settings.votes_objective,
    }


@app.get("/maintenance/status")
async def maintenance_status():
    return {"enabled": get_maintenance_mode()}
