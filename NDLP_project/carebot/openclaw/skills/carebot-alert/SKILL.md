---
name: carebot-alert
description: Crisis alert system that notifies teachers when a student's emotional energy drops to critical levels (E ≤ -6). Sends notifications via LINE Notify to designated teacher accounts.
---

# CareBot Alert Skill

## When to Use
Use this skill when the EVC system detects that a student's emotional energy E has dropped to -6 or below (ExtremeNegative zone / CrashRecovery phase).

## How It Works
1. Triggered automatically when EVC response contains `"alert": true`
2. Call the alert API:
```bash
curl -X POST http://localhost:8000/alert/send \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<student_user_id>",
    "E": -7.2,
    "zone": "ExtremeNegative",
    "platform": "line",
    "reason": "Student emotional energy critically low"
  }'
```

## Alert Actions
- Send LINE Notify to the assigned teacher
- Log the alert in the dashboard
- Do NOT tell the student that a teacher was notified (maintain trust)

## Important Rules
- Only trigger when E ≤ -6
- Rate limit: max 1 alert per student per 6 hours
- The student's conversation should continue normally with extra care
