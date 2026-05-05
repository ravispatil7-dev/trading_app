import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# ===== GLOBAL =====
SYMBOL = "XAUUSD"
current_trade = None
trade_history = []
balance = 0

timeframes = {
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4
}

# ===== CONNECT =====
def connect():
    if not mt5.initialize():
        return False
    return True

# ===== RSI =====
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]

# ===== ATR =====
def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    return atr.iloc[-1]

# ===== TREND =====
def calculate_trend(df):
    ema50 = df['close'].ewm(span=50).mean().iloc[-1]
    ema200 = df['close'].ewm(span=200).mean().iloc[-1]
    return "UP" if ema50 > ema200 else "DOWN"

# ===== MULTI TF =====
def get_multi_tf_data():
    if not connect():
        return {"error": "MT5 not connected"}

    result = {}

    for name, tf in timeframes.items():
        rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, 200)

        if rates is None:
            continue

        df = pd.DataFrame(rates)

        result[name] = {
            "rsi": round(calculate_rsi(df), 2),
            "atr": round(calculate_atr(df), 2),
            "trend": calculate_trend(df)
        }

    return result

# ===== AUTO CLOSE =====
def check_trade_close(price):
    global current_trade, trade_history, balance

    if not current_trade:
        return

    sl = current_trade["sl"]
    tp = current_trade["tp"]
    signal = current_trade["signal"]

    close = False

    if signal == "BUY" and (price <= sl or price >= tp):
        close = True
    elif signal == "SELL" and (price >= sl or price <= tp):
        close = True

    if close:
        profit = (price - current_trade["entry"]) if signal == "BUY" else (current_trade["entry"] - price)

        current_trade["exit"] = round(price, 2)
        current_trade["profit"] = round(profit, 2)
        current_trade["status"] = "CLOSED"

        balance += profit
        trade_history.append(current_trade.copy())

        current_trade = None

# ===== MAIN SIGNAL =====
def get_signal():
    global current_trade

    data = get_multi_tf_data()
    if "error" in data:
        return data

    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.bid if tick else 0

    # ===== AUTO CLOSE =====
    check_trade_close(price)

    # ===== TRAILING SL =====
    if current_trade:
        if current_trade["signal"] == "BUY":
            if price - current_trade["entry"] > 2:
                current_trade["sl"] = max(current_trade["sl"], round(price - 1, 2))

        elif current_trade["signal"] == "SELL":
            if current_trade["entry"] - price > 2:
                current_trade["sl"] = min(current_trade["sl"], round(price + 1, 2))

        return {
            "status": "IN_TRADE",
            "price": round(price, 2),
            "sentiment": "RUNNING",
            "trade": current_trade,
            "timeframes": data
        }

    # ===== SIGNAL LOGIC =====
    confirmations = []

    for tf in data:
        rsi = data[tf]["rsi"]
        trend = data[tf]["trend"]

        if rsi > 55 and trend == "UP":
            confirmations.append("BUY")
        elif rsi < 45 and trend == "DOWN":
            confirmations.append("SELL")

    bullish = confirmations.count("BUY")
    bearish = confirmations.count("SELL")

    if bullish >= 2:
        signal = "BUY"
        sentiment = "STRONG BUY"
    elif bearish >= 2:
        signal = "SELL"
        sentiment = "STRONG SELL"
    else:
        return {
            "status": "WAIT",
            "price": round(price, 2),
            "sentiment": "NEUTRAL",
            "timeframes": data
        }

    # ===== ENTRY / SL / TP =====
    atr = data["M15"]["atr"]

    if signal == "BUY":
        entry = price
        sl = entry - (atr * 1.5)
        tp = entry + (atr * 3)
    else:
        entry = price
        sl = entry + (atr * 1.5)
        tp = entry - (atr * 3)

    current_trade = {
        "signal": signal,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "time": str(datetime.now()),
        "status": "OPEN"
    }

    return {
        "status": "NEW_SIGNAL",
        "price": round(price, 2),
        "sentiment": sentiment,
        "trade": current_trade,
        "timeframes": data
    }

# ===== MANUAL CLOSE =====
def manual_close_trade(price):
    global current_trade
    if not current_trade:
        return None

    check_trade_close(price)
    return current_trade

# ===== HISTORY =====
def get_trade_history():
    return trade_history