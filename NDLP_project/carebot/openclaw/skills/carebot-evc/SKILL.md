---
name: carebot-evc
description: Emotional Vector Control (EVC) engine for analyzing user emotions and generating empathetic responses. This skill processes incoming messages through the EVC pipeline to determine emotional state and appropriate response policy.
---

# CareBot EVC Skill

## When to Use
Use this skill whenever a user sends a message that needs emotional analysis and an empathetic response. This is the core skill that powers CareBot's emotional intelligence.

## How It Works
1. Receive user message from LINE or Discord
2. Call the EVC FastAPI backend at `http://localhost:8000/evc/process`
3. The backend will:
   - Extract emotion features using GROK 8b model
   - Compute Support (S), Drag (D), and Sensitivity (K) forces
   - Update emotional energy E using the EVC equation
   - Classify zone and phase
   - Generate response policy
   - Generate emotionally-aware response using GROK 70b model
4. Return the response to the user

## API Call
```bash
curl -X POST http://localhost:8000/evc/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user_id>",
    "platform": "<line|discord>",
    "message": "<user_message>"
  }'
```

## Response Format
The API returns:
```json
{
  "response": "Bot's reply text",
  "evc_state": {
    "E": 2.5,
    "zone": "Positive",
    "phase": "Rising"
  },
  "alert": false
}
```

## Important Rules
- Always check the `alert` field — if `true`, trigger the carebot-alert skill
- Respond in Thai (ภาษาไทย) by default
- Match the emotional tone based on the zone:
  - ExtremeNegative: gentle, protective
  - Negative: warm, empathetic
  - Neutral: friendly, natural
  - Positive: enthusiastic
  - OverheatPositive: warm but with boundaries
