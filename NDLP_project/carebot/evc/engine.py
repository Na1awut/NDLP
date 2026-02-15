"""
EVC Engine v4 — Hormonal Emotional Model

สมการหลัก: เปลี่ยนจาก single E เป็น Hormone Cocktail

Pipeline:
  1. Restore hormone cocktail + bot state จาก previous state
  2. Update cocktail ด้วย EmotionFeatures
  3. Compute E_composite จาก cocktail
  4. Compute forces (S, D, K) — backward compatible
  5. Update bot mirroring (Pacing & Leading)
  6. Classify zone & phase
  7. Update flags
  8. Return new state + forces

Backward Compatible:
  - ยังคืน E, zone, phase, delta_E เหมือน v3
  - เพิ่ม hormone_levels, bot_E, dominant_state
"""
import math
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import (
    EVCState, EmotionFeatures, EVCForces, EVCFlags,
    EmotionalZone, EmotionalPhase
)
from evc.hormones.cocktail import HormoneCocktail
from evc.hormones.definitions import create_all_hormones
from evc.mirroring import BotEmotionalState
from evc.scoring import compute_forces
from evc.rules import classify_zone, classify_phase, update_flags
from evc.therapeutic import apply_therapeutic_bias, get_therapeutic_note


# ──────────────────────────────────────────────
# Constants (kept for backward compatibility)
# ──────────────────────────────────────────────
MAX_DELTA = 3.0
DELTA_HISTORY_SIZE = 5


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


# ──────────────────────────────────────────────
# Core EVC v4 Update
# ──────────────────────────────────────────────
def update_evc(
    current_state: EVCState,
    emotion: EmotionFeatures,
    current_time: datetime | None = None,
) -> tuple[EVCState, EVCForces]:
    """
    Update EVC state using Hormonal Model v4.

    Returns: (new_state, forces)
    """
    if current_time is None:
        current_time = datetime.now()

    E_prev = current_state.E

    # ── Step 1: Restore hormone cocktail ──
    cocktail = HormoneCocktail()
    if current_state.hormone_levels:
        cocktail.restore_levels(current_state.hormone_levels)

    # ── Step 2: Update cocktail with emotion ──
    cocktail.update(emotion)

    # ── Step 3: Compute E from cocktail ──
    E_hormonal = cocktail.compute_E()

    # ── Step 4: Compute forces (backward compatible) ──
    forces = compute_forces(emotion, current_state)

    # ── Step 5: Apply therapeutic bias ──
    S_biased = apply_therapeutic_bias(forces.S, E_prev)
    forces_biased = EVCForces(S=round(S_biased, 4), D=forces.D, K=forces.K)

    # ── Step 6: Blend hormonal E with forces-based E ──
    # E_target from forces (v3 equation for compatibility)
    E_target_forces = clamp(forces.K * (S_biased - forces.D) * 10, -10.0, 10.0)

    # Blend: 70% hormonal, 30% forces-based (hormonal is primary)
    E_blended = 0.7 * E_hormonal + 0.3 * E_target_forces

    # Delta E with rate limiting
    delta_E_raw = E_blended - E_prev
    delta_E = clamp(delta_E_raw, -MAX_DELTA, MAX_DELTA)
    E_next = clamp(E_prev + delta_E, -10.0, 10.0)

    # ── Step 7: Bot mirroring ──
    bot_state = BotEmotionalState()
    bot_state.E_bot = current_state.bot_E
    bot_state.pacing_turns = current_state.bot_pacing_turns
    bot_state.user_negative_streak = current_state.bot_negative_streak
    bot_state.update(E_next)

    # ── Step 8: Classify zone & phase ──
    zone = classify_zone(E_next)
    phase = classify_phase(E_next, delta_E)

    # ── Step 9: Update flags ──
    flags = update_flags(current_state.flags, emotion, E_next)

    # ── Step 10: Update delta history ──
    delta_history = list(current_state.delta_history)
    delta_history.append(round(delta_E, 4))
    if len(delta_history) > DELTA_HISTORY_SIZE:
        delta_history = delta_history[-DELTA_HISTORY_SIZE:]

    # ── Build new state ──
    new_state = EVCState(
        E=round(E_next, 4),
        E_prev=round(E_prev, 4),
        delta_E=round(delta_E, 4),
        E_target=round(E_blended, 4),
        I=0.3,  # Not used in v4 but kept for compatibility
        M=0.05,
        zone=zone,
        phase=phase,
        flags=flags,
        turn=current_state.turn + 1,
        timestamp=current_time,
        delta_history=delta_history,
        # v4 additions
        hormone_levels=cocktail.serialize_levels(),
        bot_E=round(bot_state.E_bot, 4),
        bot_pacing_turns=bot_state.pacing_turns,
        bot_negative_streak=bot_state.user_negative_streak,
        dominant_state=cocktail.get_dominant_state(),
    )

    return new_state, forces_biased


def create_initial_state() -> EVCState:
    """สร้าง EVC state เริ่มต้น (neutral) with baseline hormones"""
    cocktail = HormoneCocktail()

    return EVCState(
        E=0.0,
        E_prev=0.0,
        delta_E=0.0,
        E_target=0.0,
        I=0.3,
        M=0.05,
        zone=EmotionalZone.NEUTRAL,
        phase=EmotionalPhase.STABLE,
        flags=EVCFlags(),
        turn=0,
        timestamp=datetime.now(),
        delta_history=[],
        hormone_levels=cocktail.serialize_levels(),
        bot_E=0.0,
        bot_pacing_turns=0,
        bot_negative_streak=0,
        dominant_state="neutral",
    )


def get_bot_tone_instruction(state: EVCState) -> str:
    """Get bot tone instruction for LLM from current state."""
    bot = BotEmotionalState()
    bot.E_bot = state.bot_E
    bot.pacing_turns = state.bot_pacing_turns
    return bot.get_tone_instruction()


def get_bot_tone(state: EVCState) -> str:
    """Get bot tone label from current state."""
    bot = BotEmotionalState()
    bot.E_bot = state.bot_E
    return bot.get_tone()
