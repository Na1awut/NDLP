"""
EVC Emotion Extractor — LLM-based emotion extraction using GROK 8b

Primary:   GROK llama-3.1-8b-instant → structured JSON
Fallback:  Rule-based Thai/English keyword matching
"""
import json
import re
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.evc_models import EmotionFeatures, Intent


# ──────────────────────────────────────────────
# GROK LLM Extraction Prompt
# ──────────────────────────────────────────────
EXTRACTION_PROMPT = """คุณเป็นผู้เชี่ยวชาญด้านการวิเคราะห์อารมณ์จากข้อความ (ทั้งภาษาไทยและอังกฤษ)

วิเคราะห์ข้อความผู้ใช้แล้วตอบเป็น JSON เท่านั้น:

{
  "valence": <float -1.0 ถึง 1.0>,
  "arousal": <float 0.0 ถึง 1.0>,
  "dominance": <float 0.0 ถึง 1.0>,
  "intent": "<greeting|venting|seeking_help|praise|apology|sarcasm|aggression|neutral|farewell>",
  "sarcasm_prob": <float 0.0 ถึง 1.0>,
  "support_need": <float 0.0 ถึง 1.0>,
  "uncertainty": <float 0.0 ถึง 1.0>,
  "confidence": <float 0.0 ถึง 1.0>
}

คำอธิบาย:
- valence: ขั้วอารมณ์ (-1=ลบสุด, 0=กลาง, +1=บวกสุด)
- arousal: ระดับตื่นตัว (0=สงบ, 1=ตื่นเต้น/เร้าอารมณ์)
- dominance: ระดับควบคุม (0=ยอมจำนน/ขอความช่วยเหลือ, 1=ควบคุม/สั่งการ)
- intent: จุดประสงค์หลักของข้อความ
- sarcasm_prob: ความน่าจะเป็นของการประชด/เสียดสี
- support_need: ความต้องการการสนับสนุน/ปลอบใจ
- uncertainty: ความไม่มั่นใจของผู้ใช้ในข้อความ
- confidence: ความมั่นใจของคุณในการวิเคราะห์

⚠️ ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น"""


async def extract_with_GROK(text: str, GROK_client) -> Optional[EmotionFeatures]:
    """
    สกัดอารมณ์ผ่าน GROK llama-3.1-8b-instant
    คืน None ถ้าล้มเหลว (จะ fallback เป็น rule-based)
    """
    try:
        response = await GROK_client.extract_emotion(text, EXTRACTION_PROMPT)

        if response is None:
            return None

        # Parse JSON from response
        json_str = response.strip()
        # Handle markdown code blocks
        if "```" in json_str:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

        data = json.loads(json_str)

        # Validate intent
        valid_intents = [i.value for i in Intent]
        intent_str = data.get("intent", "neutral")
        if intent_str not in valid_intents:
            intent_str = "neutral"

        return EmotionFeatures(
            valence=max(-1.0, min(1.0, float(data.get("valence", 0.0)))),
            arousal=max(0.0, min(1.0, float(data.get("arousal", 0.5)))),
            dominance=max(0.0, min(1.0, float(data.get("dominance", 0.5)))),
            intent=Intent(intent_str),
            sarcasm_prob=max(0.0, min(1.0, float(data.get("sarcasm_prob", 0.0)))),
            support_need=max(0.0, min(1.0, float(data.get("support_need", 0.5)))),
            uncertainty=max(0.0, min(1.0, float(data.get("uncertainty", 0.3)))),
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        )

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        print(f"[EVC] GROK extraction failed: {e}")
        return None


# ──────────────────────────────────────────────
# Rule-based Fallback (Thai + English keywords)
# ──────────────────────────────────────────────

# Thai keywords
POSITIVE_WORDS_TH = [
    "ดีใจ", "สนุก", "ชอบ", "รัก", "ยินดี", "ขอบคุณ",
    "เยี่ยม", "สุดยอด", "น่ารัก", "มีความสุข", "สบายดี",
    "ผ่อนคลาย", "สำเร็จ", "ภูมิใจ", "ดีมาก", "เก่ง",
]

NEGATIVE_WORDS_TH = [
    "เครียด", "เศร้า", "เบื่อ", "โกรธ", "เจ็บ", "ผิดหวัง",
    "กลัว", "กังวล", "ท้อ", "เหนื่อย", "หมดแรง", "ทุกข์",
    "เสียใจ", "หดหู่", "ไม่ไหว", "อยากตาย", "ไม่มีค่า",
    "น่าอาย", "แย่", "ล้มเหลว", "โดดเดี่ยว",
]

SARCASM_WORDS_TH = [
    "เหรอ", "จริงดิ", "ใช่สิ", "แน่นอน", "ดีจริง",
    "เก่งจัง", "น่าอิจฉา", "สุดยอดเลย",
]

GREETING_WORDS_TH = ["สวัสดี", "หวัดดี", "ดีครับ", "ดีค่ะ", "ว่าไง"]
FAREWELL_WORDS_TH = ["บาย", "ลาก่อน", "ไปก่อน", "ไปละ"]
HELP_WORDS_TH = ["ช่วย", "ขอ", "แนะนำ", "ทำไง", "ยังไง"]

# English keywords
POSITIVE_WORDS_EN = [
    "happy", "good", "great", "love", "thank", "nice",
    "awesome", "amazing", "wonderful", "excited", "proud",
]

NEGATIVE_WORDS_EN = [
    "sad", "angry", "stressed", "tired", "hate", "afraid",
    "worried", "depressed", "hopeless", "lonely", "hurt",
    "exhausted", "disappointed", "anxious", "scared",
]

SARCASM_WORDS_EN = [
    "sure", "yeah right", "oh great", "wonderful",
    "how nice", "obviously",
]


def _count_matches(text: str, words: list[str]) -> int:
    """Count how many keywords appear in text"""
    text_lower = text.lower()
    return sum(1 for w in words if w in text_lower)


def extract_rule_based(text: str) -> EmotionFeatures:
    """
    Rule-based fallback emotion extraction (Thai + English)
    ใช้เมื่อ GROK ล้มเหลว
    """
    text_lower = text.lower()

    # ─── Valence ───
    pos_count = _count_matches(text, POSITIVE_WORDS_TH + POSITIVE_WORDS_EN)
    neg_count = _count_matches(text, NEGATIVE_WORDS_TH + NEGATIVE_WORDS_EN)
    total = pos_count + neg_count
    if total > 0:
        valence = (pos_count - neg_count) / total
    else:
        valence = 0.0

    # ─── Arousal ───
    exclamation_count = text.count("!") + text.count("!!")
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    arousal = min(1.0, 0.3 + exclamation_count * 0.15 + caps_ratio * 0.5)

    # ─── Sarcasm ───
    sarcasm_count = _count_matches(text, SARCASM_WORDS_TH + SARCASM_WORDS_EN)
    sarcasm_prob = min(1.0, sarcasm_count * 0.3)

    # ─── Intent ───
    if _count_matches(text, GREETING_WORDS_TH + ["hello", "hi", "hey"]) > 0:
        intent = Intent.GREETING
    elif _count_matches(text, FAREWELL_WORDS_TH + ["bye", "goodbye"]) > 0:
        intent = Intent.FAREWELL
    elif _count_matches(text, HELP_WORDS_TH + ["help", "please", "how"]) > 0:
        intent = Intent.SEEKING_HELP
    elif sarcasm_prob > 0.5:
        intent = Intent.SARCASM
    elif neg_count > 2:
        intent = Intent.VENTING
    elif pos_count > 2:
        intent = Intent.PRAISE
    else:
        intent = Intent.NEUTRAL

    # ─── Dominance ───
    command_words = ["ทำ", "ไป", "หยุด", "ต้อง", "do", "go", "stop", "must"]
    submit_words = ["ช่วย", "ขอ", "please", "help"]
    dom_up = _count_matches(text, command_words)
    dom_down = _count_matches(text, submit_words)
    dominance = max(0.0, min(1.0, 0.5 + (dom_up - dom_down) * 0.15))

    # ─── Support need ───
    support_need = max(0.0, min(1.0, 0.5 + neg_count * 0.15 - pos_count * 0.1))

    # ─── Uncertainty ───
    uncertain_words = ["ไม่รู้", "ไม่แน่ใจ", "มั้ง", "คงจะ", "maybe", "not sure", "idk"]
    uncertainty = min(1.0, _count_matches(text, uncertain_words) * 0.25 + 0.2)

    return EmotionFeatures(
        valence=round(valence, 3),
        arousal=round(arousal, 3),
        dominance=round(dominance, 3),
        intent=intent,
        sarcasm_prob=round(sarcasm_prob, 3),
        support_need=round(support_need, 3),
        uncertainty=round(uncertainty, 3),
        confidence=0.4,  # lower confidence for rule-based
    )


# ──────────────────────────────────────────────
# Main Extraction Function
# ──────────────────────────────────────────────
async def extract_emotion(text: str, GROK_client=None) -> EmotionFeatures:
    """
    สกัดอารมณ์จากข้อความ
    Primary: GROK LLM → Fallback: Rule-based
    """
    if GROK_client is not None:
        result = await extract_with_GROK(text, GROK_client)
        if result is not None:
            return result

    # Fallback to rule-based
    return extract_rule_based(text)
