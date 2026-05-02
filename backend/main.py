from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.arena.router import router as arena_router
from backend.tool_arena.auth import prewarm_all_oauth_providers
from backend.tool_arena.registry import registry
from backend.tool_arena.router import router as tool_arena_router
from backend.config import OBJECTIVES
from backend.llms.router import router as models_router
from backend.logger import configure_logger, configure_uvicorn_logging
from backend.cors_utils import build_origins, get_origins
from backend.sentry import init_sentry
from backend.utils.countries import CountryPortalAnno, get_country_portal_count


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm OAuth providers so the first user request to /tool-arena/compare
    # doesn't pay the cold-start cost (metadata discovery + token refresh +
    # MCP session init). This is the root cause of "first call fails, then
    # works" reports against the Clarifeye tool.
    await prewarm_all_oauth_providers(
        [registry.get_server(sid) for sid in registry.server_ids]
    )
    yield


app = FastAPI(lifespan=lifespan)

logger = configure_logger()
configure_uvicorn_logging()
# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)

init_sentry()


origins = get_origins()

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
app.include_router(tool_arena_router)


@app.get("/counter")
async def get_counter(country_portal: CountryPortalAnno):
    return {
        "count": get_country_portal_count(country_portal),
        "objective": OBJECTIVES[country_portal],
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
