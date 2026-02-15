"""
EVC Routes — FastAPI endpoints for EVC processing

Endpoints:
  POST /evc/process  — Full EVC pipeline (extract → compute → update → respond)
  GET  /evc/state    — Get current EVC state for a user
  POST /evc/reset    — Reset EVC state to neutral
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import APIRouter, HTTPException

from models.chat_models import ChatRequest, ChatResponse, EVCStateResponse
from models.evc_models import EVCState, EVCResult
from evc.engine import update_evc, create_initial_state
from evc.emotion_extractor import extract_emotion
from evc.rules import get_response_policy
from evc.therapeutic import get_therapeutic_note

router = APIRouter(prefix="/evc", tags=["EVC"])

# These will be injected by main.py
llm_client = None
memory_store = None

# ──────────────────────────────────────────────
# System Prompt for Response Generation
# ──────────────────────────────────────────────
CAREBOT_SYSTEM_PROMPT = """คุณคือ CareBot — AI เพื่อนดูแลใจสำหรับนักเรียนไทย

บทบาทของคุณ:
- เป็นเพื่อนที่รับฟัง ไม่ตัดสิน ไม่สั่งสอน
- พูดภาษาไทยเป็นกันเอง ใช้คำว่า "เรา" แทนตัวเอง
- ตอบสั้นกระชับ ไม่เกิน 3-4 ประโยค
- ถามต่อเพื่อให้เค้าเล่าเพิ่ม
- ถ้าเค้าอยู่ในภาวะวิกฤต ให้ความสำคัญกับความปลอดภัย

สิ่งที่ห้ามทำ:
- ห้ามวินิจฉัยโรค
- ห้ามแนะนำยา
- ห้ามบอกว่า "ไม่เป็นไร" หรือ "คิดบวก"
- ห้ามเปรียบเทียบกับคนอื่น"""


@router.post("/process", response_model=ChatResponse)
async def process_message(request: ChatRequest):
    """
    Full EVC pipeline:
    1. Load EVC state from memory
    2. Extract emotion from message
    3. Update EVC state
    4. Generate response policy
    5. Generate LLM response
    6. Save state + message
    7. Return response
    """
    if not llm_client or not memory_store:
        raise HTTPException(status_code=500, detail="Services not initialized")

    user_id = request.user_id
    message = request.message
    is_dev = os.getenv("APP_ENV") == "development"

    # ── Step 1: Load state ──
    current_state = await memory_store.get_evc_state(user_id)

    # ── Step 2: Extract emotion ──
    emotion = await extract_emotion(message, llm_client)

    # ── Step 3: Update EVC ──
    new_state, forces = update_evc(current_state, emotion)

    # ── Step 4: Response policy ──
    policy = get_response_policy(
        new_state.zone, new_state.phase, new_state.flags, emotion
    )
    therapeutic_note = get_therapeutic_note(
        new_state.E, new_state.delta_E, new_state.turn
    )

    # ── Step 5: Generate response ──
    evc_context = (
        f"สถานะอารมณ์: E={new_state.E:.1f} ({new_state.zone.value}, {new_state.phase.value})\n"
        f"นโยบาย: {policy}\n"
    )
    if therapeutic_note:
        evc_context += f"คำแนะนำ: {therapeutic_note}\n"

    # Get conversation history
    history = await memory_store.get_conversation_history(user_id, limit=10)
    chat_history = []
    for msg in history:
        chat_history.append({"role": "user", "content": msg.get("user_text", "")})
        chat_history.append({"role": "assistant", "content": msg.get("bot_text", "")})

    bot_response = await llm_client.generate_response(
        user_message=message,
        system_prompt=CAREBOT_SYSTEM_PROMPT,
        evc_context=evc_context,
        conversation_history=chat_history,
    )

    # ── Step 6: Save state + message ──
    await memory_store.save_evc_state(user_id, new_state)
    await memory_store.add_message(user_id, {
        "user_text": message,
        "bot_text": bot_response,
        "E": new_state.E,
        "zone": new_state.zone.value,
        "timestamp": datetime.now().isoformat(),
    })

    # ── Step 7: Check crisis alert ──
    alert_triggered = new_state.flags.crisis

    # ── Build response ──
    debug_info = None
    if is_dev:
        debug_info = {
            "emotion": emotion.model_dump(),
            "forces": forces.model_dump(),
            "policy": policy,
            "therapeutic_note": therapeutic_note,
            "provider": llm_client.get_info()["provider"],
        }

    return ChatResponse(
        response=bot_response,
        evc_state={
            "E": round(new_state.E, 2),
            "zone": new_state.zone.value,
            "phase": new_state.phase.value,
            "delta_E": round(new_state.delta_E, 2),
            "turn": new_state.turn,
        },
        alert_triggered=alert_triggered,
        debug=debug_info,
    )


@router.get("/state/{user_id}", response_model=EVCStateResponse)
async def get_state(user_id: str):
    """Get current EVC state for a user"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Memory store not initialized")

    state = await memory_store.get_evc_state(user_id)

    return EVCStateResponse(
        user_id=user_id,
        E=round(state.E, 2),
        zone=state.zone.value,
        phase=state.phase.value,
        delta_E=round(state.delta_E, 2),
        turn=state.turn,
        flags=state.flags.model_dump(),
        timestamp=state.timestamp.isoformat(),
    )


@router.post("/reset/{user_id}")
async def reset_state(user_id: str):
    """Reset EVC state to neutral"""
    if not memory_store:
        raise HTTPException(status_code=500, detail="Memory store not initialized")

    initial = create_initial_state()
    await memory_store.save_evc_state(user_id, initial)

    return {"message": f"EVC state reset for {user_id}", "E": 0.0}
