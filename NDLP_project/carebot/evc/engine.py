"""
EVC Engine — Core Emotional Energy Update Equation (Optimized v3)

สมการหลัก:
  E* = clamp(K × (S - D) × 10, -10, +10)
  ΔE_raw = I_t × (E* - E_t) - M_t × sgn(E_t) × |E_t|
  ΔE = clamp(ΔE_raw, -MAX_DELTA, +MAX_DELTA)    ← Rate Limiter
  E_{t+1} = clamp(E_t + ΔE, -10, +10)

4 Optimizations:
  1. Adaptive Inertia — กันอารมณ์เหวี่ยง
  2. Rate-limited ΔE — จำกัด |ΔE| ≤ 3 ต่อ turn
  3. Time-based Memory Decay — ห่างนาน → ลืมมากขึ้น
  4. Therapeutic Bias — ค่อยๆ ดันขึ้นเมื่ออยู่โซนลบ
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
from evc.scoring import compute_forces
from evc.rules import classify_zone, classify_phase, update_flags
from evc.therapeutic import apply_therapeutic_bias


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
MAX_DELTA = 3.0          # Maximum |ΔE| per turn
BASE_INERTIA = 0.3       # Default inertia
MAX_INERTIA = 0.7        # Maximum adaptive inertia
BASE_MEMORY_DECAY = 0.05 # Default memory decay
DELTA_HISTORY_SIZE = 5   # Number of ΔE values to keep


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def sign(x: float) -> float:
    """Sign function: returns -1, 0, or 1"""
    if x > 0:
        return 1.0
    elif x < 0:
        return -1.0
    return 0.0


# ──────────────────────────────────────────────
# Optimization 1: Adaptive Inertia
# ──────────────────────────────────────────────
def adaptive_inertia(delta_history: list[float], base: float = BASE_INERTIA) -> float:
    """
    ถ้าอารมณ์เหวี่ยงบ่อย (volatile) → เพิ่ม Inertia
    I = min(0.7, base + 0.1 × mean_volatility_last_3)
    """
    if len(delta_history) >= 3:
        recent = delta_history[-3:]
        volatility = sum(abs(d) for d in recent) / len(recent)
        return min(MAX_INERTIA, base + 0.1 * volatility)
    return base


# ──────────────────────────────────────────────
# Optimization 3: Time-based Memory Decay
# ──────────────────────────────────────────────
def time_based_decay(
    base_M: float,
    last_timestamp: datetime | None,
    current_timestamp: datetime
) -> float:
    """
    ห่างนาน = ลืมมากขึ้น
    M = base × (1 + log(1 + hours_since_last))
    """
    if last_timestamp is None:
        return base_M

    delta = current_timestamp - last_timestamp
    hours = delta.total_seconds() / 3600.0

    if hours <= 0:
        return base_M

    return base_M * (1 + math.log(1 + hours))


# ──────────────────────────────────────────────
# Core EVC Update
# ──────────────────────────────────────────────
def update_evc(
    current_state: EVCState,
    emotion: EmotionFeatures,
    current_time: datetime | None = None,
) -> tuple[EVCState, EVCForces]:
    """
    Update EVC state using optimized v3 equation.

    Returns: (new_state, forces)
    """
    if current_time is None:
        current_time = datetime.now()

    E_prev = current_state.E

    # ── Step 1: Compute forces ──
    forces = compute_forces(emotion, current_state)
    S = forces.S
    D = forces.D
    K = forces.K

    # ── Step 2: Apply therapeutic bias (Optimization 4) ──
    S = apply_therapeutic_bias(S, E_prev)

    # ── Step 3: Compute target energy ──
    E_target = clamp(K * (S - D) * 10, -10.0, 10.0)

    # ── Step 4: Adaptive inertia (Optimization 1) ──
    I = adaptive_inertia(current_state.delta_history, BASE_INERTIA)

    # ── Step 5: Time-based memory decay (Optimization 3) ──
    M = time_based_decay(BASE_MEMORY_DECAY, current_state.timestamp, current_time)

    # ── Step 6: Core equation ──
    delta_E_raw = I * (E_target - E_prev) - M * sign(E_prev) * abs(E_prev)

    # ── Step 7: Rate limiter (Optimization 2) ──
    delta_E = clamp(delta_E_raw, -MAX_DELTA, MAX_DELTA)

    # ── Step 8: Final energy ──
    E_next = clamp(E_prev + delta_E, -10.0, 10.0)

    # ── Step 9: Classify zone & phase ──
    zone = classify_zone(E_next)
    phase = classify_phase(E_next, delta_E)

    # ── Step 10: Update flags ──
    flags = update_flags(current_state.flags, emotion, E_next)

    # ── Step 11: Update delta history ──
    delta_history = list(current_state.delta_history)
    delta_history.append(round(delta_E, 4))
    if len(delta_history) > DELTA_HISTORY_SIZE:
        delta_history = delta_history[-DELTA_HISTORY_SIZE:]

    # ── Build new state ──
    new_state = EVCState(
        E=round(E_next, 4),
        E_prev=round(E_prev, 4),
        delta_E=round(delta_E, 4),
        E_target=round(E_target, 4),
        I=round(I, 4),
        M=round(M, 6),
        zone=zone,
        phase=phase,
        flags=flags,
        turn=current_state.turn + 1,
        timestamp=current_time,
        delta_history=delta_history,
    )

    return new_state, forces


def create_initial_state() -> EVCState:
    """สร้าง EVC state เริ่มต้น (neutral)"""
    return EVCState(
        E=0.0,
        E_prev=0.0,
        delta_E=0.0,
        E_target=0.0,
        I=BASE_INERTIA,
        M=BASE_MEMORY_DECAY,
        zone=EmotionalZone.NEUTRAL,
        phase=EmotionalPhase.STABLE,
        flags=EVCFlags(),
        turn=0,
        timestamp=datetime.now(),
        delta_history=[],
    )
