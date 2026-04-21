import os
import re
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv

# ================== LOAD CONFIG ==================
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

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
    -1001821769537,#TESLA TRADERS XAU
    -1002365747286,#Hifaz’s Trading Club
    -5277876817
]

PRINT_ALL_MESSAGES = True
SEND_TEST_ON_START = True

client = TelegramClient("session", api_id, api_hash)

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
            .replace("：", " ")   # fullwidth colon → space
            .replace("–", "-")    # en-dash → hyphen
            .replace("—", "-")    # em-dash → hyphen
    )

# ================== SIGNAL CHECKER ==================

def is_signal(text):
    if not text:
        return False
    t = text.upper()

    # ❌ Block EA bot execution/update messages
    if "TRADE TYPE:" in t:
        return False
    if "UPDATE STOP LOSS" in t or "UPDATE TAKE PROFIT" in t:
        return False
    if "TRADE CLOSED" in t or "POINTS MOVED" in t:
        return False
    if "NEW STOP LOSS:" in t or "NEW TAKE PROFIT:" in t:
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

        # ✅ Normalize first
        text = normalize_text(raw_text)

        if not is_signal(text):
            return

        # ✅ Forward normalized text
        await client.send_message(target_group, text)
        print(f"✅ Forwarded from {chat_id}")

    except Exception as e:
        print("❌ Error:", e)

# ================== MAIN ==================
async def main():
    await client.start(phone)

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
            result = await client.send_message(target_entity, "🚀 BOT STARTED")
            print("✅ Test message sent:", result.id)
        except Exception as e:
            print("❌ Send failed:", e)

    print("🚀 Listening...")
    await client.run_until_disconnected()
# ================== RUN ==================
if __name__ == "__main__":
    asyncio.run(main())
