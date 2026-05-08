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

api_id        = int(os.getenv("API_ID"))
api_hash      = os.getenv("API_HASH")
phone         = os.getenv("PHONE")
session_string = os.getenv("SESSION_STRING")

target_group_raw = os.getenv("TARGET_GROUP_ID")
target_group = int(target_group_raw) if target_group_raw.startswith("-100") else target_group_raw

HEARTBEAT_INTERVAL = 30 * 60  # 30 minutes

# ================== SETTINGS ==================

SOURCES_FILE = "sources.json"

DEFAULT_SOURCE_CHATS = [
    -1001223812798,
    -1002086907376,
    -1001540535352,
    -1001564046986,
    -1002184500107,
    -1003298681349,
    -1001897903474,
    -1001746260985,
    -1001821769537,
    -1002365747286,
    -1001604836510,
    -1001886710177,
    -1002053336035,
    -1002407499797,
    -1002214622470,
    -1001821969165,
    -1001560921264,
    -1001325493987,
    -1001477403711,
    -1001782503005,
    -1001943914831,
    -1002057625630,
    -1001875148578,
    -1002762751030,
    -1001590096134,
    -1002375711533,
    -1002685861814,
    -1001310831497,
    -5277876817,
    -1001200882128,
    -1002200425625,
    -1002138960867,
    -1001389726384,
    -1001414558402,
    -1002701771444,
    -1002122493772,
    -1001548594995,
    -1003854485927,
    1001821769537,
    -1003082825084,
    -1001784375097
]

def load_sources() -> list:
    """Load source chat IDs — merge defaults + saved so new deploys add new defaults."""
    import json
    saved = []
    if os.path.exists(SOURCES_FILE):
        try:
            with open(SOURCES_FILE, "r") as f:
                data = json.load(f)
                saved = data.get("chats", [])
        except Exception:
            pass
    # Merge: start with defaults, add any extra saved IDs
    merged = list(DEFAULT_SOURCE_CHATS)
    for cid in saved:
        if cid not in merged:
            merged.append(cid)
    # Save merged back so file stays up to date
    save_sources(merged)
    return merged

def save_sources(chats: list):
    """Save source chat IDs to file."""
    import json
    with open(SOURCES_FILE, "w") as f:
        json.dump({"chats": chats}, f, indent=2)

# Load on startup — always use this instead of SOURCE_CHATS directly
SOURCE_CHATS = load_sources()

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

    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').upper()

    # Fix common typos
    t = t.replace('BUYY', 'BUY').replace('SELLL', 'SELL')
    # Remove Telegram link format [text](url) → keep just text
    import re as _re
    t = _re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    # Remove # from symbol hashtags
    t = t.replace('#', '')

    if "TRADE TYPE:" in t:                                        return False
    if "UPDATE STOP LOSS" in t or "UPDATE TAKE PROFIT" in t:     return False
    if "TRADE CLOSED" in t or "POINTS MOVED" in t:               return False
    if "NEW STOP LOSS:" in t or "NEW TAKE PROFIT:" in t:         return False
    if "TRADE EXECUTED" in t:                                     return False
    if "HIT" in t:                                                return False
    if "PROFIT DONE" in t or "PROFIT BOOKED" in t:               return False
    if "PIPS PROFIT" in t or "PIPS DONE" in t:                   return False
    if "TARGET HIT" in t or "TARGET ACHIEVED" in t:              return False
    if "TP HIT" in t or "SL HIT" in t:                           return False
    if "CLOSED" in t and "PROFIT" in t:                           return False
    if "IN PROFIT" in t:                                          return False
    if "LOCK IN" in t or "LOCK PROFIT" in t:                     return False
    if "BREAKEVEN" in t or "BREAK EVEN" in t:                    return False
    if "RUNNING SMOOTH" in t or "SETUP RUNNING" in t:            return False
    if "CLOSE HALF" in t or "HALF PROFIT" in t:                  return False
    if "TICKET:" in t or "TICKET #" in t:                        return False
    if "NEW EXECUTION" in t:                                      return False
    if "PENDING" in t and "LOTS:" in t:                           return False
    if "POSITION VALUE" in t:                                     return False
    if ("SELL STOP" in t or "BUY STOP" in t) and "LOTS:" in t:   return False
    if ("SELL LIMIT" in t or "BUY LIMIT" in t) and "LOTS:" in t: return False
    if "BALANCE:" in t and "EQUITY:" in t:                        return False
    if "FLOATING:" in t:                                          return False
    if "STATUS UPDATE" in t:                                      return False
    if "ACCOUNT BALANCE" in t:                                    return False
    if "PIPS" in t and ("+" in t or "-" in t) and ("SELL-" in t or "BUY-" in t): return False
    if re.search(r'[+-]\d+\s*PIPS', t):                           return False
    if re.search(r'\d+\s*\+\s*PIPS', t):                          return False
    if re.search(r'TP\s*\d+\s*\d+\s*\+\s*PIPS', t):              return False

    has_direction  = re.search(r'\b(BUY|SELL)\b', t)
    has_trade_info = re.search(
        r'(TP\s*\d*\s*[:\-]?\s*[\d]|SL\s*[:\-]?\s*[\d]|TAKE\s*PROFIT|STOP\s*LOSS|STOPLOSS|TAKEPROFIT|TARGET\s*\d)', t
    )
    return bool(has_direction and has_trade_info)


# ================== HELPERS ==================
async def get_chat_name(chat_id):
    try:
        entity = await client.get_entity(chat_id)
        return entity.title or entity.first_name or str(chat_id)
    except Exception as e:
        print(f"⚠️ Could not get chat name for {chat_id}: {e}")
        return f"Chat_{chat_id}"


def log_signal(source_chat_id, source_chat_name, symbol, type_, entry, tp, sl, raw_text, missed=False):
    try:
        import json
        log_entry = {
            "timestamp":        datetime.now().isoformat(),
            "source_chat_id":   source_chat_id,
            "source_chat_name": source_chat_name,
            "symbol":           symbol,
            "type":             type_,
            "entry":            entry,
            "tp":               tp,
            "sl":               sl,
            "raw_text":         raw_text,
            "missed":           missed,
        }
        with open("signals.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"📝 Logged: {symbol} {type_}")
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
            print("ID:  ", event.chat_id)
            print("TEXT:", event.message.message)
            print("-" * 50)
        except Exception as e:
            print("❌ Debug error:", e)


# ================== COMMAND HANDLERS ==================
@client.on(events.NewMessage(outgoing=True, pattern=r'^/test$'))
async def cmd_test(event):
    try:
        await client.send_message(target_group,
            "🧪 TEST SIGNAL\nXAUUSD BUY 1900\nTP1: 1910\nSL: 1890"
        )
        await event.reply("✅ Test signal sent!")
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


@client.on(events.NewMessage(outgoing=True, pattern=r'^/check (.+)'))
async def cmd_check(event):
    test_text  = event.pattern_match.group(1)
    normalized = normalize_text(test_text)
    result     = is_signal(normalized)
    parsed     = parse_signal(normalized)
    preview    = format_signal(parsed, source="[check]") if result else "❌ Would be filtered"

    await event.reply(
        f"📝 Input: {test_text}\n"
        f"🔄 Normalized: {normalized}\n"
        f"{'✅ WOULD FORWARD' if result else '❌ WOULD BE FILTERED'}\n\n"
        f"📊 Parsed:\n"
        f"  Symbol: {parsed.get('symbol', 'N/A')}\n"
        f"  Type:   {parsed['type']}\n"
        f"  Entry:  {parsed['entry']}\n"
        f"  TP:     {parsed['tp']}\n"
        f"  SL:     {parsed['sl'] or '(auto ~$10)'}\n\n"
        f"📤 Preview:\n{preview}"
    )



# ================== CHAT MANAGEMENT COMMANDS ==================
@client.on(events.NewMessage(pattern=r'^/addchat\s+(-?\d+)(?:\s+(.+))?$'))
async def cmd_addchat(event):
    global SOURCE_CHATS
    chat_id = int(event.pattern_match.group(1))
    label   = event.pattern_match.group(2) or ""
    if chat_id in SOURCE_CHATS:
        await client.send_message(target_group, f"⚠️ Already exists: {chat_id}")
        return
    SOURCE_CHATS.append(chat_id)
    save_sources(SOURCE_CHATS)
    await client.send_message(target_group, f"✅ Added: {chat_id} {label}\nTotal: {len(SOURCE_CHATS)} sources")
    print(f"➕ Added source: {chat_id} {label}")

@client.on(events.NewMessage(pattern=r'^/removechat\s+(-?\d+)$'))
async def cmd_removechat(event):
    global SOURCE_CHATS
    chat_id = int(event.pattern_match.group(1))
    if chat_id not in SOURCE_CHATS:
        await client.send_message(target_group, f"❌ Not found: {chat_id}")
        return
    SOURCE_CHATS.remove(chat_id)
    save_sources(SOURCE_CHATS)
    await client.send_message(target_group, f"✅ Removed: {chat_id}\nTotal: {len(SOURCE_CHATS)} sources")
    print(f"➖ Removed source: {chat_id}")

@client.on(events.NewMessage(pattern=r'^/addchats\s+([\d\s\-]+)$'))
async def cmd_addchats(event):
    global SOURCE_CHATS
    raw = event.pattern_match.group(1)
    ids = [int(x.strip()) for x in raw.split() if x.strip().lstrip("-").isdigit()]
    added, already = [], []
    for cid in ids:
        if cid in SOURCE_CHATS:
            already.append(cid)
        else:
            SOURCE_CHATS.append(cid)
            added.append(cid)
    if added:
        save_sources(SOURCE_CHATS)
    lines = []
    if added:
        lines.append(f"✅ Added {len(added)}: {' '.join(str(c) for c in added)}")
    if already:
        lines.append(f"⚠️ Already exists: {' '.join(str(c) for c in already)}")
    lines.append(f"📋 Total: {len(SOURCE_CHATS)}")
    await client.send_message(target_group, "\n".join(lines))
    print(f"➕ Bulk added: {added}")

@client.on(events.NewMessage(pattern=r'^/removechats\s+([\d\s\-]+)$'))
async def cmd_removechats(event):
    global SOURCE_CHATS
    raw = event.pattern_match.group(1)
    ids = [int(x.strip()) for x in raw.split() if x.strip().lstrip("-").isdigit()]
    removed, not_found = [], []
    for cid in ids:
        if cid in SOURCE_CHATS:
            SOURCE_CHATS.remove(cid)
            removed.append(cid)
        else:
            not_found.append(cid)
    if removed:
        save_sources(SOURCE_CHATS)
    lines = []
    if removed:
        lines.append(f"✅ Removed {len(removed)}: {' '.join(str(c) for c in removed)}")
    if not_found:
        lines.append(f"❌ Not found: {' '.join(str(c) for c in not_found)}")
    lines.append(f"📋 Total remaining: {len(SOURCE_CHATS)}")
    await client.send_message(target_group, "\n".join(lines))
    print(f"➖ Bulk removed: {removed}")

@client.on(events.NewMessage(pattern=r'^/listchats$'))
async def cmd_listchats(event):
    if not SOURCE_CHATS:
        await client.send_message(target_group, "📋 No source chats configured.")
        return
    lines = [f"📋 Source Chats ({len(SOURCE_CHATS)} total):\n"]
    for i, cid in enumerate(SOURCE_CHATS, 1):
        lines.append(f"{i}. {cid}")
    await client.send_message(target_group, "\n".join(lines))

# ================== MAIN HANDLER ==================
@client.on(events.NewMessage)
async def handler(event):
    try:
        chat_id = event.chat_id

        raw_text = event.message.message or ""
        if not raw_text.strip():
            return

        # Allow /addchat, /removechat, /listchats from anywhere
        if raw_text.startswith("/"):
            return

        if chat_id not in SOURCE_CHATS:
            return

        text = normalize_text(raw_text)
        if not is_signal(text):
            return

        data      = parse_signal(text)
        chat_name = await get_chat_name(chat_id)

        if not data["type"] or not data["entry"]:
            await client.send_message(target_group, text)
            log_signal(chat_id, chat_name, data.get("symbol"), data["type"],
                       data["entry"], data["tp"], data["sl"], raw_text)
            print(f"✅ Forwarded (raw) from {chat_id}")
            return

        # format_signal handles missing SL automatically (~$10 default)
        output = format_signal(data, source=chat_name)
        await client.send_message(target_group, output)

        log_signal(
            source_chat_id=chat_id, source_chat_name=chat_name,
            symbol=data.get("symbol"), type_=data["type"],
            entry=data["entry"], tp=data["tp"], sl=data["sl"],
            raw_text=raw_text, missed=False,
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
                f"🟢 BOT STARTED\n"
                f"📡 Listening to signal sources...\n"
                f"📋 Monitoring {len(SOURCE_CHATS)} groups"
            )
            print("✅ Start message sent")
        except Exception as e:
            print("❌ Send failed:", e)

    # Recover missed messages (last 30 mins)
    print("🔄 Checking missed messages (last 30 mins)...")
    cutoff    = datetime.now(timezone.utc) - timedelta(minutes=30)
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
                    data      = parse_signal(text)
                    chat_name = await get_chat_name(chat_id)
                    output    = format_signal(data, source=chat_name)
                    await client.send_message(target_group, f"📬 MISSED SIGNAL\n\n{output}")
                    recovered += 1
                    print(f"📬 Recovered from {chat_id}")
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Missed check failed {chat_id}: {e}")

    print(f"{'✅ No missed signals' if recovered == 0 else f'📬 Recovered {recovered} signals'}")

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
                "🔴 BOT STOPPED\n⚠️ Signal forwarding is paused.\n🔁 Restart the bot."
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