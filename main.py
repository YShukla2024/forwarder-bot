import os
import re
import asyncio
import unicodedata
from datetime import datetime, timedelta, timezone
from flask import Flask
import threading
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv
from normalizer import normalize_text, parse_signal, format_signal, is_valid_signal

# ================== FLASK KEEPALIVE ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 8000))
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

HEARTBEAT_INTERVAL = 30 * 60  # 30 minutes

# ================== SETTINGS ==================

SOURCE_CHATS = [
    -1001223812798,
    -1002086907376, # XTREME FREE GOLD SIGNALS
    -1001540535352,
    -1001564046986,
    -1002116974051,
    -1002184500107,
    -1003298681349,
    -1001897903474,
    -1002284339674,
    -1001746260985,
    -1001067365629,
    -1001548665510,
    -1001821769537,
    -1002365747286,
    -1001218056271,
    -1001588519179,
    -1001381790914, # Sureshot INDICES
    -1001954127662, # Sureshot FX Vip
    -1001604836510,
    -1001886710177,
    -1002053336035,
    -1001805719691,
    -1002518518156,
    -1002407499797,
    -1002798991586,
    -1002214622470,
    -1001821969165,
    -1002057625630, # FOREX TRADING SIGNAL
    -1001875148578, # FG FOREX GOLD
    -1002762751030, # VASILY TRADER
    -1001590096134, # Gold Trader Avi
    -1002375711533, # David's Gold Strategy
    -1002685861814, # AURICVERSE GOLD
    -1001310831497, # TRADE WITH AHSAN
    -5277876817      # Gold Signal Test
]

PRINT_ALL_MESSAGES = True
SEND_TEST_ON_START = True

client = TelegramClient(StringSession(session_string), api_id, api_hash)

# ================== HEARTBEAT ==================
async def send_heartbeat(target_entity):
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            await client.send_message(target_entity,
                f"💓 BOT ALIVE\n"
                f"📡 Monitoring {len(SOURCE_CHATS)} groups\n"
                f"🕐 {now}"
            )
            print(f"💓 Heartbeat sent at {now}")
        except Exception as e:
            print(f"❌ Heartbeat failed: {e}")

# ================== SIGNAL CHECKER ==================
def is_signal(text):
    if not text:
        return False
    
    # Normalize Unicode characters (converts fancy Unicode to ASCII equivalents)
    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').upper()

    # ❌ EA/broker execution messages
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

    # ❌ TP hit / profit done messages
    if "HIT" in t:
        return False
    if "PROFIT DONE" in t or "PROFIT BOOKED" in t:
        return False
    if "PIPS PROFIT" in t or "PIPS DONE" in t:
        return False
    if "TARGET HIT" in t or "TARGET ACHIEVED" in t:
        return False
    if "TP HIT" in t or "SL HIT" in t:
        return False
    if "CLOSED" in t and "PROFIT" in t:
        return False

    # ❌ "Running in profit / smooth / lock in gains" messages  ✅ NEW
    if "IN PROFIT" in t:
        return False
    if "LOCK IN" in t or "LOCK PROFIT" in t:
        return False
    if "BREAKEVEN" in t or "BREAK EVEN" in t:
        return False
    if "RUNNING SMOOTH" in t or "SETUP RUNNING" in t:
        return False
    if "CLOSE HALF" in t or "HALF PROFIT" in t:
        return False

    # ❌ Pending order / ticket execution messages  ✅ NEW
    if "TICKET:" in t or "TICKET #" in t:
        return False
    if "NEW EXECUTION" in t:
        return False
    if "PENDING" in t and "LOTS:" in t:
        return False
    if "POSITION VALUE" in t:
        return False
    if "SELL STOP" in t or "BUY STOP" in t:
        return False
    if "SELL LIMIT" in t or "BUY LIMIT" in t and "LOTS:" in t:
        return False

    # ❌ Account status / balance messages  ✅ NEW
    if "BALANCE:" in t and "EQUITY:" in t:
        return False
    if "FLOATING:" in t:
        return False
    if "STATUS UPDATE" in t:
        return False
    if "ACCOUNT BALANCE" in t:
        return False

    # ❌ PIPS result messages  ✅ NEW
    if "PIPS" in t and ("+" in t or "-" in t) and ("SELL-" in t or "BUY-" in t):
        return False
    if re.search(r'[+-]\d+\s*PIPS', t):
        return False

    has_direction = re.search(r'\b(BUY|SELL)\b', t)
    has_trade_info = re.search(
        r'(TP|SL|PIPS?|TAKE\s*PROFIT|STOP\s*LOSS|STOPLOSS|TAKEPROFIT)',
        t
    )

    return bool(has_direction and has_trade_info)

# ================== HELPER FUNCTIONS ==================
async def get_chat_name(chat_id):
    """Retrieve the name of a chat/channel by its ID."""
    try:
        entity = await client.get_entity(chat_id)
        return entity.title or entity.first_name or str(chat_id)
    except Exception as e:
        print(f"⚠️ Could not get chat name for {chat_id}: {e}")
        return f"Chat_{chat_id}"


def log_signal(source_chat_id, source_chat_name, symbol, type_, entry, tp, sl, raw_text, missed=False):
    """Log trading signal to file."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "source_chat_id": source_chat_id,
            "source_chat_name": source_chat_name,
            "symbol": symbol,
            "type": type_,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "raw_text": raw_text,
            "missed": missed
        }
        
        with open("signals.log", "a") as f:
            import json
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"📝 Logged signal: {symbol} {type_}")
    except Exception as e:
        print(f"❌ Logging error: {e}")

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
    parsed = parse_signal(test_text)
    await event.reply(
        f"📝 Input: {test_text}\n"
        f"🔄 Normalized: {normalized}\n"
        f"{'✅ WOULD FORWARD' if result else '❌ WOULD BE FILTERED'}\n\n"
        f"📊 Parsed:\n"
        f"Type: {parsed['type']}\n"
        f"Entry: {parsed['entry']}\n"
        f"TP: {parsed['tp']}\n"
        f"SL: {parsed['sl']}"
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

        data = parse_signal(text)
        chat_name = await get_chat_name(chat_id)

        if not data["type"] or not data["entry"]:
            await client.send_message(target_group, text)
            log_signal(chat_id, chat_name, data["symbol"], data["type"],
                      data["entry"], data["tp"], data["sl"], raw_text)
            print(f"✅ Forwarded (raw) from {chat_id}")
            return

        # ✅ Pass chat_name to format_signal
        output = format_signal(data, source=chat_name)
        await client.send_message(target_group, output)

        log_signal(
            source_chat_id=chat_id,
            source_chat_name=chat_name,
            symbol=data["symbol"],
            type_=data["type"],
            entry=data["entry"],
            tp=data["tp"],
            sl=data["sl"],
            raw_text=raw_text,
            missed=False
        )

        print(f"✅ Forwarded (clean) from {chat_id}")

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

    # ✅ Recover missed messages
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

    # ✅ Start heartbeat
    asyncio.ensure_future(send_heartbeat(target_entity))
    print("💓 Heartbeat started (every 30 mins)")

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