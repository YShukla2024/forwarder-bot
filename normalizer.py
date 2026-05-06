import re

# ================== NORMALIZE ==================
def normalize_text(text: str) -> str:
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
# Approximate USD pip value per 0.01 lot for each symbol
PIP_VALUE_MAP = {
    "XAUUSD":  0.10,   # Gold:    1 pip = $0.10 per 0.01 lot
    "XAGUSD":  0.05,   # Silver
    "USDJPY":  0.0076, # JPY pairs
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

DEFAULT_SL_USD = 10.0  # Risk $10 by default


def calculate_default_sl(symbol: str, entry: float, direction: str) -> float:
    """
    Calculate a default Stop Loss price that risks ~$10
    for a 0.01 lot trade based on symbol pip value.
    """
    symbol_upper = (symbol or "DEFAULT").upper()
    pip_value = PIP_VALUE_MAP.get(symbol_upper, PIP_VALUE_MAP["DEFAULT"])

    # Pip size differs by instrument
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
    sl_distance  = round(pips_needed * pip_size, 5)

    if direction == "BUY":
        return round(entry - sl_distance, 3)
    else:
        return round(entry + sl_distance, 3)


# ================== PARSE SIGNAL ==================
def parse_signal(text: str) -> dict:
    text = normalize_text(text)
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
        (["XAU", "GOLD"],              "XAUUSD"),
        (["EURUSD"],                   "EURUSD"),
        (["GBPUSD"],                   "GBPUSD"),
        (["USDJPY", "JPPY"],           "USDJPY"),
        (["CHFJPY"],                   "CHFJPY"),
        (["USDCHF"],                   "USDCHF"),
        (["AUDUSD"],                   "AUDUSD"),
        (["USDCAD"],                   "USDCAD"),
        (["NZDUSD"],                   "NZDUSD"),
        (["GBPJPY"],                   "GBPJPY"),
        (["EURJPY"],                   "EURJPY"),
        (["XAG", "SILVER"],            "XAGUSD"),
        (["BTC", "BITCOIN"],           "BTCUSD"),
        (["ETH", "ETHEREUM"],          "ETHUSD"),
        (["LTC", "LITECOIN"],          "LTCUSD"),
        (["XRP", "RIPPLE"],            "XRPUSD"),
        (["ADA", "CARDANO"],           "ADAUSD"),
        (["DOT", "POLKADOT"],          "DOTUSD"),
        (["SOL", "SOLANA"],            "SOLUSD"),
        (["DOGE", "DOGECOIN"],         "DOGEUSD"),
        (["AVAX", "AVALANCHE"],        "AVAXUSD"),
        (["MATIC", "POLYGON"],         "MATICUSD"),
        (["SHIB", "SHIBA INU"],        "SHIBUSD"),
        (["UNI", "UNISWAP"],           "UNIUSD"),
        (["LINK", "CHAINLINK"],        "LINKUSD"),
        (["LUNA", "TERRA"],            "LUNAUSD"),
        (["ALGO", "ALGORAND"],         "ALGOUSD"),
        (["ATOM", "COSMOS"],           "ATOMUSD"),
        (["USOUSD", "USOIL"],          "USOUSD"),
        (["COPPER"],                   "CATPGPY"),
        (["NGUSD", "NATGAS"],          "NGUSD"),
        (["NAS", "NASDAQ", "US100"],   "NAS100"),
        (["SP500", "SPX"],             "SPX500"),
        (["DOW", "DJ30"],              "DJ30"),
    ]
    for keywords, sym in symbol_map:
        if any(k in upper for k in keywords):
            result["symbol"] = sym
            break

    # ── TYPE ─────────────────────────────────────────────────────────
    if re.search(r'\bBUY\b', upper):
        result["type"] = "BUY"
    elif re.search(r'\bSELL\b', upper):
        result["type"] = "SELL"

    # ── ENTRY ────────────────────────────────────────────────────────
    entry_match = re.search(
        r'\b(BUY|SELL)\s*(?:NOW|LIMIT|ZONE|NEAR)?\s*[:\-]?\s*'
        r'([\d]{2,}(?:\.\d+)?)(?:\s*[-/]\s*([\d]{2,}(?:\.\d+)?))?',
        upper
    )
    entry_keyword_match = re.search(
        r'ENTRY\s*(?:BUY|SELL)?\s*[:\-]?\s*'
        r'([\d]{2,}(?:\.\d+)?)(?:\s*[-/]\s*([\d]{2,}(?:\.\d+)?))?',
        upper
    )
    zone_match = re.search(
        r'(?:ZONE)\s*([\d]{2,}(?:\.\d+)?)\s*[-–]\s*([\d]{2,}(?:\.\d+)?)',
        upper
    )
    at_match = re.search(r'@\s*([\d]{2,}(?:\.\d+)?)', upper)

    if entry_match:
        v1 = float(entry_match.group(2))
        v2 = entry_match.group(3)
        result["entry"] = str(round((v1 + float(v2)) / 2)) if v2 else entry_match.group(2)
    elif entry_keyword_match:
        v1 = float(entry_keyword_match.group(1))
        v2 = entry_keyword_match.group(2)
        result["entry"] = str(round((v1 + float(v2)) / 2)) if v2 else entry_keyword_match.group(1)
    elif zone_match:
        v1, v2 = float(zone_match.group(1)), float(zone_match.group(2))
        result["entry"] = str(round((v1 + v2) / 2))
    elif at_match:
        result["entry"] = at_match.group(1)

    # ── TP ───────────────────────────────────────────────────────────
    tp_matches = re.findall(
        r'\bTP\s*\d*\s*[:\-\.\s_]?\s*([\d]{2,}(?:\.\d+)?)', upper
    )
    takeprofit_matches = re.findall(
        r'\bTAKEPROFIT\s*\d*\s*[:\-\.\s_]?\s*([\d]{2,}(?:\.\d+)?)', upper
    )
    take_profit_matches = re.findall(
        r'\bTAKE\s*PROFIT\s*\d*\s*[:\-\.\s_]?\s*([\d]{2,}(?:\.\d+)?)', upper
    )
    target_matches = re.findall(
        r'\bTARGET\s*\d*\s*[:\-\.\s_]?\s*([\d]{2,}(?:\.\d+)?)', upper
    )

    all_tp = tp_matches or takeprofit_matches or take_profit_matches or target_matches
    result["tp"] = [float(tp) for tp in all_tp]

    # ── SL ───────────────────────────────────────────────────────────
    sl_match = re.search(
        r'\b(?:SL|STOPLOSS|STOP\s*LOSS)\s*[:\-\.\s_]?\s*([\d]{2,}(?:\.\d+)?)',
        upper
    )
    if sl_match:
        result["sl"] = float(sl_match.group(1))

    return result


# ================== FORMAT SIGNAL ==================
def format_signal(data: dict, source: str = None) -> str:
    """
    Simple signal formatter — original company format.
    Auto-fills missing SL with ~$10 default risk.
    Output: TYPE SYMBOL ENTRY\nTP FIRST_TP\nSL VALUE\nSource: name
    """
    symbol    = (data.get("symbol") or "UNKNOWN").upper()
    direction = (data.get("type")   or "").upper()
    entry     = data.get("entry")
    sl        = data.get("sl")
    tp_list   = data.get("tp") or []

    # ── Auto-fill missing SL ──────────────────────────────────────────
    if not sl and entry:
        try:
            sl = calculate_default_sl(symbol, float(entry), direction)
        except Exception:
            sl = None

    # ── First TP only ─────────────────────────────────────────────────
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
    """Signal is valid if it has type, entry, and at least one TP."""
    return bool(data["type"] and data["entry"] and data["tp"])