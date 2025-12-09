from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

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

app = SentryAsgiMiddleware(app)
