import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.arena.router import router as arena_router
from backend.tool_arena.readiness import (
    get_probe_interval_seconds,
    get_readiness_registry,
    probe_server,
    readiness_probe_loop,
)
from backend.tool_arena.registry import registry
from backend.tool_arena.router import admin_router as tool_arena_admin_router
from backend.tool_arena.router import router as tool_arena_router
from backend.config import OBJECTIVES
from backend.llms.router import router as models_router
from backend.logger import configure_logger, configure_uvicorn_logging
from backend.cors_utils import build_origins, get_origins
from backend.sentry import init_sentry
from backend.utils.countries import CountryPortalAnno, get_country_portal_count

# Cap the initial blocking probe so a slow upstream cannot wedge Railway
# health-checks at startup. Individual probes still have their own per-server
# timeout (10s default inside ``probe_server``), so 30s is enough headroom for
# 2-3 sequential failures while staying well under the platform health budget.
_INITIAL_PROBE_BUDGET_SECONDS = 30.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2: replace the OAuth pre-warm with the readiness probe. The probe
    # runs the same handshake (token refresh + MCP initialize) but also
    # records the result in the ReadinessRegistry. Running both would just
    # double-refresh tokens for no extra signal.
    servers = [registry.get_server(sid) for sid in registry.server_ids]
    readiness = get_readiness_registry()

    try:
        await asyncio.wait_for(
            asyncio.gather(
                *(probe_server(s, readiness) for s in servers),
                return_exceptions=True,
            ),
            timeout=_INITIAL_PROBE_BUDGET_SECONDS,
        )
    except asyncio.TimeoutError:
        # Hitting the budget is fine — servers that did not respond stay in
        # whatever state they were in (likely UNKNOWN, which the dispatcher
        # treats as not ready). The background loop will retry shortly.
        pass

    # Background re-probe loop. Stored on app.state so shutdown can cancel.
    interval = get_probe_interval_seconds()
    app.state.readiness_task = asyncio.create_task(
        readiness_probe_loop(servers, interval_seconds=interval)
    )

    try:
        yield
    finally:
        task: asyncio.Task | None = getattr(app.state, "readiness_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass


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
app.include_router(tool_arena_admin_router)


@app.get("/counter")
async def get_counter(country_portal: CountryPortalAnno):
    return {
        "count": get_country_portal_count(country_portal),
        "objective": OBJECTIVES[country_portal],
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
