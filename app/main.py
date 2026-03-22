from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import init_db
from app.api import webhooks, events, deliveries


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Webhook Platform",
    description=(
        "Multi-tenant webhook delivery platform with event ingestion, "
        "fan-out delivery, retry with exponential backoff + jitter, "
        "dead letter queue, and HMAC-SHA256 payload signing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(events.router)
app.include_router(deliveries.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Webhook Platform",
        "version": "1.0.0",
        "docs": "/docs",
    }
