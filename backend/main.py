from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from backend.statistics import router as statistics_router
from backend.suggestions.router import router as suggestions_router
from backend.utils.countries import get_vote_count
from backend.vote_tags.router import router as vote_tags_router
from utils.database.settings import get_app_settings
from utils.storage.redis import get_maintenance_mode


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.COMPARIA_DB_URI and settings.ADMIN_EMAILS:
        from utils.database.actions.seed import seed_admins

        await seed_admins()

    if settings.COMPARIA_DB_URI:
        from backend import publishing

        publishing.start(app)
        try:
            yield
        finally:
            await publishing.stop(app)
    else:
        yield


app = FastAPI(lifespan=lifespan)

logger = configure_logger()
configure_uvicorn_logging()
# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)

init_sentry()


# Deployments serve front and API from one origin through Caddy, so the extra
# dev origins are only needed when running the front separately in debug mode.
origins = [settings.COMPARIA_APP_URL, *settings.COMPARIA_CORS_ORIGINS]
if settings.LANGUIA_DEBUG:
    origins += [
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


# Blocks normal traffic while maintenance mode is on. Registered after
# auth/anonymous (see ordering note below) so it wraps them and short-circuits
# before any session/auth lookups run.
MAINTENANCE_EXEMPT_PATHS = {"/maintenance/status", "/metrics"}


async def maintenance_middleware(request: Request, call_next):
    if request.url.path not in MAINTENANCE_EXEMPT_PATHS and get_maintenance_mode():
        return JSONResponse(
            {"detail": "Service temporarily unavailable for maintenance"},
            status_code=503,
        )
    return await call_next(request)


app.middleware("http")(maintenance_middleware)

# Registered after auth/anonymous/maintenance so it wraps them (Starlette builds
# the stack with the last-registered middleware outermost), otherwise auth_middleware
# short-circuits CORS preflight/401 responses before CORS headers are added.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["content-type"],
)


# Registered last so it wraps every other middleware, including CORS: the
# headers must show up on every response, errors and 401s/503s included.
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    # setdefault, not assignment: a route serving untrusted bytes can set a
    # stricter policy of its own and keep it (see GET /auth/config/logo).
    response.headers.setdefault(
        "Content-Security-Policy",
        "frame-ancestors 'none'; form-action 'none'; base-uri 'none'",
    )
    # This is the API, not a browser client: uvicorn isn't started with
    # --proxy-headers, so request.url.scheme stays "http" behind Caddy and
    # X-Forwarded-Proto is the only way to know the original request was TLS.
    is_https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    if is_https:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
    return response


app.middleware("http")(security_headers_middleware)


def _verify_metrics_token(request: Request) -> None:
    # No-op when METRICS_TOKEN is unset, keeping /metrics open like before.
    token = settings.METRICS_TOKEN
    if not token:
        return
    if request.headers.get("authorization") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", dependencies=[Depends(_verify_metrics_token)]
)

app.include_router(models_router)
app.include_router(suggestions_router)
app.include_router(vote_tags_router)
app.include_router(arena_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(settings_router)
app.include_router(statistics_router)


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
