"""NutriChef local NLP service (FastAPI). Run: uvicorn app.main:app --port 8000"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db, services
from .config import settings
from .routers import chat, generate, nlp, recipes, users, vision
from .schemas import Health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    services.startup()
    yield
    from .nlp.llm import llm_service

    llm_service.shutdown()


app = FastAPI(
    title="NutriChef NLP API",
    version="1.0.0",
    description="Local recipe search, NLP understanding and generation. No external inference services.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(recipes.router)
app.include_router(nlp.router)
app.include_router(users.router)
app.include_router(generate.router)
app.include_router(chat.router)
app.include_router(vision.router)


@app.get("/api/nlp/health", response_model=Health, tags=["system"])
def health() -> Health:
    comps = dict(services.components)
    status = "ok" if all(v.startswith("ok") or v == "disabled" for v in comps.values()) else "degraded"
    return Health(status=status, recipes=db.recipe_count(), components=comps, offline=True)
