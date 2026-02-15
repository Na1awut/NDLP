"""
8 Hormone Definitions — Biologically-inspired parameters

Each hormone defines:
  - How it maps EmotionFeatures to stimulus
  - Biological half-life and production rate
  - Baseline resting level

ระบบต่อมไร้ท่อจำลอง (Simulated Endocrine System)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from evc.hormones import HormoneBase
from models.evc_models import EmotionFeatures


# ──────────────────────────────────────────────
# 1. Serotonin — อารมณ์มั่นคง, ความสุข
# ──────────────────────────────────────────────
class Serotonin(HormoneBase):
    """
    สร้างจาก: positive valence, calm, low uncertainty
    ลักษณะ: สร้างช้า สลายช้า → ความสุขที่มั่นคง
    """
    def __init__(self):
        super().__init__(
            name="serotonin",
            level=3.0,
            half_life=6,
            max_production=1.5,
            baseline=3.0,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """Positive valence + low arousal + low uncertainty → serotonin"""
        pos_val = max(0.0, e.valence)           # 0-1
        calm = max(0.0, 1.0 - e.arousal)        # 0-1
        clarity = 1.0 - e.uncertainty            # 0-1
        return (pos_val * 0.5 + calm * 0.3 + clarity * 0.2)


# ──────────────────────────────────────────────
# 2. Dopamine — ตื่นเต้น, แรงจูงใจ, รางวัล
# ──────────────────────────────────────────────
class Dopamine(HormoneBase):
    """
    สร้างจาก: praise, excitement, positive surprise
    ลักษณะ: สไปก์เร็ว สลายเร็ว → ความสุขชั่วคราว
    """
    def __init__(self):
        super().__init__(
            name="dopamine",
            level=2.0,
            half_life=2,
            max_production=3.0,
            baseline=2.0,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """High valence + high arousal + praise → dopamine spike"""
        excitement = max(0.0, e.valence) * e.arousal  # 0-1
        praise = 0.5 if e.intent.value == "praise" else 0.0
        return min(1.0, excitement * 0.6 + praise * 0.4)


# ──────────────────────────────────────────────
# 3. Cortisol — ความเครียด
# ──────────────────────────────────────────────
class Cortisol(HormoneBase):
    """
    สร้างจาก: negative valence, high arousal, stress
    ลักษณะ: สะสมช้า สลายช้ามาก → เครียดนาน ส่งผลสะสม
    """
    def __init__(self):
        super().__init__(
            name="cortisol",
            level=1.0,
            half_life=8,
            max_production=2.0,
            baseline=1.0,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """Negative valence + high arousal + uncertainty → cortisol"""
        stress = max(0.0, -e.valence)            # 0-1
        tension = e.arousal * 0.5                 # 0-0.5
        worry = e.uncertainty * 0.3               # 0-0.3
        return min(1.0, stress * 0.5 + tension + worry)


# ──────────────────────────────────────────────
# 4. Oxytocin — ผูกพัน, ไว้ใจ
# ──────────────────────────────────────────────
class Oxytocin(HormoneBase):
    """
    สร้างจาก: gratitude, trust, low sarcasm, apology
    ลักษณะ: สร้างยาก ทำลายง่าย → ความไว้ใจต้องสะสม
    """
    def __init__(self):
        super().__init__(
            name="oxytocin",
            level=1.0,
            half_life=4,
            max_production=1.5,
            baseline=1.0,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """Low sarcasm + trust intents + positive valence → oxytocin"""
        trust = (1.0 - e.sarcasm_prob) * 0.3
        gratitude = 0.4 if e.intent.value in ("praise", "apology") else 0.0
        warmth = max(0.0, e.valence) * 0.3
        return min(1.0, trust + gratitude + warmth)


# ──────────────────────────────────────────────
# 5. Adrenaline (Epinephrine) — fight-or-flight
# ──────────────────────────────────────────────
class Adrenaline(HormoneBase):
    """
    สร้างจาก: crisis, fear, anger, extreme arousal
    ลักษณะ: สไปก์เร็วมาก สลายเร็ว → ตื่นตัวฉับพลัน
    """
    def __init__(self):
        super().__init__(
            name="adrenaline",
            level=0.5,
            half_life=1,
            max_production=5.0,
            baseline=0.5,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """Extreme arousal + negative valence + anger/crisis → adrenaline"""
        danger = max(0.0, -e.valence) * e.arousal  # 0-1
        crisis = 0.5 if e.support_need > 0.8 else 0.0
        anger = 0.3 if e.intent.value == "complaint" and e.dominance > 0.7 else 0.0
        return min(1.0, danger * 0.5 + crisis + anger)


# ──────────────────────────────────────────────
# 6. Endorphin — ผ่อนคลาย, ลดเจ็บปวด
# ──────────────────────────────────────────────
class Endorphin(HormoneBase):
    """
    สร้างจาก: relief after stress, humor, catharsis
    ลักษณะ: สร้างหลังผ่อนคลาย → "ร้องไห้แล้วสบายขึ้น"
    """
    def __init__(self):
        super().__init__(
            name="endorphin",
            level=1.5,
            half_life=3,
            max_production=2.0,
            baseline=1.5,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """
        Endorphin เกิดจาก "relief" — valence ไม่ลบมากแล้ว
        + intent = venting (ระบาย = catharsis)
        """
        relief = max(0.0, 0.5 + e.valence * 0.5)  # valence 0 → 0.5, +1 → 1.0
        venting = 0.3 if e.intent.value == "venting" else 0.0
        low_arousal = max(0.0, 1.0 - e.arousal) * 0.2
        return min(1.0, relief * 0.5 + venting + low_arousal)


# ──────────────────────────────────────────────
# 7. GABA — สงบ, ลดกังวล
# ──────────────────────────────────────────────
class GABA(HormoneBase):
    """
    สร้างจาก: low arousal, calm, feeling safe
    ลักษณะ: ต้านทาน adrenaline → เบรกระบบ fight-or-flight
    """
    def __init__(self):
        super().__init__(
            name="gaba",
            level=2.0,
            half_life=3,
            max_production=2.0,
            baseline=2.0,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """Low arousal + neutral-positive valence → GABA"""
        calm = max(0.0, 1.0 - e.arousal)         # 0-1
        safe = max(0.0, 0.5 + e.valence * 0.5)   # 0-1
        low_need = max(0.0, 1.0 - e.support_need) * 0.3
        return min(1.0, calm * 0.4 + safe * 0.3 + low_need)


# ──────────────────────────────────────────────
# 8. Norepinephrine — สมาธิ, ตื่นตัว
# ──────────────────────────────────────────────
class Norepinephrine(HormoneBase):
    """
    สร้างจาก: high arousal, alertness, focus
    ลักษณะ: ทำงานคู่ adrenaline แต่อยู่นานกว่า
    """
    def __init__(self):
        super().__init__(
            name="norepinephrine",
            level=1.5,
            half_life=2,
            max_production=2.5,
            baseline=1.5,
        )

    def compute_stimulus(self, e: EmotionFeatures) -> float:
        """High arousal regardless of valence → norepinephrine"""
        alertness = e.arousal * 0.6
        intensity = abs(e.valence) * 0.2  # any strong emotion
        focus = e.dominance * 0.2         # assertive = focused
        return min(1.0, alertness + intensity + focus)


# ──────────────────────────────────────────────
# Factory function
# ──────────────────────────────────────────────
def create_all_hormones() -> dict[str, HormoneBase]:
    """Create fresh set of all 8 hormones at baseline levels."""
    hormones = [
        Serotonin(),
        Dopamine(),
        Cortisol(),
        Oxytocin(),
        Adrenaline(),
        Endorphin(),
        GABA(),
        Norepinephrine(),
    ]
    return {h.name: h for h in hormones}
