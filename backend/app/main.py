"""
RAG Document Assistant — FastAPI entry point.
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models import Base
from app.rag.vectorstore import init_collection

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle events."""
    # ── Startup ──────────────────────────────────────────────
    # Create all PostgreSQL tables
    Base.metadata.create_all(bind=engine)
    # Ensure the Qdrant collection exists
    init_collection()
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    yield
    # ── Shutdown ─────────────────────────────────────────────
    # (nothing to clean up for now)


app = FastAPI(
    title="RAG Document Assistant",
    description="Upload documents and chat with them using RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
from app.api.documents import router as documents_router  # noqa: E402
from app.api.chat import router as chat_router  # noqa: E402

app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "RAG Document Assistant API is running"}
