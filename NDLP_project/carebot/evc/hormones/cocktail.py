"""
Hormone Cocktail — Orchestrates all 8 hormones + interaction matrix

เลียนแบบระบบต่อมไร้ท่อ:
  1. รับ EmotionFeatures → แต่ละฮอร์โมน produce
  2. Apply interaction matrix (cross-effects)
  3. Decay ทุกตัวเข้าหา baseline
  4. คำนวณ E_composite จาก cocktail

Interaction Matrix (8×8):
  Positive = กระตุ้น, Negative = กด
  ค่าจากความสัมพันธ์ทางชีววิทยาจริงๆ
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from evc.hormones import HormoneBase
from evc.hormones.definitions import create_all_hormones
from models.evc_models import EmotionFeatures

# ──────────────────────────────────────────────
# Hormone order (for matrix indexing)
# ──────────────────────────────────────────────
HORMONE_ORDER = [
    "serotonin",      # 0
    "dopamine",       # 1
    "cortisol",       # 2
    "oxytocin",       # 3
    "adrenaline",     # 4
    "endorphin",      # 5
    "gaba",           # 6
    "norepinephrine", # 7
]

# ──────────────────────────────────────────────
# 8×8 Interaction Matrix
#
# interaction_matrix[i][j] = effect of hormone j ON hormone i
# Positive = stimulate, Negative = suppress
#
#              Sero   Dopa   Cort   Oxyto  Adren  Endor  GABA   Norep
# ──────────────────────────────────────────────
INTERACTION_MATRIX = [
    # Serotonin affected by:
    [ 0.00, +0.10, -0.20, +0.10,  0.00, +0.10, +0.10,  0.00],
    # Dopamine affected by:
    [+0.10,  0.00,  0.00,  0.00, +0.10,  0.00,  0.00, +0.10],
    # Cortisol affected by:
    [-0.15, -0.05,  0.00, -0.15, +0.20, -0.10, -0.10, +0.10],
    # Oxytocin affected by:
    [+0.15,  0.00, -0.15,  0.00, -0.10, +0.10, +0.15,  0.00],
    # Adrenaline affected by:
    [-0.10, +0.05, +0.15, -0.05,  0.00,  0.00, -0.25, +0.15],
    # Endorphin affected by:
    [+0.10,  0.00, -0.10, +0.10, -0.05,  0.00, +0.10,  0.00],
    # GABA affected by:
    [+0.10,  0.00, -0.10, +0.10, -0.15, +0.05,  0.00, -0.10],
    # Norepinephrine affected by:
    [ 0.00, +0.10, +0.10,  0.00, +0.20,  0.00, -0.10,  0.00],
]

# ──────────────────────────────────────────────
# E_composite weights (positive = good, negative = bad)
# ──────────────────────────────────────────────
E_WEIGHTS = {
    "serotonin":      +0.25,  # ความสุขมั่นคง
    "dopamine":       +0.15,  # ตื่นเต้น/แรงจูงใจ
    "cortisol":       -0.25,  # เครียด (ลบ)
    "oxytocin":       +0.15,  # ผูกพัน/ไว้ใจ
    "adrenaline":     -0.10,  # วิกฤต (ลบ)
    "endorphin":      +0.10,  # ผ่อนคลาย
    "gaba":           +0.05,  # สงบ
    "norepinephrine": -0.05,  # ตื่นตัว (มากไป = ลบ)
}

# Normalize: Σ|weights| should sum to meaningful range
# Current: +0.70, -0.40 → max E ≈ +7, min E ≈ -4 (at level 10)
# This gives good range for -10 to +10 scale


class HormoneCocktail:
    """
    ระบบต่อมไร้ท่อจำลอง — orchestrate 8 hormones

    Usage:
        cocktail = HormoneCocktail()
        cocktail.update(emotion_features)
        E = cocktail.compute_E()
        dominant = cocktail.get_dominant_state()
    """

    def __init__(self, hormones: dict[str, HormoneBase] | None = None):
        self.hormones = hormones or create_all_hormones()

    def update(self, emotion: EmotionFeatures) -> None:
        """
        Full hormone update cycle:
        1. Each hormone produces based on emotion stimulus
        2. Apply cross-hormone interactions
        3. Apply natural decay
        """
        # ── Step 1: Production ──
        for name, hormone in self.hormones.items():
            stimulus = hormone.compute_stimulus(emotion)
            hormone.produce(stimulus)

        # ── Step 2: Cross-hormone interactions ──
        self._apply_interactions()

        # ── Step 3: Natural decay ──
        for hormone in self.hormones.values():
            hormone.decay()

    def _apply_interactions(self) -> None:
        """
        Apply 8×8 interaction matrix.
        Each hormone is affected by all other hormones' current levels.
        """
        # Collect current levels (before interaction)
        levels = [self.hormones[name].get_normalized() for name in HORMONE_ORDER]

        for i, target_name in enumerate(HORMONE_ORDER):
            target = self.hormones[target_name]
            interaction_sum = 0.0

            for j, source_name in enumerate(HORMONE_ORDER):
                if i == j:
                    continue
                weight = INTERACTION_MATRIX[i][j]
                interaction_sum += weight * levels[j]

            # Apply interaction effect
            if interaction_sum > 0:
                target.stimulate(interaction_sum)
            elif interaction_sum < 0:
                target.suppress(abs(interaction_sum))

    def compute_E(self) -> float:
        """
        คำนวณ E composite จาก weighted combination ของทุกฮอร์โมน.

        E = Σ(weight_i × level_i)
        Clamped to [-10, +10]
        """
        E = 0.0
        for name, weight in E_WEIGHTS.items():
            E += weight * self.hormones[name].level
        return max(-10.0, min(10.0, E))

    def get_dominant_state(self) -> str:
        """
        หาสภาวะอารมณ์หลักจากฮอร์โมนที่เหนือกว่า baseline มากที่สุด.

        Returns: label เช่น "stressed", "calm", "excited", "trusting"
        """
        state_map = {
            "serotonin": "content",       # พอใจ
            "dopamine": "excited",        # ตื่นเต้น
            "cortisol": "stressed",       # เครียด
            "oxytocin": "trusting",       # ไว้ใจ
            "adrenaline": "alert",        # ตื่นตัว/วิกฤต
            "endorphin": "relieved",      # ผ่อนคลาย
            "gaba": "calm",              # สงบ
            "norepinephrine": "focused",  # มีสมาธิ
        }

        max_diff = -999.0
        dominant = "neutral"

        for name, hormone in self.hormones.items():
            diff = hormone.level - hormone.baseline
            if diff > max_diff:
                max_diff = diff
                dominant = state_map.get(name, "neutral")

        # If no hormone is significantly above baseline → neutral
        if max_diff < 0.5:
            dominant = "neutral"

        return dominant

    def get_levels(self) -> dict[str, float]:
        """Get all hormone levels as dict."""
        return {name: round(h.level, 3) for name, h in self.hormones.items()}

    def to_dict(self) -> dict:
        """Full serialization for API/debug."""
        return {
            "hormones": {name: h.to_dict() for name, h in self.hormones.items()},
            "E_composite": round(self.compute_E(), 3),
            "dominant_state": self.get_dominant_state(),
        }

    def serialize_levels(self) -> dict[str, float]:
        """Minimal serialization for storage."""
        return {name: h.level for name, h in self.hormones.items()}

    def restore_levels(self, levels: dict[str, float]) -> None:
        """Restore hormone levels from storage."""
        for name, level in levels.items():
            if name in self.hormones:
                self.hormones[name].level = level
