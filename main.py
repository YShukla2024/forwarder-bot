import os  # ✅ sabse pehle
import re
import asyncio
from datetime import datetime, timedelta, timezone
from flask import Flask
import threading
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 8000))  # ✅ ab os available hai
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ================== LOAD CONFIG ==================
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")
session_string = os.getenv("SESSION_STRING")

target_group_raw = os.getenv("TARGET_GROUP_ID")
target_group = int(target_group_raw) if target_group_raw.startswith("-100") else target_group_raw

# ================== SETTINGS ==================

SOURCE_CHATS = [
    -1001223812798,
    -1002086907376,
    -1001540535352,
    -1001564046986,
    -1002116974051,
    -1002184500107,
    -1003298681349,
    -1001897903474,
    -1002284339674,
    -1001746260985,
    -1001428572098,
    -1001067365629,
    -1001548665510,
    -1001821769537,
    -1002365747286,
    -1001218056271,
    -1001588519179,
    -1001381790914,
    -1001954127662,
    -1001604836510,
    -1001886710177,
    -1002053336035,
    -1001805719691,
    -1001875148578,  # FG FOREX GOLD
    -5277876817
]

PRINT_ALL_MESSAGES = True
SEND_TEST_ON_START = True

client = TelegramClient(StringSession(session_string), api_id, api_hash)

# ================== NORMALIZE ==================

def normalize_text(text):
    return (
        text.replace("¹", "1")
            .replace("²", "2")
            .replace("³", "3")
            .replace("⁴", "4")
            .replace("⁵", "5")
            .replace("⁶", "6")
            .replace("⁷", "7")
            .replace("⁸", "8")
            .replace("⁹", "9")
            .replace("：", " ")
            .replace("–", "-")
            .replace("—", "-")
    )

# ================== SIGNAL CHECKER ==================

def is_signal(text):
    if not text:
        return False
    t = text.upper()

    if "TRADE TYPE:" in t:
        return False
    if "UPDATE STOP LOSS" in t or "UPDATE TAKE PROFIT" in t:
        return False
    if "TRADE CLOSED" in t or "POINTS MOVED" in t:
        return False
    if "NEW STOP LOSS:" in t or "NEW TAKE PROFIT:" in t:
        return False
    if "TRADE EXECUTED" in t:
        return False

    has_direction = re.search(r'\b(BUY|SELL)\b', t)
    has_trade_info = re.search(
        r'\b(TP|SL|PIPS?|TAKE\s*PROFIT|STOP\s*LOSS|STOPLOSS|TAKEPROFIT)\b',
        t
    )

    return bool(has_direction and has_trade_info)

# ================== DEBUG LOGGER ==================
@client.on(events.NewMessage)
async def debug_logger(event):
    if PRINT_ALL_MESSAGES:
        try:
            chat = await event.get_chat()
            print("\n📩 NEW MESSAGE")
            print("CHAT:", getattr(chat, "title", "Unknown"))
            print("ID:", event.chat_id)
            print("TEXT:", event.message.message)
            print("-" * 50)
        except Exception as e:
            print("❌ Debug error:", e)

# ================== COMMAND HANDLER ==================
@client.on(events.NewMessage(outgoing=True, pattern=r'^/test$'))
async def cmd_test(event):
    try:
        await client.send_message(target_group,
            "🧪 TEST SIGNAL\n"
            "XAUUSD BUY 1900\n"
            "TP1: 1910\n"
            "SL: 1890"
        )
        await event.reply("✅ Test signal sent to target group!")
        print("🧪 Manual test triggered")
    except Exception as e:
        await event.reply(f"❌ Test failed: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/status$'))
async def cmd_status(event):
    await event.reply(
        f"🟢 Bot is running\n"
        f"📋 Monitoring {len(SOURCE_CHATS)} source groups\n"
        f"🎯 Target: {target_group}"
    )
    print("📊 Status check triggered")

@client.on(events.NewMessage(outgoing=True, pattern=r'^/check (.+)'))
async def cmd_check(event):
    test_text = event.pattern_match.group(1)
    normalized = normalize_text(test_text)
    result = is_signal(normalized)
    await event.reply(
        f"📝 Input: {test_text}\n"
        f"🔄 Normalized: {normalized}\n"
        f"{'✅ WOULD FORWARD' if result else '❌ WOULD BE FILTERED'}"
    )

# ================== MAIN HANDLER ==================
@client.on(events.NewMessage)
async def handler(event):
    try:
        chat_id = event.chat_id

        if chat_id not in SOURCE_CHATS:
            return

        raw_text = event.message.message or ""
        if not raw_text.strip():
            return

        if raw_text.startswith("/"):
            return

        text = normalize_text(raw_text)

        if not is_signal(text):
            return

        await client.send_message(target_group, text)
        print(f"✅ Forwarded from {chat_id}")

    except Exception as e:
        print("❌ Error:", e)

# ================== MAIN ==================
async def main():
    await client.start()

    print("🔄 Loading sources...")
    for chat_id in SOURCE_CHATS:
        try:
            await client.get_entity(chat_id)
            print("✅ Loaded:", chat_id)
        except Exception as e:
            print("❌ Failed:", chat_id, e)

    target_entity = await client.get_entity(target_group)
    print("🎯 Target:", target_entity.title)

    if SEND_TEST_ON_START:
        try:
            await client.send_message(target_entity,
                "🟢 BOT STARTED\n"
                "📡 Listening to signal sources...\n"
                f"📋 Monitoring {len(SOURCE_CHATS)} groups"
            )
            print("✅ Start message sent")
        except Exception as e:
            print("❌ Send failed:", e)

    print("🔄 Checking missed messages (last 30 mins)...")
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    recovered = 0

    for chat_id in SOURCE_CHATS:
        try:
            async for msg in client.iter_messages(chat_id, limit=20):
                if msg.date < cutoff:
                    break
                if not msg.text or not msg.text.strip():
                    continue
                text = normalize_text(msg.text)
                if is_signal(text):
                    await client.send_message(target_group,
                        f"📬 MISSED SIGNAL\n\n{text}"
                    )
                    recovered += 1
                    print(f"📬 Recovered from {chat_id}")
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Missed check failed {chat_id}: {e}")

    if recovered == 0:
        print("✅ No missed signals found")
    else:
        print(f"📬 Recovered {recovered} missed signals")

    print("🚀 Listening...")

    try:
        await client.run_until_disconnected()
    except asyncio.CancelledError:
        pass
    finally:
        print("⚠️ Sending stop message...")
        try:
            if not client.is_connected():
                await client.connect()
            await client.send_message(target_entity,
                "🔴 BOT STOPPED\n"
                "⚠️ Signal forwarding is paused.\n"
                "🔁 Restart the bot."
            )
            print("✅ Stop message sent")
        except Exception as e:
            print("❌ Could not send stop message:", e)
        finally:
            await client.disconnect()

# ================== RUN ==================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⚠️ Stopped by user (Ctrl+C)")