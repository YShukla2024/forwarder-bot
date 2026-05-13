import re

# ================== NORMALIZE ==================
def normalize_text(text: str) -> str:
    import re as _re

    # Step 1: Remove Telegram hyperlink format [label](url) → keep label only
    text = _re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Step 2: Remove markdown bold/italic asterisks
    text = _re.sub(r'\*+', ' ', text)

    # Step 3: Extract symbol from hashtag BEFORE any unicode stripping
    text = _re.sub(r'#([A-Za-z]{2,10})', lambda m: " " + m.group(1) + " ", text)

    # Step 4: Fix SHORT → SELL, LONG → BUY
    text = _re.sub(r'\bSHORT\b', 'SELL', text, flags=_re.IGNORECASE)
    text = _re.sub(r'\bLONG\b',  'BUY',  text, flags=_re.IGNORECASE)

    # Step 5: Fix BUY/SELL typos
    text = _re.sub(r'BUYY+',    'BUY',  text, flags=_re.IGNORECASE)
    text = _re.sub(r'SELL{2,}', 'SELL', text, flags=_re.IGNORECASE)

    # Step 6: Fix TP. / SL. dot separator
    text = _re.sub(r'\b(TP\s*\d*)\.\s*', r'\1 ', text, flags=_re.IGNORECASE)
    text = _re.sub(r'\b(SL)\.\s*',        r'\1 ', text, flags=_re.IGNORECASE)

    # Step 7: Fix 4716.4718 (two prices joined by dot) → 4716-4718
    text = _re.sub(r'(\b\d{4,})\.(\d{4,}\b)', r'\1-\2', text)

    # Step 7b: Fix short range "4693-95" → "4693-4695" (complete prefix)
    def expand_short_range(m):
        full = m.group(1)
        short = m.group(2)
        prefix = full[:len(full)-len(short)]
        return full + '-' + prefix + short
    text = _re.sub(r'(\b\d{4,})-(\d{2}\b)', expand_short_range, text)

    # Step 8: Strip emojis — replace non-ASCII with space
    text = "".join(ch if ord(ch) < 128 else " " for ch in text)

    # Step 9: Add spaces around keywords glued to numbers
    text = _re.sub(r'(\d)(SL|TP|BUY|SELL)', r'\1 \2', text, flags=_re.IGNORECASE)
    text = _re.sub(r'(SL|TP)(\d)',           r'\1 \2', text, flags=_re.IGNORECASE)

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


def clean_number(val: float) -> str:
    return str(int(val)) if val == int(val) else str(val)


# ================== DEFAULT SL CALCULATOR ==================
PIP_VALUE_MAP = {
    "XAUUSD":  1.00,
    "XAGUSD":  0.05,
    "USDJPY":  0.0076,
    "GBPJPY":  0.0076,
    "EURJPY":  0.0076,
    "CHFJPY":  0.0076,
    "GBPUSD":  0.01,
    "EURUSD":  0.01,
    "AUDUSD":  0.01,
    "NZDUSD":  0.01,
    "USDCAD":  0.0076,
    "USDCHF":  0.0109,
    "BTCUSD":  0.01,
    "ETHUSD":  0.01,
    "USOUSD":  0.01,
    "NGUSD":   0.01,
    "DEFAULT": 0.01,
}

DEFAULT_SL_USD = 10.0

MIN_SL_DISTANCE = {
    "XAUUSD":  10.0,
    "XAGUSD":  0.50,
    "BTCUSD":  500.0,
    "ETHUSD":  20.0,
    "USDJPY":  0.50,
    "GBPJPY":  0.50,
    "EURJPY":  0.50,
    "EURUSD":  0.0010,
    "GBPUSD":  0.0010,
    "DEFAULT": 0.0010,
}


def calculate_default_sl(symbol: str, entry: float, direction: str) -> float:
    symbol_upper = (symbol or "DEFAULT").upper()
    pip_value    = PIP_VALUE_MAP.get(symbol_upper, PIP_VALUE_MAP["DEFAULT"])

    if "JPY" in symbol_upper:
        pip_size = 0.01
    elif "XAU" in symbol_upper or "GOLD" in symbol_upper:
        pip_size = 0.01
    elif "XAG" in symbol_upper or "SILVER" in symbol_upper:
        pip_size = 0.01
    elif "BTC" in symbol_upper or "ETH" in symbol_upper:
        pip_size = 1.0
    else:
        pip_size = 0.0001

    pips_needed = DEFAULT_SL_USD / pip_value
    sl_distance = round(pips_needed * pip_size, 5)
    min_dist    = MIN_SL_DISTANCE.get(symbol_upper, MIN_SL_DISTANCE["DEFAULT"])
    sl_distance = max(sl_distance, min_dist)

    if direction == "BUY":
        return round(entry - sl_distance, 3)
    else:
        return round(entry + sl_distance, 3)


# ================== PARSE SIGNAL ==================
def parse_signal(text: str) -> dict:
    text  = normalize_text(text)
    upper = text.upper()

    result = {
        "type":   None,
        "symbol": "XAUUSD",
        "entry":  None,
        "tp":     [],
        "sl":     None
    }

    # ── SYMBOL ───────────────────────────────────────────────────────
    symbol_map = [
        (["XAU", "GOLD"],            "XAUUSD"),
        (["EURUSD", "EUR/USD"],      "EURUSD"),
        (["GBPUSD", "GBP/USD"],      "GBPUSD"),
        (["USDJPY", "USD/JPY"],      "USDJPY"),
        (["CHFJPY", "CHF/JPY"],      "CHFJPY"),
        (["USDCHF", "USD/CHF"],      "USDCHF"),
        (["AUDUSD", "AUD/USD"],      "AUDUSD"),
        (["USDCAD", "USD/CAD"],      "USDCAD"),
        (["NZDUSD", "NZD/USD"],      "NZDUSD"),
        (["GBPJPY", "GBP/JPY"],      "GBPJPY"),
        (["EURJPY", "EUR/JPY"],      "EURJPY"),
        (["XAG", "SILVER"],          "XAGUSD"),
        (["BTC", "BITCOIN"],         "BTCUSD"),
        (["ETH", "ETHEREUM"],        "ETHUSD"),
        (["LTC", "LITECOIN"],        "LTCUSD"),
        (["XRP", "RIPPLE"],          "XRPUSD"),
        (["ADA", "CARDANO"],         "ADAUSD"),
        (["DOT", "POLKADOT"],        "DOTUSD"),
        (["SOL", "SOLANA"],          "SOLUSD"),
        (["DOGE", "DOGECOIN"],       "DOGEUSD"),
        (["AVAX", "AVALANCHE"],      "AVAXUSD"),
        (["MATIC", "POLYGON"],       "MATICUSD"),
        (["SHIB", "SHIBA"],          "SHIBUSD"),
        (["UNI", "UNISWAP"],         "UNIUSD"),
        (["LINK", "CHAINLINK"],      "LINKUSD"),
        (["LUNA", "TERRA"],          "LUNAUSD"),
        (["ALGO", "ALGORAND"],       "ALGOUSD"),
        (["ATOM", "COSMOS"],         "ATOMUSD"),
        (["USOUSD", "USOIL"],        "USOUSD"),
        (["COPPER"],                 "CATPGPY"),
        (["NGUSD", "NATGAS"],        "NGUSD"),
        (["NAS", "NASDAQ", "US100"], "NAS100"),
        (["SP500", "SPX"],           "SPX500"),
        (["DOW", "DJ30"],            "DJ30"),
    ]
    for keywords, sym in symbol_map:
        if any(k in upper for k in keywords):
            result["symbol"] = sym
            break

    # ── SYMBOL FALLBACK BY PRICE RANGE ───────────────────────────────
    if result["symbol"] == "XAUUSD":
        all_prices = re.findall(r'\b(\d{4,6}(?:\.\d+)?)\b', upper)
        if all_prices:
            max_price = max(float(p) for p in all_prices)
            if max_price > 50000:
                result["symbol"] = "BTCUSD"
            elif max_price > 5000:
                result["symbol"] = "ETHUSD"

    # ── TYPE ─────────────────────────────────────────────────────────
    if re.search(r'\bBUY\b', upper):
        result["type"] = "BUY"
    elif re.search(r'\bSELL\b', upper):
        result["type"] = "SELL"

    # ── ENTRY ────────────────────────────────────────────────────────
    entry_match = re.search(
        r'\b(BUY|SELL)\s*(?:NOW|LIMIT|ZONE|NEAR)?\s*[@:\-]?\s*'
        r'([\d]+(?:\.\d+)?)(?:\s*[-/]\s*([\d]+(?:\.\d+)?))?',
        upper
    )
    entry_keyword_match = re.search(
        r'ENTRY\s*(?:BUY|SELL)?\s*[:\-]{0,2}\s*'
        r'([\d]+(?:\.\d+)?)(?:\s*[-/]\s*([\d]+(?:\.\d+)?))?',
        upper
    )
    zone_match = re.search(
        r'ZONE\s*([\d]+(?:\.\d+)?)\s*[-]\s*([\d]+(?:\.\d+)?)', upper
    )
    at_match = re.search(r'@\s*([\d]+(?:\.\d+)?)', upper)

    if entry_match:
        v1 = entry_match.group(2)
        v2 = entry_match.group(3)
        result["entry"] = f"{v1}-{v2}" if v2 else v1
    elif entry_keyword_match:
        v1 = entry_keyword_match.group(1)
        v2 = entry_keyword_match.group(2)
        result["entry"] = f"{v1}-{v2}" if v2 else v1
    elif zone_match:
        v1, v2 = zone_match.group(1), zone_match.group(2)
        result["entry"] = f"{v1}-{v2}"
    elif at_match:
        result["entry"] = at_match.group(1)

    # ── TP ───────────────────────────────────────────────────────────
    def flat(matches):
        out = []
        for m in matches:
            val = (m[0] or m[1]) if isinstance(m, tuple) else m
            if val:
                out.append(val)
        return out

    tp_matches = re.findall(
        r'\bTP\s*\d{0,2}\s*[:\-\.\s_]\s*([\d]+(?:\.\d+)?)|\bTP\s*\d{0,2}\s+([\d]+(?:\.\d+)?)',
        upper
    )
    takeprofit_matches = re.findall(
        r'\bTAKEPROFIT\s*(?:[1-9]\d?)?\s*[:\-\.\s_]?\s*([\d]+(?:\.\d+)?)', upper
    )
    take_profit_matches = re.findall(
        r'\bTAKE\s*PROFIT\s*(?:[1-9]\d?)?\s*[:\-\.\s_]?\s*([\d]+(?:\.\d+)?)', upper
    )
    target_matches = re.findall(
        r'\bTARGET\s*(?:[1-9]\d?)?\s*[:\-\.\s_]+\s*([\d]{3,}(?:\.\d+)?)', upper
    )
    tp1_matches = re.findall(
        r'\bTP[1-9]\s*[:\-\.]?\s*([\d]+(?:\.\d+)?)', upper
    )

    all_tp = (flat(tp_matches) or flat(tp1_matches) or
              takeprofit_matches or take_profit_matches or target_matches)

    # Filter out wrong TP values — keep only within 20% of entry
    if result["entry"]:
        try:
            entry_f = float(result["entry"])
            all_tp  = [t for t in all_tp if entry_f > 0 and abs(float(t) - entry_f) / entry_f < 0.20]
        except Exception:
            pass

    result["tp"] = [float(tp) for tp in all_tp]

    # ── SL ───────────────────────────────────────────────────────────
    # Allow text between SL and number e.g. "SL: Solid break 4714"
    sl_match = re.search(
        r'\b(?:SL|STOPLOSS|STOP\s*LOSS)\b[^0-9]{0,40}?([\d]+(?:\.\d+)?)',
        upper
    )
    if sl_match:
        result["sl"] = float(sl_match.group(1))

    return result


# ================== FORMAT SIGNAL ==================
def format_signal(data: dict, source: str = None) -> str:
    symbol    = (data.get("symbol") or "UNKNOWN").upper()
    direction = (data.get("type")   or "").upper()
    entry     = data.get("entry")
    sl        = data.get("sl")
    tp_list   = data.get("tp") or []

    # Auto-fill missing SL
    if not sl and entry:
        try:
            sl = calculate_default_sl(symbol, float(entry), direction)
        except Exception:
            sl = None

    first_tp = clean_number(tp_list[0]) if tp_list else "N/A"
    sl_str   = clean_number(sl) if sl else "N/A"

    lines = [f"{direction} {symbol} {entry or 'N/A'}"]
    lines.append(f"TP {first_tp}")
    lines.append(f"SL {sl_str}")
    if source:
        lines.append(f"Source: {source}")

    return "\n".join(lines)


# ================== VALIDATION ==================
def is_valid_signal(data: dict) -> bool:
    return bool(data["type"] and data["entry"] and data["tp"])