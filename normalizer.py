import re

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

def parse_signal(text: str) -> dict:
    text = normalize_text(text)
    upper = text.upper()

    result = {
        "type": None,
        "symbol": "XAUUSD",
        "entry": None,
        "tp": [],
        "sl": None
    }

    # ================== SYMBOL ==================
    if "XAU" in upper or "GOLD" in upper:
        result["symbol"] = "XAUUSD"
    elif "EURUSD" in upper:
        result["symbol"] = "EURUSD"
    elif "GBPUSD" in upper:
        result["symbol"] = "GBPUSD"
    elif "USDJPY" in upper:
        result["symbol"] = "USDJPY"
    elif "CHFJPY" in upper:
        result["symbol"] = "CHFJPY"
    elif "JPPY" in upper:
        result["symbol"] = "USDJPY"
    elif "USDCHF" in upper:
        result["symbol"] = "USDCHF"
    elif "AUDUSD" in upper:
        result["symbol"] = "AUDUSD"
    elif "USDCAD" in upper:
        result["symbol"] = "USDCAD"
    elif "NZDUSD" in upper:
        result["symbol"] = "NZDUSD"
    elif "XAG" in upper or "SILVER" in upper:
        result["symbol"] = "XAGUSD"
    elif "BTC" in upper or "BITCOIN" in upper:
        result["symbol"] = "BTCUSD"
    elif "ETH" in upper or "ETHEREUM" in upper:
        result["symbol"] = "ETHUSD"
    elif "LTC" in upper or "LITECOIN" in upper:
        result["symbol"] = "LTCUSD"
    elif "XRP" in upper or "RIPPLE" in upper:
        result["symbol"] = "XRPUSD"
    elif "ADA" in upper or "CARDANO" in upper:
        result["symbol"] = "ADAUSD"
    elif "DOT" in upper or "POLKADOT" in upper:
        result["symbol"] = "DOTUSD"
    elif "SOL" in upper or "SOLANA" in upper:
        result["symbol"] = "SOLUSD"
    elif "DOGE" in upper or "DOGECOIN" in upper:
        result["symbol"] = "DOGEUSD"
    elif "AVAX" in upper or "AVALANCHE" in upper:
        result["symbol"] = "AVAXUSD"
    elif "MATIC" in upper or "POLYGON" in upper:
        result["symbol"] = "MATICUSD"
    elif "SHIB" in upper or "SHIBA INU" in upper:
        result["symbol"] = "SHIBUSD"
    elif "UNI" in upper or "UNISWAP" in upper:
        result["symbol"] = "UNIUSD"
    elif "LINK" in upper or "CHAINLINK" in upper:
        result["symbol"] = "LINKUSD"
    elif "LUNA" in upper or "TERRA" in upper:
        result["symbol"] = "LUNAUSD"
    elif "ALGO" in upper or "ALGORAND" in upper:
        result["symbol"] = "ALGOUSD"
    elif "ATOM" in upper or "COSMOS" in upper:
        result["symbol"] = "ATOMUSD"
    elif "USOUSD" in upper or "USOIL" in upper:
        result["symbol"] = "USOUSD"
    elif "COPPER" in upper:
        result["symbol"] = "CATPGPY"
    elif "NGUSD" in upper or "NATGAS" in upper:
        result["symbol"] = "NGUSD"

    # ================== TYPE ==================
    if re.search(r'\bBUY\b', upper):
        result["type"] = "BUY"
    elif re.search(r'\bSELL\b', upper):
        result["type"] = "SELL"

    # ================== ENTRY ==================
    entry_match = re.search(
        r'\b(BUY|SELL)\s*(?:NOW|LIMIT|ZONE)?\s*'
        r'([\d]{4,}(?:\.\d+)?)(?:\s*[-/]\s*([\d]{4,}(?:\.\d+)?))?',
        upper
    )
    zone_match = re.search(
        r'(?:ZONE|ENTRY)\s*([\d]{4,}(?:\.\d+)?)\s*[-–]\s*([\d]{4,}(?:\.\d+)?)',
        upper
    )

    if entry_match:
        result["entry"] = entry_match.group(2)
    elif zone_match:
        result["entry"] = zone_match.group(1)

    if not result["entry"]:
        at_match = re.search(r'@\s*([\d]{4,}(?:\.\d+)?)', upper)
        if at_match:
            result["entry"] = at_match.group(1)

    # ================== TP ==================
    # ✅ separator optional — handles TP14686 (after superscript normalize)
    # ✅ _ added — handles SL_ 4708
    tp_matches = re.findall(
        r'\bTP\s*\d*\s*[:\-\.\s_]?\s*([\d]{4,}(?:\.\d+)?)',
        upper
    )
    takeprofit_matches = re.findall(
        r'\bTAKEPROFIT\s*\d*\s*[:\-\.\s_]?\s*([\d]{4,}(?:\.\d+)?)',
        upper
    )
    take_profit_matches = re.findall(
        r'\bTAKE\s*PROFIT\s*\d*\s*[:\-\.\s_]?\s*([\d]{4,}(?:\.\d+)?)',
        upper
    )

    all_tp = tp_matches or takeprofit_matches or take_profit_matches
    result["tp"] = [float(tp) for tp in all_tp]

    # ================== SL ==================
    # ✅ _ added — handles SL_ 4708
    # ✅ separator optional — handles SL4708
    sl_match = re.search(
        r'\b(?:SL|STOPLOSS|STOP\s*LOSS)\s*[:\-\.\s_]?\s*([\d]{4,}(?:\.\d+)?)',
        upper
    )
    if sl_match:
        result["sl"] = float(sl_match.group(1))

    return result

def format_signal(data: dict) -> str:
    lines = []
    lines.append(f"{data['type']} {data['symbol']} {data['entry'] or 'N/A'}")
    if data["tp"]:
        lines.append(f"TP {clean_number(data['tp'][0])}")
    if data["sl"]:
        lines.append(f"SL {clean_number(data['sl'])}")
    return "\n".join(lines)

def is_valid_signal(data: dict) -> bool:
    return bool(data["type"] and data["entry"] and data["tp"] and data["sl"])