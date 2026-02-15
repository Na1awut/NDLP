"""
LLM Client — Groq API for CareBot

Uses Groq SDK for fast LLM inference.
Models:
  - llama-3.1-8b-instant: สกัดอารมณ์ (fast)
  - llama-3.3-70b-versatile: สร้างคำตอบ (smart)
"""
import os
from typing import Optional
from groq import AsyncGroq


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
FAST_MODEL = "llama-3.1-8b-instant"
SMART_MODEL = "llama-3.3-70b-versatile"


class LLMClient:
    """
    Dual-model Groq LLM client.
    Fast model for emotion extraction, smart model for response generation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.client = AsyncGroq(api_key=self.api_key)

    async def extract_emotion(self, text: str, system_prompt: str) -> Optional[str]:
        """
        สกัดอารมณ์จากข้อความ (ใช้ fast model)
        Returns raw JSON string from LLM
        """
        try:
            response = await self.client.chat.completions.create(
                model=FAST_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LLMClient] Emotion extraction failed: {e}")
            return None

    async def generate_response(
        self,
        user_message: str,
        system_prompt: str,
        evc_context: str = "",
        conversation_history: Optional[list[dict]] = None,
    ) -> str:
        """
        สร้างคำตอบ (ใช้ smart model)
        """
        messages = [{"role": "system", "content": system_prompt}]

        if evc_context:
            messages.append({
                "role": "system",
                "content": f"[EVC Context]\n{evc_context}"
            })

        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append(msg)

        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.completions.create(
                model=SMART_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            return response.choices[0].message.content or "ขอโทษนะ ตอนนี้ตอบไม่ได้"
        except Exception as e:
            print(f"[LLMClient] Response generation failed: {e}")
            return "ขอโทษนะ ระบบมีปัญหาอยู่ ลองใหม่อีกทีนะ 🙏"

    def get_info(self) -> dict:
        """Return client info for debugging"""
        return {
            "provider": "groq",
            "fast_model": FAST_MODEL,
            "smart_model": SMART_MODEL,
            "has_key": bool(self.api_key),
        }
