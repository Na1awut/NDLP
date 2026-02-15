"""
CareBot FastAPI — Main Application

Wires together:
  - EVC Engine (emotion → forces → state update)
  - LLM Client (xAI Grok)
  - Memory Store (In-memory / Cosmos DB)
  - API Routes
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Load .env from project root (carebot/ folder)
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Fix imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.llm_client import LLMClient
from services.memory_store import create_memory_store
from api.routes import evc_routes
from api.routes import auth_routes


# ──────────────────────────────────────────────
# App Lifecycle
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown"""
    # ── Startup ──
    print("🤖 CareBot starting up...")

    # Initialize services
    llm_client = LLMClient()
    memory_store = create_memory_store()

    # Inject into routes
    evc_routes.llm_client = llm_client
    evc_routes.memory_store = memory_store
    auth_routes.memory_store = memory_store

    info = llm_client.get_info()
    print(f"   LLM Provider: {info['provider']}")
    print(f"   Fast Model:   {info['fast_model']}")
    print(f"   Smart Model:  {info['smart_model']}")
    print(f"   API Key:      {'✅' if info['has_key'] else '❌ MISSING'}")
    print(f"   Memory Store: {type(memory_store).__name__}")
    print("🤖 CareBot ready!")

    yield

    # ── Shutdown ──
    print("🤖 CareBot shutting down...")


# ──────────────────────────────────────────────
# Create App
# ──────────────────────────────────────────────
app = FastAPI(
    title="CareBot API",
    description="EVC Emotional AI Chatbot for Thai Students — ดูแลสุขภาพจิตนักเรียน",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
app.include_router(evc_routes.router)
app.include_router(auth_routes.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "carebot",
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    return {
        "message": "🤖 CareBot API — EVC Emotional AI Chatbot",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "process": "POST /evc/process",
            "state": "GET /evc/state/{user_id}",
            "reset": "POST /evc/reset/{user_id}",
        },
    }
