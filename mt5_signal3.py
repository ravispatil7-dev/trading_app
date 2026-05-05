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

# ===== SUPPORT / RESISTANCE =====
def calculate_support_resistance(df, window=20):
    support = df['low'].rolling(window).min().iloc[-1]
    resistance = df['high'].rolling(window).max().iloc[-1]
    return support, resistance

# ===== CANDLE STRENGTH =====
def candle_strength(df):
    last = df.iloc[-1]
    body = abs(last['close'] - last['open'])
    range_ = last['high'] - last['low']

    if range_ == 0:
        return "WEAK"

    strength = body / range_

    if strength > 0.6:
        return "STRONG"
    elif strength > 0.4:
        return "MEDIUM"
    else:
        return "WEAK"

# ===== BREAKOUT =====
def breakout_signal(price, support, resistance):
    if price > resistance:
        return "BREAKOUT_BUY"
    elif price < support:
        return "BREAKOUT_SELL"
    return None

# ===== MULTI TF DATA =====
def get_multi_tf_data():
    if not connect():
        return {"error": "MT5 not connected"}

    result = {}

    for name, tf in timeframes.items():
        rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, 200)
        if rates is None:
            continue

        df = pd.DataFrame(rates)

        support, resistance = calculate_support_resistance(df)

        result[name] = {
            "rsi": round(calculate_rsi(df), 2),
            "atr": round(calculate_atr(df), 2),
            "trend": calculate_trend(df),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "candle": candle_strength(df)
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
        support = data[tf]["support"]
        resistance = data[tf]["resistance"]
        candle = data[tf]["candle"]

        breakout = breakout_signal(price, support, resistance)

        if (
            rsi > 55 and
            trend == "UP" and
            candle == "STRONG" and
            breakout == "BREAKOUT_BUY"
        ):
            confirmations.append("BUY")

        elif (
            rsi < 45 and
            trend == "DOWN" and
            candle == "STRONG" and
            breakout == "BREAKOUT_SELL"
        ):
            confirmations.append("SELL")

    bullish = confirmations.count("BUY")
    bearish = confirmations.count("SELL")

    # ===== HIGHER TF FILTER =====
    htf_trend = data["H4"]["trend"]

    if bullish >= 2 and htf_trend == "UP":
        signal = "BUY"
        sentiment = "STRONG BUY"
    elif bearish >= 2 and htf_trend == "DOWN":
        signal = "SELL"
        sentiment = "STRONG SELL"
    else:
        return {
            "status": "WAIT",
            "price": round(price, 2),
            "sentiment": "FILTERED",
            "timeframes": data
        }

    # ===== SMART SL/TP =====
    if signal == "BUY":
        sl = min([data[tf]["support"] for tf in data])
        tp = price + (price - sl) * 2
    else:
        sl = max([data[tf]["resistance"] for tf in data])
        tp = price - (sl - price) * 2

    current_trade = {
        "signal": signal,
        "entry": round(price, 2),
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