"""Puzzler — FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.database import init_db
from app.routers import auth, puzzle, session, player


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables, then seed the daily puzzle pool."""
    init_db()
    # Seed the puzzle pool so /daily always returns a real puzzle
    from app.database import SessionLocal
    from app.services.puzzle_pool import ensure_daily_puzzle
    db = SessionLocal()
    try:
        ensure_daily_puzzle(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Puzzler API",
    description="AI-powered adaptive puzzle platform — puzzles that learn you.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Vanilla JS frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(puzzle.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(player.router, prefix="/api")


@app.get("/health", tags=["meta"])
def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0", "service": "puzzler-api"}


@app.get("/", tags=["meta"])
def root():
    return {"message": "Welcome to Puzzler API. Visit /docs for interactive documentation."}
