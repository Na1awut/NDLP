"""
EVC Models — Pydantic schemas for the Emotional Vector Control system
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class EmotionalZone(str, Enum):
    """Emotional zone classification based on E value"""
    EXTREME_NEGATIVE = "ExtremeNegative"   # E ≤ -6
    NEGATIVE = "Negative"                   # -6 < E ≤ -2
    NEUTRAL = "Neutral"                     # -2 < E ≤ 2
    POSITIVE = "Positive"                   # 2 < E ≤ 6
    OVERHEAT_POSITIVE = "OverheatPositive"  # E > 6


class EmotionalPhase(str, Enum):
    """Phase classification based on ΔE"""
    CRASH_RECOVERY = "CrashRecovery"  # E ≤ -6 and rising
    DECLINING = "Declining"           # ΔE < -0.5
    STABLE = "Stable"                 # -0.5 ≤ ΔE ≤ 0.5
    RISING = "Rising"                 # ΔE > 0.5
    PEAK = "Peak"                     # E > 6 and declining


class Intent(str, Enum):
    """User intent classification"""
    GREETING = "greeting"
    VENTING = "venting"
    SEEKING_HELP = "seeking_help"
    PRAISE = "praise"
    APOLOGY = "apology"
    SARCASM = "sarcasm"
    AGGRESSION = "aggression"
    NEUTRAL = "neutral"
    FAREWELL = "farewell"


# ──────────────────────────────────────────────
# Emotion Features (output from emotion extractor)
# ──────────────────────────────────────────────

class EmotionFeatures(BaseModel):
    """Emotion features extracted from user text"""
    valence: float = Field(0.0, ge=-1.0, le=1.0, description="ขั้วอารมณ์: -1 (ลบ) ถึง +1 (บวก)")
    arousal: float = Field(0.5, ge=0.0, le=1.0, description="ระดับตื่นตัว: 0 (สงบ) ถึง 1 (ตื่นเต้น)")
    dominance: float = Field(0.5, ge=0.0, le=1.0, description="ระดับควบคุม: 0 (ยอมจำนน) ถึง 1 (ควบคุม)")
    intent: Intent = Field(Intent.NEUTRAL, description="จุดประสงค์ของข้อความ")
    sarcasm_prob: float = Field(0.0, ge=0.0, le=1.0, description="ความน่าจะเป็นของการประชด")
    support_need: float = Field(0.5, ge=0.0, le=1.0, description="ความต้องการการสนับสนุน")
    uncertainty: float = Field(0.3, ge=0.0, le=1.0, description="ความไม่แน่ใจ")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="ความมั่นใจของการสกัด")


# ──────────────────────────────────────────────
# EVC Flags
# ──────────────────────────────────────────────

class EVCFlags(BaseModel):
    """Boolean flags for special emotional states"""
    sarcasm: bool = False
    anger: bool = False
    anxiety: bool = False
    stress: bool = False
    crisis: bool = False
    boundary_setting: bool = False
    mood_swing: bool = False


# ──────────────────────────────────────────────
# EVC Forces
# ──────────────────────────────────────────────

class EVCForces(BaseModel):
    """Computed EVC forces"""
    S: float = Field(0.0, description="Support Force (แรงยก)")
    D: float = Field(0.0, description="Drag Force (แรงฉุด)")
    K: float = Field(1.0, description="Sensitivity (ตัวคูณ)")


# ──────────────────────────────────────────────
# EVC State
# ──────────────────────────────────────────────

class EVCState(BaseModel):
    """Complete EVC state for one conversation turn"""
    E: float = Field(0.0, ge=-10.0, le=10.0, description="Emotional Energy")
    E_prev: float = Field(0.0, ge=-10.0, le=10.0, description="Previous Emotional Energy")
    delta_E: float = Field(0.0, description="Change in E")
    E_target: float = Field(0.0, ge=-10.0, le=10.0, description="Target Energy")

    I: float = Field(0.3, ge=0.0, le=1.0, description="Inertia")
    M: float = Field(0.05, ge=0.0, le=1.0, description="Memory Decay")

    zone: EmotionalZone = Field(EmotionalZone.NEUTRAL)
    phase: EmotionalPhase = Field(EmotionalPhase.STABLE)
    flags: EVCFlags = Field(default_factory=EVCFlags)

    turn: int = Field(0, description="Conversation turn number")
    timestamp: datetime = Field(default_factory=datetime.now)

    # History for adaptive inertia
    delta_history: list[float] = Field(default_factory=list, description="Recent ΔE values")

    # EVC v4: Hormonal model state
    hormone_levels: dict[str, float] = Field(default_factory=dict, description="Hormone levels for cocktail persistence")
    bot_E: float = Field(0.0, description="Bot emotional state (for mirroring)")
    bot_pacing_turns: int = Field(0, description="Bot pacing turn count")
    bot_negative_streak: int = Field(0, description="User negative streak for bot mirroring")
    dominant_state: str = Field("neutral", description="Dominant emotional state label")


# ──────────────────────────────────────────────
# EVC Processing Result
# ──────────────────────────────────────────────

class EVCResult(BaseModel):
    """Complete result of EVC processing pipeline"""
    state: EVCState
    emotion: EmotionFeatures
    forces: EVCForces
    response_policy: str = ""
    therapeutic_note: str = ""
    alert_triggered: bool = False
