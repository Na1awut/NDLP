---
name: carebot-line
description: LINE Bot message handler for CareBot. Receives messages from LINE Messaging API webhook, processes them through the EVC system, and sends replies back to the LINE user.
---

# CareBot LINE Skill

## When to Use
Use this skill to handle incoming LINE messages and send replies.

## Webhook Setup
The FastAPI backend handles LINE webhook at: `POST /webhook/line`
LINE must be configured to send events to this endpoint.

## Message Flow
1. LINE sends webhook event to `/webhook/line`
2. FastAPI verifies the signature using LINE Channel Secret
3. Extract user message and LINE user ID
4. Send typing indicator to show "กำลังพิมพ์..."
5. Call EVC skill to process the message
6. Reply to user via LINE Reply API

## Commands
- `/gettoken` — Generate a 6-character linking token (expires in 5 minutes)
- `/link <token>` — Link this LINE account with another platform (e.g., Discord)
- `/status` — Show current emotional state summary
- Normal messages — Process through EVC pipeline

## Important Rules
- Always reply within 30 seconds (LINE timeout)
- Send typing indicator immediately while processing
- Use Thai language for all responses
- Keep responses under 500 characters for LINE readability
