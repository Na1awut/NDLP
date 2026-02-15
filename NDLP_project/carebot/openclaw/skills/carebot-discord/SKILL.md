---
name: carebot-discord
description: Discord Bot handler for CareBot. Receives messages and slash commands from Discord, processes them through the EVC system, and sends replies in Discord channels or DMs.
---

# CareBot Discord Skill

## When to Use
Use this skill to handle incoming Discord messages and slash commands.

## Bot Setup
The Discord bot uses discord.py library running inside the FastAPI process.
It listens for messages in designated channels and DMs.

## Message Flow
1. Discord bot receives a message or slash command
2. Extract user message and Discord user ID
3. Show typing indicator in the channel
4. Call EVC skill to process the message
5. Reply in the same channel or DM

## Slash Commands
- `/gettoken` — Generate a 6-character linking token (expires in 5 minutes)
- `/link <token>` — Link this Discord account with another platform (e.g., LINE)
- `/status` — Show current emotional state as an embed
- `/reset` — Reset emotional state to neutral (admin only)

## Important Rules
- Use Discord embeds for rich responses when appropriate
- Use Thai language for all responses
- Support both channel messages and DMs
- Show typing indicator during EVC processing
- For DMs, be extra attentive (students may share more privately)
