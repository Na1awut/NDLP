"""
Bot Emotional State — Empathetic Mirroring (Pacing & Leading)

เลียนแบบเทคนิคจิตวิทยา "Pacing & Leading":
  1. PACE  — Bot ดิ่งลงไปอยู่ระดับเดียวกับ user (mirror)
  2. MATCH — ให้ user รู้สึกว่า "เข้าใจฉัน" (stay close)
  3. LEAD  — ค่อยๆ ดึงอารมณ์ขึ้น (gradually lift)

สมการ:
  mirror_target = E_user × mirror_ratio
  lead_force = lead_rate × max(0, pacing_turns - min_pacing)
  E_bot += smoothing × (mirror_target + lead_force - E_bot)
"""


class BotEmotionalState:
    """
    Bot's own emotional state — separate from user's E.
    Controls the TONE of response, not the content.
    """

    def __init__(
        self,
        mirror_ratio: float = 0.6,   # ดิ่งไป 60% ของ user
        lead_rate: float = 0.4,       # ดึงขึ้น 0.4 ต่อ turn
        min_pacing: int = 2,          # ต้อง pace อย่างน้อย 2 turn
        smoothing: float = 0.5,       # ความเร็วในการเปลี่ยน E_bot
        max_lead: float = 3.0,        # ดึงขึ้นสูงสุด 3.0
    ):
        self.E_bot: float = 0.0
        self.mirror_ratio = mirror_ratio
        self.lead_rate = lead_rate
        self.min_pacing = min_pacing
        self.smoothing = smoothing
        self.max_lead = max_lead

        # Internal tracking
        self.pacing_turns: int = 0     # จำนวน turns ที่ bot pacing อยู่
        self.user_negative_streak: int = 0  # จำนวน turns ที่ user ลบติดต่อ

    def update(self, E_user: float) -> None:
        """
        Update bot emotional state based on user's E.

        Logic:
        - If user is negative → enter pacing mode (mirror down)
        - After min_pacing turns → start leading up
        - If user turns positive → match their energy
        """
        # Track user negative streak
        if E_user < -0.5:
            self.user_negative_streak += 1
            self.pacing_turns += 1
        else:
            self.user_negative_streak = 0
            # Don't reset pacing_turns immediately — gradual transition
            self.pacing_turns = max(0, self.pacing_turns - 1)

        # ── Phase 1: Mirror target ──
        if E_user < 0:
            # PACE: Drop to mirror level (but not as deep as user)
            mirror_target = E_user * self.mirror_ratio
        else:
            # MATCH: When user is positive, mirror positive too
            mirror_target = E_user * 0.8  # 80% of positive

        # ── Phase 2: Leading force ──
        lead_force = 0.0
        if self.pacing_turns >= self.min_pacing and E_user < 0:
            # Start leading up after minimum pacing duration
            lead_turns = self.pacing_turns - self.min_pacing
            lead_force = min(self.max_lead, self.lead_rate * lead_turns)

        # ── Phase 3: Compute target and smooth transition ──
        target = mirror_target + lead_force

        # Smooth approach to target (avoid jarring tone shifts)
        self.E_bot += self.smoothing * (target - self.E_bot)

        # Clamp to reasonable range
        self.E_bot = max(-8.0, min(8.0, self.E_bot))

    def get_tone(self) -> str:
        """
        Map E_bot to a response tone label.

        Returns a tone label that guides the LLM's style of response.
        """
        if self.E_bot < -3.0:
            return "deep_empathy"
        elif self.E_bot < 0.0:
            return "gentle_support"
        elif self.E_bot < 2.0:
            return "soft_encouragement"
        else:
            return "hopeful_lead"

    def get_tone_instruction(self) -> str:
        """
        Get Thai language instruction for LLM based on current tone.

        This is injected into the system prompt to control response style.
        """
        tone = self.get_tone()

        instructions = {
            "deep_empathy": (
                "🎭 โทนเสียง: เสียงอ่อน เข้าใจ\n"
                "- พูดเบาๆ แสดงว่ารู้สึกหนักใจไปด้วย\n"
                "- ไม่ต้องรีบปลอบ ไม่ต้องรีบแก้ปัญหา\n"
                "- ใช้คำเช่น 'เรารู้สึกหนักใจไปด้วยเลย...' 'มันหนักจริงๆ นะ'\n"
                "- ตอบสั้นมาก 1-2 ประโยค แสดงการรับรู้"
            ),
            "gentle_support": (
                "🎭 โทนเสียง: อ่อนโยน ไม่ตัดสิน\n"
                "- อยู่ด้วย รับฟัง ไม่รีบให้คำแนะนำ\n"
                "- ถามเพิ่มเบาๆ เพื่อให้เค้าเล่าต่อ\n"
                "- ใช้คำเช่น 'เล่าเพิ่มได้นะ...' 'เราอยู่ตรงนี้ฟังอยู่'"
            ),
            "soft_encouragement": (
                "🎭 โทนเสียง: ให้กำลังใจเบาๆ\n"
                "- เริ่มชี้จุดดีที่เห็นในตัวเค้า\n"
                "- ชื่นชมความกล้าที่เล่า\n"
                "- ใช้คำเช่น 'เราว่าเค้าเก่งมากนะที่...' 'สังเกตไหมว่า...'"
            ),
            "hopeful_lead": (
                "🎭 โทนเสียง: นำไปข้างหน้า\n"
                "- ชวนคิดเรื่องเป้าหมาย สิ่งที่อยากทำ\n"
                "- พูดถึงอนาคตในแง่บวก\n"
                "- ใช้คำเช่น 'ลองดูด้วยกันไหม?' 'ถ้ามีอะไรอยากลอง...'"
            ),
        }

        return instructions.get(tone, instructions["gentle_support"])

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "E_bot": round(self.E_bot, 3),
            "tone": self.get_tone(),
            "pacing_turns": self.pacing_turns,
            "user_negative_streak": self.user_negative_streak,
        }
