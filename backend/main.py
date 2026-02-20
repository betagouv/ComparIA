from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.arena.router import router as arena_router
from backend.config import OBJECTIVES
from backend.llms.router import router as models_router
from backend.logger import configure_logger, configure_uvicorn_logging
from backend.sentry import init_sentry
from backend.utils.countries import CountryPortalAnno, get_country_portal_count

app = FastAPI()

logger = configure_logger()
configure_uvicorn_logging()
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
async def get_counter(country_portal: CountryPortalAnno):
    return {
        "count": get_country_portal_count(country_portal),
        "objective": OBJECTIVES[country_portal],
    }
