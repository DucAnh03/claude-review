"""
FastAPI backend for the Code Review system.

Run from project root:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db as database

from .api import devs, health, repos, reviews, skills, stats
from .core.config import ALLOWED_ORIGINS
from .core.jobs import job_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    job_manager.start()
    print(f"[backend] Started. Allowed origins: {ALLOWED_ORIGINS}")
    yield


app = FastAPI(
    title="Code Review API",
    version="1.0.0",
    description="Backend for Slack/Vercel code review tool. Wraps Claude Code CLI + git.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public
app.include_router(health.router)

# Auth-protected (Bearer token)
app.include_router(repos.router)
app.include_router(devs.router)
app.include_router(reviews.router)
app.include_router(skills.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {
        "service": "Code Review API",
        "docs":    "/docs",
        "health":  "/api/health",
    }
