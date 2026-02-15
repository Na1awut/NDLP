"""
Chat Models — Request/Response schemas for API endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import EVCState, EmotionFeatures, EVCForces


# ──────────────────────────────────────────────
# Chat Request / Response
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """POST /evc/process request body"""
    user_id: str = Field(..., description="User ID (platform-linked)")
    platform: str = Field("web", description="line | discord | web")
    message: str = Field(..., description="User message text")


class ChatResponse(BaseModel):
    """POST /evc/process response"""
    response: str = Field(..., description="Bot reply text")
    evc_state: Optional[dict] = Field(None, description="Current EVC state summary")
    alert_triggered: bool = Field(False, description="Was crisis alert triggered?")
    debug: Optional[dict] = Field(None, description="Debug info (dev only)")


class EVCStateResponse(BaseModel):
    """GET /evc/state response"""
    user_id: str
    E: float
    zone: str
    phase: str
    delta_E: float
    turn: int
    flags: dict
    timestamp: str


class HealthResponse(BaseModel):
    """GET /health response"""
    status: str = "ok"
    service: str = "carebot"
    version: str = "0.1.0"
    llm_provider: Optional[str] = None
