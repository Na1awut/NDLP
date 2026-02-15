"""
EVC Rules — Zone/Phase classification and Response Policy generation

Zone classification based on E:
  ExtremeNegative: E ≤ -6
  Negative:        -6 < E ≤ -2
  Neutral:         -2 < E ≤ 2
  Positive:        2 < E ≤ 6
  OverheatPositive: E > 6

Phase classification based on ΔE:
  CrashRecovery: E ≤ -6 and ΔE > 0
  Declining:     ΔE < -0.5
  Stable:        -0.5 ≤ ΔE ≤ 0.5
  Rising:        ΔE > 0.5
  Peak:          E > 6 and ΔE < 0
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import (
    EmotionalZone, EmotionalPhase, EVCFlags,
    EmotionFeatures, Intent
)


# ──────────────────────────────────────────────
# Zone Classification
# ──────────────────────────────────────────────
def classify_zone(E: float) -> EmotionalZone:
    """จัดโซนอารมณ์จากค่า E"""
    if E <= -6:
        return EmotionalZone.EXTREME_NEGATIVE
    elif E <= -2:
        return EmotionalZone.NEGATIVE
    elif E <= 2:
        return EmotionalZone.NEUTRAL
    elif E <= 6:
        return EmotionalZone.POSITIVE
    else:
        return EmotionalZone.OVERHEAT_POSITIVE


# ──────────────────────────────────────────────
# Phase Classification
# ──────────────────────────────────────────────
def classify_phase(E: float, delta_E: float) -> EmotionalPhase:
    """จัดเฟสอารมณ์จากค่า E และ ΔE"""
    if E <= -6 and delta_E > 0:
        return EmotionalPhase.CRASH_RECOVERY
    elif E > 6 and delta_E < 0:
        return EmotionalPhase.PEAK
    elif delta_E < -0.5:
        return EmotionalPhase.DECLINING
    elif delta_E > 0.5:
        return EmotionalPhase.RISING
    else:
        return EmotionalPhase.STABLE


# ──────────────────────────────────────────────
# Flag Update
# ──────────────────────────────────────────────
def update_flags(
    current_flags: EVCFlags,
    emotion: EmotionFeatures,
    E: float
) -> EVCFlags:
    """อัปเดต flags จากอารมณ์ที่สกัดได้"""
    return EVCFlags(
        sarcasm=emotion.sarcasm_prob > 0.5,
        anger=(
            emotion.valence < -0.5
            and emotion.arousal > 0.7
            and emotion.dominance > 0.6
        ),
        anxiety=(
            emotion.valence < -0.3
            and emotion.arousal > 0.6
            and emotion.dominance < 0.4
        ),
        stress=(
            emotion.arousal > 0.7
            and emotion.support_need > 0.6
        ),
        crisis=E <= -6,
        boundary_setting=(
            emotion.dominance > 0.7
            and emotion.intent == Intent.AGGRESSION
        ),
        mood_swing=abs(emotion.valence) > 0.7 and emotion.arousal > 0.6,
    )


# ──────────────────────────────────────────────
# Response Policy Generation
# ──────────────────────────────────────────────
def get_response_policy(
    zone: EmotionalZone,
    phase: EmotionalPhase,
    flags: EVCFlags,
    emotion: EmotionFeatures,
) -> str:
    """
    สร้าง policy string สำหรับ LLM — บอกว่าควรตอบยังไง
    """
    policies: list[str] = []

    # ──── CRISIS MODE (สูงสุด) ────
    if flags.crisis:
        policies.append(
            "🚨 CRISIS MODE: นักเรียนอยู่ในภาวะวิกฤต "
            "ตอบอย่างอ่อนโยนที่สุด อย่าตัดสิน อย่าสั่งสอน "
            "ถามว่ารู้สึกปลอดภัยไหม บอกว่าพร้อมรับฟัง"
        )

    # ──── SARCASM DETECTED ────
    if flags.sarcasm:
        policies.append(
            "ประชดตรวจพบ: อย่าตอบตามตัวอักษร "
            "ถามว่าจริงๆ แล้วรู้สึกยังไง ใช้น้ำเสียงอ่อนโยน"
        )

    # ──── ANGER DETECTED ────
    if flags.anger:
        policies.append(
            "ความโกรธ: ยอมรับความรู้สึก อย่าต่อล้อต่อเถียง "
            "ให้พื้นที่ระบาย ถามว่าอะไรทำให้โกรธ"
        )

    # ──── ANXIETY DETECTED ────
    if flags.anxiety:
        policies.append(
            "ความกังวล: พูดสงบ ช้าลง ให้ความมั่นใจ "
            "ช่วยจัดระเบียบความคิด"
        )

    # ──── Zone-based policy ────
    if zone == EmotionalZone.EXTREME_NEGATIVE:
        policies.append(
            "โซนลบสุด: ปกป้อง ดูแล อย่ากดดัน "
            "ถามเรื่องความปลอดภัย"
        )
    elif zone == EmotionalZone.NEGATIVE:
        policies.append(
            "โซนลบ: เห็นอกเห็นใจ รับฟัง "
            "ค่อยๆ ชวนหาทางออก"
        )
    elif zone == EmotionalZone.NEUTRAL:
        policies.append(
            "โซนกลาง: เป็นธรรมชาติ เป็นมิตร"
        )
    elif zone == EmotionalZone.POSITIVE:
        policies.append(
            "โซนบวก: กระตือรือร้น ร่วมยินดี ส่งเสริม"
        )
    elif zone == EmotionalZone.OVERHEAT_POSITIVE:
        policies.append(
            "ตื่นเต้นมาก: ร่วมยินดีแต่ช่วยให้สมดุล "
            "อย่าเพิ่มความตื่นเต้นเกินไป"
        )

    # ──── Phase-based modifier ────
    if phase == EmotionalPhase.CRASH_RECOVERY:
        policies.append("กำลังฟื้นตัว: ชื่นชมเบาๆ สังเกตอาการ")
    elif phase == EmotionalPhase.DECLINING:
        policies.append("อารมณ์กำลังลง: ระวังมากขึ้น ถามเชิงรุก")
    elif phase == EmotionalPhase.RISING:
        policies.append("อารมณ์กำลังดีขึ้น: ส่งเสริมต่อ")

    # ──── Mood swing ────
    if flags.mood_swing:
        policies.append("อารมณ์แกว่ง: ตอบสม่ำเสมอ อย่าตาม mood ไปมา")

    if not policies:
        policies.append("ตอบเป็นธรรมชาติ เป็นมิตร")

    return " | ".join(policies)
