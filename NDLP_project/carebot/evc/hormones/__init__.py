"""
Hormone Base — Foundation class for all hormones in EVC v4

Each hormone has:
  - level: current concentration (0.0 - 10.0)
  - half_life: turns until level halves naturally
  - max_production: maximum production per turn from stimuli
  - decay_rate: computed from half_life = 0.5^(1/half_life)
"""
import math
from dataclasses import dataclass, field


@dataclass
class HormoneBase:
    """Base class for all 8 hormones in the Hormonal Emotional Model."""

    name: str
    level: float = 0.0
    half_life: int = 4          # turns until level halves
    max_production: float = 3.0  # max added per turn
    baseline: float = 2.0       # resting level (homeostasis target)

    @property
    def decay_rate(self) -> float:
        """Decay multiplier per turn: 0.5^(1/half_life)"""
        return math.pow(0.5, 1.0 / self.half_life)

    def decay(self) -> None:
        """Apply natural decay toward baseline."""
        # Decay toward baseline, not toward zero
        diff = self.level - self.baseline
        diff *= self.decay_rate
        self.level = self.baseline + diff

    def produce(self, stimulus: float) -> None:
        """
        Produce hormone based on stimulus intensity (0.0 - 1.0).
        Stimulus is mapped from EmotionFeatures in each subclass.
        """
        production = stimulus * self.max_production
        self.level = min(10.0, self.level + production)

    def suppress(self, amount: float) -> None:
        """Suppress hormone level by amount (from cross-hormone interaction)."""
        self.level = max(0.0, self.level - amount)

    def stimulate(self, amount: float) -> None:
        """Stimulate hormone level by amount (from cross-hormone interaction)."""
        self.level = min(10.0, self.level + amount)

    def get_normalized(self) -> float:
        """Get level normalized to 0.0 - 1.0 range."""
        return self.level / 10.0

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "name": self.name,
            "level": round(self.level, 3),
            "baseline": self.baseline,
            "half_life": self.half_life,
        }
