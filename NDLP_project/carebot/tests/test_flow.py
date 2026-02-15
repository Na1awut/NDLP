"""Test: EVC v4 Hormonal Flow — Multi-turn with hormone levels + bot mirroring"""
import requests
import time

API = "http://127.0.0.1:8000"
USER = "flow-test-v4"

# Reset first
requests.post(f"{API}/evc/reset/{USER}", timeout=5)
print("=== EVC v4 Hormonal Flow Test ===\n")

messages = [
    "วันนี้เครียดมากเลย สอบไม่ผ่าน",
    "อ่านหนังสือหนักมากแต่ก็ไม่ไหว ท้อจัง",
    "แต่เพื่อนบอกว่าจะช่วยติว ก็ดีขึ้นนิดนึง",
    "ขอบคุณนะที่รับฟัง รู้สึกดีขึ้นเยอะ",
    "วันนี้สอบผ่านแล้ว ดีใจมากเลย!",
]

# Header
print(f"{'Turn':<5} {'E_user':>7} {'E_bot':>7} {'Tone':<20} {'State':<12} {'Zone':<10} {'Phase':<12}")
print("-" * 90)

for i, msg in enumerate(messages, 1):
    r = requests.post(f"{API}/evc/process", json={
        "user_id": USER,
        "platform": "web",
        "message": msg,
    }, timeout=30).json()

    evc = r["evc_state"]
    d = r.get("debug", {})
    bot = d.get("bot", {})
    hormones = d.get("hormones", {})
    dom = d.get("dominant_state", "?")

    print(f"{i:<5} {evc['E']:>+7.2f} {bot.get('E_bot', 0):>+7.2f} {bot.get('tone', '?'):<20} {dom:<12} {evc['zone']:<10} {evc['phase']:<12}")

    # Show hormone levels
    if hormones:
        h_str = "  H: "
        for name, level in hormones.items():
            short = name[:4].upper()
            h_str += f"{short}={level:.1f} "
        print(h_str)

    # Show bot response
    resp = r.get("response", "")
    if len(resp) > 60:
        resp = resp[:60] + "..."
    print(f"  → {resp}")
    print()

    time.sleep(1)

print("=== Done ===")
