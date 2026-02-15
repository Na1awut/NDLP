"""
CareBot FastAPI — Main Application (Minimal for Docker test)
Full implementation will be done in Phase 2
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CareBot API",
    description="EVC Emotional AI Chatbot for Thai Students",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        "docs": "/docs",
    }
