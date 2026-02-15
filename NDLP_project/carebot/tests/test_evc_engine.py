"""
Unit tests for EVC Engine — Core equation, optimizations, and full pipeline
"""
import sys
import os
import pytest
from datetime import datetime, timedelta

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import (
    EVCState, EmotionFeatures, EVCFlags, EVCForces,
    EmotionalZone, EmotionalPhase, Intent
)
from evc.engine import (
    update_evc, create_initial_state,
    adaptive_inertia, time_based_decay, clamp, sign,
    MAX_DELTA, BASE_INERTIA, BASE_MEMORY_DECAY
)
from evc.scoring import (
    compute_support_force, compute_drag_force,
    compute_sensitivity, compute_forces
)
from evc.rules import classify_zone, classify_phase, get_response_policy
from evc.therapeutic import apply_therapeutic_bias, get_therapeutic_note
from evc.emotion_extractor import extract_rule_based


# ──────────────────────────────────────────────
# Test Helper
# ──────────────────────────────────────────────
def make_emotion(
    valence=0.0, arousal=0.5, dominance=0.5,
    intent=Intent.NEUTRAL, sarcasm_prob=0.0,
    support_need=0.5, uncertainty=0.3
) -> EmotionFeatures:
    return EmotionFeatures(
        valence=valence, arousal=arousal, dominance=dominance,
        intent=intent, sarcasm_prob=sarcasm_prob,
        support_need=support_need, uncertainty=uncertainty,
    )


# ══════════════════════════════════════════════
# 1. Core Equation Tests
# ══════════════════════════════════════════════

class TestCoreEquation:
    """ทดสอบสมการหลัก EVC"""

    def test_initial_state_is_neutral(self):
        """สถานะเริ่มต้นต้องเป็น neutral"""
        state = create_initial_state()
        assert state.E == 0.0
        assert state.zone == EmotionalZone.NEUTRAL
        assert state.phase == EmotionalPhase.STABLE
        assert state.turn == 0

    def test_positive_emotion_increases_E(self):
        """อารมณ์เชิงบวกต้องทำให้ E เพิ่มขึ้น"""
        state = create_initial_state()
        emotion = make_emotion(valence=0.8, intent=Intent.PRAISE)
        new_state, forces = update_evc(state, emotion)
        assert new_state.E > state.E
        assert new_state.turn == 1

    def test_negative_emotion_decreases_E(self):
        """อารมณ์เชิงลบต้องทำให้ E ลดลง"""
        state = create_initial_state()
        emotion = make_emotion(valence=-0.8, arousal=0.7)
        new_state, forces = update_evc(state, emotion)
        assert new_state.E < state.E

    def test_E_stays_within_bounds(self):
        """E ต้องอยู่ในช่วง [-10, 10] เสมอ"""
        state = create_initial_state()
        # Push extremely positive
        for _ in range(20):
            emotion = make_emotion(valence=1.0, arousal=1.0, intent=Intent.PRAISE)
            state, _ = update_evc(state, emotion)
        assert -10.0 <= state.E <= 10.0

        # Push extremely negative
        state = create_initial_state()
        for _ in range(20):
            emotion = make_emotion(valence=-1.0, arousal=1.0)
            state, _ = update_evc(state, emotion)
        assert -10.0 <= state.E <= 10.0

    def test_neutral_emotion_drifts_toward_zero(self):
        """อารมณ์กลางๆ ต้องค่อยๆ พา E ไปหา 0 (memory decay)"""
        # Start positive
        state = create_initial_state()
        state = state.model_copy(update={"E": 5.0})
        emotion = make_emotion(valence=0.0)  # neutral

        new_state, _ = update_evc(state, emotion)
        # E should decrease towards 0 due to memory decay
        assert new_state.E < 5.0


# ══════════════════════════════════════════════
# 2. Rate Limiter Tests (Optimization 2)
# ══════════════════════════════════════════════

class TestRateLimiter:
    """ทดสอบ Rate Limiter (|ΔE| ≤ 3)"""

    def test_delta_E_is_clamped(self):
        """ΔE ต้องไม่เกิน ±3 ต่อ turn"""
        state = create_initial_state()
        # Extreme emotion should still be rate-limited
        emotion = make_emotion(valence=1.0, arousal=1.0, intent=Intent.PRAISE)
        new_state, _ = update_evc(state, emotion)
        assert abs(new_state.delta_E) <= MAX_DELTA + 0.01  # small float tolerance

    def test_no_bipolar_jumps(self):
        """ต้องไม่กระโดดจากบวกสุดไปลบสุดใน turn เดียว"""
        state = create_initial_state()
        state = state.model_copy(update={"E": 8.0})
        emotion = make_emotion(valence=-1.0, arousal=1.0)
        new_state, _ = update_evc(state, emotion)
        # Should not drop more than MAX_DELTA
        assert state.E - new_state.E <= MAX_DELTA + 0.01


# ══════════════════════════════════════════════
# 3. Adaptive Inertia Tests (Optimization 1)
# ══════════════════════════════════════════════

class TestAdaptiveInertia:
    """ทดสอบ Adaptive Inertia"""

    def test_base_inertia_with_no_history(self):
        """ไม่มี history → ใช้ base inertia"""
        I = adaptive_inertia([], BASE_INERTIA)
        assert I == BASE_INERTIA

    def test_volatile_history_increases_inertia(self):
        """อารมณ์เหวี่ยง → Inertia สูงขึ้น"""
        volatile_history = [3.0, -2.5, 2.8]  # high volatility
        I = adaptive_inertia(volatile_history)
        assert I > BASE_INERTIA

    def test_stable_history_keeps_low_inertia(self):
        """อารมณ์เสถียร → Inertia ใกล้ base"""
        stable_history = [0.1, -0.1, 0.05]  # low volatility
        I = adaptive_inertia(stable_history)
        assert I < 0.4  # close to base

    def test_inertia_never_exceeds_max(self):
        """Inertia ต้องไม่เกิน 0.7"""
        extreme_history = [10.0, -10.0, 10.0]
        I = adaptive_inertia(extreme_history)
        assert I <= 0.7


# ══════════════════════════════════════════════
# 4. Time-based Decay Tests (Optimization 3)
# ══════════════════════════════════════════════

class TestTimeBasedDecay:
    """ทดสอบ Time-based Memory Decay"""

    def test_no_time_gap_returns_base(self):
        """ไม่มีช่วงห่าง → ใช้ base decay"""
        now = datetime.now()
        M = time_based_decay(BASE_MEMORY_DECAY, now, now)
        assert M == pytest.approx(BASE_MEMORY_DECAY, abs=0.001)

    def test_longer_gap_more_decay(self):
        """ห่างนาน → decay มากขึ้น"""
        now = datetime.now()
        one_hour = now - timedelta(hours=1)
        six_hours = now - timedelta(hours=6)

        M_1h = time_based_decay(BASE_MEMORY_DECAY, one_hour, now)
        M_6h = time_based_decay(BASE_MEMORY_DECAY, six_hours, now)

        assert M_6h > M_1h > BASE_MEMORY_DECAY

    def test_no_previous_timestamp_returns_base(self):
        """ไม่มี timestamp ก่อนหน้า → ใช้ base"""
        M = time_based_decay(BASE_MEMORY_DECAY, None, datetime.now())
        assert M == BASE_MEMORY_DECAY


# ══════════════════════════════════════════════
# 5. Therapeutic Bias Tests (Optimization 4)
# ══════════════════════════════════════════════

class TestTherapeuticBias:
    """ทดสอบ Therapeutic Bias"""

    def test_negative_E_increases_support(self):
        """E ลบ → S เพิ่มขึ้น"""
        S_original = 0.3
        S_biased = apply_therapeutic_bias(S_original, -5.0)
        assert S_biased > S_original

    def test_positive_E_no_bias(self):
        """E บวก → ไม่มี bias"""
        S_original = 0.3
        S_biased = apply_therapeutic_bias(S_original, 3.0)
        assert S_biased == S_original

    def test_more_negative_stronger_bias(self):
        """E ลบยิ่งมาก → bias ยิ่งแรง"""
        S1 = apply_therapeutic_bias(0.3, -2.0)
        S2 = apply_therapeutic_bias(0.3, -8.0)
        assert S2 > S1


# ══════════════════════════════════════════════
# 6. Zone & Phase Classification Tests
# ══════════════════════════════════════════════

class TestZonePhase:
    """ทดสอบการจัดโซนและเฟส"""

    def test_zone_classification(self):
        assert classify_zone(-8.0) == EmotionalZone.EXTREME_NEGATIVE
        assert classify_zone(-4.0) == EmotionalZone.NEGATIVE
        assert classify_zone(0.0) == EmotionalZone.NEUTRAL
        assert classify_zone(4.0) == EmotionalZone.POSITIVE
        assert classify_zone(8.0) == EmotionalZone.OVERHEAT_POSITIVE

    def test_phase_classification(self):
        assert classify_phase(-7.0, 1.0) == EmotionalPhase.CRASH_RECOVERY
        assert classify_phase(7.0, -1.0) == EmotionalPhase.PEAK
        assert classify_phase(0.0, -1.0) == EmotionalPhase.DECLINING
        assert classify_phase(0.0, 1.0) == EmotionalPhase.RISING
        assert classify_phase(0.0, 0.0) == EmotionalPhase.STABLE

    def test_boundary_values(self):
        """ทดสอบค่าขอบเขต"""
        assert classify_zone(-6.0) == EmotionalZone.EXTREME_NEGATIVE
        assert classify_zone(-2.0) == EmotionalZone.NEGATIVE
        assert classify_zone(2.0) == EmotionalZone.NEUTRAL
        assert classify_zone(6.0) == EmotionalZone.POSITIVE


# ══════════════════════════════════════════════
# 7. Scoring Tests
# ══════════════════════════════════════════════

class TestScoring:
    """ทดสอบ S, D, K computation"""

    def test_support_force_with_praise(self):
        """Praise intent → S สูง"""
        state = create_initial_state()
        emotion = make_emotion(valence=0.8, intent=Intent.PRAISE)
        S = compute_support_force(emotion, state)
        assert S > 0.3

    def test_drag_force_with_negative(self):
        """อารมณ์ลบ → D สูง"""
        emotion = make_emotion(valence=-0.8, sarcasm_prob=0.7)
        D = compute_drag_force(emotion)
        assert D > 0.3

    def test_sensitivity_with_crisis(self):
        """Crisis flags → K สูง"""
        state = create_initial_state()
        state = state.model_copy(update={"flags": EVCFlags(crisis=True, anger=True)})
        emotion = make_emotion(arousal=0.8)
        K = compute_sensitivity(emotion, state)
        assert K > 1.5

    def test_forces_return_valid_ranges(self):
        """S, D ∈ [0,1], K ∈ [0.5, 2.5]"""
        state = create_initial_state()
        emotion = make_emotion()
        forces = compute_forces(emotion, state)
        assert 0.0 <= forces.S <= 1.0
        assert 0.0 <= forces.D <= 1.0
        assert 0.5 <= forces.K <= 2.5


# ══════════════════════════════════════════════
# 8. Rule-based Emotion Extraction Tests
# ══════════════════════════════════════════════

class TestRuleBasedExtraction:
    """ทดสอบการสกัดอารมณ์แบบ rule-based (Thai + English)"""

    def test_positive_thai(self):
        """ข้อความบวกภาษาไทย"""
        result = extract_rule_based("วันนี้มีความสุขมาก ดีใจจัง!")
        assert result.valence > 0

    def test_negative_thai(self):
        """ข้อความลบภาษาไทย"""
        result = extract_rule_based("เครียดมาก เหนื่อยจะตาย ท้อแท้")
        assert result.valence < 0

    def test_sarcasm_thai(self):
        """ข้อความประชดภาษาไทย"""
        result = extract_rule_based("ดีจริงๆ เลย เก่งจังนะ จริงดิ")
        assert result.sarcasm_prob > 0

    def test_greeting_thai(self):
        """ทักทายภาษาไทย"""
        result = extract_rule_based("สวัสดีครับ")
        assert result.intent == Intent.GREETING

    def test_help_seeking_thai(self):
        """ขอความช่วยเหลือ"""
        result = extract_rule_based("ช่วยหน่อยได้ไหม ไม่รู้จะทำไง")
        assert result.intent == Intent.SEEKING_HELP

    def test_neutral_text(self):
        """ข้อความกลางๆ"""
        result = extract_rule_based("วันนี้ไปโรงเรียน")
        assert -0.5 < result.valence < 0.5

    def test_confidence_is_low_for_rule_based(self):
        """Rule-based ต้องมี confidence ต่ำกว่า LLM"""
        result = extract_rule_based("test message")
        assert result.confidence <= 0.5


# ══════════════════════════════════════════════
# 9. Response Policy Tests
# ══════════════════════════════════════════════

class TestResponsePolicy:
    """ทดสอบการสร้าง Response Policy"""

    def test_crisis_mode_policy(self):
        """Crisis → ต้องมี crisis mode ใน policy"""
        policy = get_response_policy(
            EmotionalZone.EXTREME_NEGATIVE,
            EmotionalPhase.CRASH_RECOVERY,
            EVCFlags(crisis=True),
            make_emotion(valence=-0.9),
        )
        assert "CRISIS" in policy

    def test_sarcasm_policy(self):
        """Sarcasm → ต้องมีนโยบายจัดการประชด"""
        policy = get_response_policy(
            EmotionalZone.NEUTRAL,
            EmotionalPhase.STABLE,
            EVCFlags(sarcasm=True),
            make_emotion(sarcasm_prob=0.8),
        )
        assert "ประชด" in policy

    def test_positive_zone_policy(self):
        """Positive → ร่วมยินดี"""
        policy = get_response_policy(
            EmotionalZone.POSITIVE,
            EmotionalPhase.RISING,
            EVCFlags(),
            make_emotion(valence=0.7),
        )
        assert "บวก" in policy or "กระตือรือร้น" in policy


# ══════════════════════════════════════════════
# 10. Integration Test — Full Pipeline
# ══════════════════════════════════════════════

class TestFullPipeline:
    """ทดสอบ Pipeline เต็ม: emotion → forces → EVC update"""

    def test_5_turn_conversation(self):
        """จำลองบทสนทนา 5 turns"""
        state = create_initial_state()

        # Turn 1: Greeting
        emotion = make_emotion(valence=0.2, intent=Intent.GREETING)
        state, forces = update_evc(state, emotion)
        assert state.turn == 1
        assert state.zone == EmotionalZone.NEUTRAL

        # Turn 2: Venting (เครียดเรื่องสอบ)
        emotion = make_emotion(
            valence=-0.7, arousal=0.7,
            intent=Intent.VENTING, support_need=0.8
        )
        state, forces = update_evc(state, emotion)
        assert state.E < state.E_prev  # decreased

        # Turn 3: More negative
        emotion = make_emotion(
            valence=-0.8, arousal=0.8,
            intent=Intent.VENTING, support_need=0.9
        )
        state, forces = update_evc(state, emotion)
        assert state.zone in [EmotionalZone.NEGATIVE, EmotionalZone.NEUTRAL]

        # Turn 4: Slightly better
        emotion = make_emotion(
            valence=-0.2, arousal=0.4,
            intent=Intent.NEUTRAL
        )
        state, forces = update_evc(state, emotion)

        # Turn 5: Positive (ขอบคุณที่รับฟัง)
        emotion = make_emotion(
            valence=0.6, arousal=0.4,
            intent=Intent.PRAISE
        )
        state, forces = update_evc(state, emotion)
        assert state.delta_E > 0  # improving

    def test_crisis_detection(self):
        """จำลองภาวะวิกฤต (E ≤ -6)"""
        state = create_initial_state()

        # Push to extreme negative
        for _ in range(10):
            emotion = make_emotion(
                valence=-1.0, arousal=0.9,
                intent=Intent.VENTING, support_need=1.0
            )
            state, _ = update_evc(state, emotion)

        # Should eventually reach crisis
        if state.E <= -6:
            assert state.flags.crisis is True
            assert state.zone == EmotionalZone.EXTREME_NEGATIVE
