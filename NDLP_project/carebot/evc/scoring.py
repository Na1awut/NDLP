"""
EVC Scoring — Compute Support Force (S), Drag Force (D), and Sensitivity (K)

สมการ:
  S = w₁·praise + w₂·apology + w₃·clarity + w₄·trust
  D = v₁·insult + v₂·sarcasm + v₃·uncertainty + v₄·conflict
  K = K₀ + α·arousal + β·uncertainty + γ·risk_score
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import EmotionFeatures, EVCState, EVCForces, Intent


# ──────────────────────────────────────────────
# Support Force Weights
# ──────────────────────────────────────────────
S_WEIGHTS = {
    "praise": 0.40,
    "apology": 0.30,
    "clarity": 0.20,
    "trust": 0.10,
}

# ──────────────────────────────────────────────
# Drag Force Weights
# ──────────────────────────────────────────────
D_WEIGHTS = {
    "insult": 0.30,
    "sarcasm": 0.25,
    "uncertainty": 0.25,
    "conflict": 0.20,
}

# ──────────────────────────────────────────────
# Sensitivity Parameters
# ──────────────────────────────────────────────
K_BASE = 1.0
K_ALPHA = 0.3   # arousal sensitivity
K_BETA = 0.2    # uncertainty sensitivity
K_GAMMA = 0.4   # risk score sensitivity


def compute_support_force(emotion: EmotionFeatures, evc: EVCState) -> float:
    """
    คำนวณแรงยก (Support Force)
    S = w₁·praise + w₂·apology + w₃·clarity + w₄·trust
    """
    # Praise component: positive valence + praise intent
    praise = 0.0
    if emotion.intent == Intent.PRAISE:
        praise = max(0.0, emotion.valence)
    elif emotion.valence > 0.3:
        praise = emotion.valence * 0.5  # partial credit for positive valence

    # Apology component
    apology = 0.5 if emotion.intent == Intent.APOLOGY else 0.0

    # Clarity component: inverse of uncertainty
    clarity = 1.0 - emotion.uncertainty

    # Trust component: low sarcasm + positive history
    trust_from_sarcasm = (1.0 - emotion.sarcasm_prob) * 0.5
    trust_from_history = 0.3 if evc.E > 0 else 0.0
    trust = trust_from_sarcasm + trust_from_history

    S = (
        S_WEIGHTS["praise"] * praise
        + S_WEIGHTS["apology"] * apology
        + S_WEIGHTS["clarity"] * clarity
        + S_WEIGHTS["trust"] * trust
    )

    return max(0.0, min(1.0, S))


def compute_drag_force(emotion: EmotionFeatures) -> float:
    """
    คำนวณแรงฉุด (Drag Force)
    D = v₁·insult + v₂·sarcasm + v₃·uncertainty + v₄·conflict
    """
    # Insult component: negative valence
    insult = max(0.0, -emotion.valence)

    # Sarcasm component
    sarcasm = emotion.sarcasm_prob

    # Uncertainty component
    uncertainty = emotion.uncertainty

    # Conflict component: high dominance + negative valence
    conflict = 0.0
    if emotion.valence < 0 and emotion.dominance > 0.6:
        conflict = emotion.dominance * 0.5

    D = (
        D_WEIGHTS["insult"] * insult
        + D_WEIGHTS["sarcasm"] * sarcasm
        + D_WEIGHTS["uncertainty"] * uncertainty
        + D_WEIGHTS["conflict"] * conflict
    )

    return max(0.0, min(1.0, D))


def compute_sensitivity(emotion: EmotionFeatures, evc: EVCState) -> float:
    """
    คำนวณ Sensitivity (K)
    K = K₀ + α·arousal + β·uncertainty + γ·risk_score
    """
    # Risk score from flags
    risk_score = 0.0
    if evc.flags.anger:
        risk_score += 0.3
    if evc.flags.anxiety:
        risk_score += 0.2
    if evc.flags.stress:
        risk_score += 0.2
    if evc.flags.sarcasm:
        risk_score += 0.15
    if evc.flags.crisis:
        risk_score += 0.5
    risk_score = min(1.0, risk_score)

    K = (
        K_BASE
        + K_ALPHA * emotion.arousal
        + K_BETA * emotion.uncertainty
        + K_GAMMA * risk_score
    )

    return max(0.5, min(2.5, K))


def compute_forces(emotion: EmotionFeatures, evc: EVCState) -> EVCForces:
    """
    คำนวณแรงทั้ง 3 ตัว → คืน EVCForces
    """
    S = compute_support_force(emotion, evc)
    D = compute_drag_force(emotion)
    K = compute_sensitivity(emotion, evc)

    return EVCForces(S=round(S, 4), D=round(D, 4), K=round(K, 4))
