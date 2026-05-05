import MetaTrader5 as mt5
import pandas as pd
import requests
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
    return (100 - (100 / (1 + rs))).iloc[-1]

# ===== ATR =====
def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

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
    return "WEAK"

# ===== BREAKOUT =====
def breakout_signal(price, support, resistance):
    if price > resistance:
        return "BREAKOUT_BUY"
    elif price < support:
        return "BREAKOUT_SELL"
    return None

# ===== ORDER BLOCK =====
def detect_order_block(df):
    for i in range(len(df)-5, len(df)-1):
        c = df.iloc[i]
        n = df.iloc[i+1]

        if c['close'] < c['open'] and n['close'] > n['open']:
            return {"type": "BULLISH_OB", "low": c['low'], "high": c['high']}

        if c['close'] > c['open'] and n['close'] < n['open']:
            return {"type": "BEARISH_OB", "low": c['low'], "high": c['high']}

    return None

# ===== LIQUIDITY SWEEP =====
def detect_liquidity_sweep(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last['high'] > prev['high'] and last['close'] < prev['high']:
        return "SWEEP_HIGH"

    if last['low'] < prev['low'] and last['close'] > prev['low']:
        return "SWEEP_LOW"

    return None

# ===== NEWS FILTER =====
def is_news_time():
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        data = requests.get(url, timeout=5).json()
        now = datetime.utcnow()

        for event in data:
            if event.get('impact') == "High":
                event_time = datetime.strptime(event['date'], "%Y-%m-%d %H:%M:%S")
                if abs((event_time - now).total_seconds()) < 1800:
                    return True
    except:
        return False

    return False

# ===== MARKET SENTIMENT =====
def calculate_market_sentiment(data, price):
    score = 0

    for tf in data:
        d = data[tf]

        if d["trend"] == "UP":
            score += 1
        else:
            score -= 1

        if d["rsi"] > 60:
            score += 1
        elif d["rsi"] < 40:
            score -= 1

        mid = (d["support"] + d["resistance"]) / 2

        if price > mid:
            score += 1
        else:
            score -= 1

        if d["liquidity"] == "SWEEP_LOW":
            score += 1
        elif d["liquidity"] == "SWEEP_HIGH":
            score -= 1

    if score >= 6:
        return "STRONG BUY"
    elif score >= 3:
        return "BUY"
    elif score <= -6:
        return "STRONG SELL"
    elif score <= -3:
        return "SELL"
    return "NEUTRAL"

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
            "candle": candle_strength(df),
            "order_block": detect_order_block(df),
            "liquidity": detect_liquidity_sweep(df)
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

    # NEWS FILTER
    if is_news_time():
        return {"status": "WAIT", "sentiment": "NEWS TIME"}

    data = get_multi_tf_data()
    if "error" in data:
        return data

    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.bid if tick else 0

    sentiment = calculate_market_sentiment(data, price)

    # AUTO CLOSE
    check_trade_close(price)

    # TRADE RUNNING
    if current_trade:
        if current_trade["signal"] == "BUY" and price - current_trade["entry"] > 2:
            current_trade["sl"] = max(current_trade["sl"], round(price - 1, 2))

        elif current_trade["signal"] == "SELL" and current_trade["entry"] - price > 2:
            current_trade["sl"] = min(current_trade["sl"], round(price + 1, 2))

        return {
            "status": "IN_TRADE",
            "price": round(price, 2),
            "sentiment": sentiment,
            "trade": current_trade
        }

    # SIGNAL LOGIC
    confirmations = []

    for tf in data:
        d = data[tf]
        breakout = breakout_signal(price, d["support"], d["resistance"])

        if (
            d["rsi"] > 55 and
            d["trend"] == "UP" and
            d["candle"] == "STRONG" and
            breakout == "BREAKOUT_BUY" and
            d["liquidity"] != "SWEEP_HIGH" and
            d["order_block"] and d["order_block"]["type"] == "BULLISH_OB"
        ):
            confirmations.append("BUY")

        elif (
            d["rsi"] < 45 and
            d["trend"] == "DOWN" and
            d["candle"] == "STRONG" and
            breakout == "BREAKOUT_SELL" and
            d["liquidity"] != "SWEEP_LOW" and
            d["order_block"] and d["order_block"]["type"] == "BEARISH_OB"
        ):
            confirmations.append("SELL")

    bullish = confirmations.count("BUY")
    bearish = confirmations.count("SELL")
    htf_trend = data["H4"]["trend"]

    if bullish >= 2 and htf_trend == "UP":
        signal = "BUY"
    elif bearish >= 2 and htf_trend == "DOWN":
        signal = "SELL"
    else:
        return {
            "status": "WAIT",
            "price": round(price, 2),
            "sentiment": sentiment
        }

    # SL / TP
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
        "trade": current_trade
    }

# ===== MANUAL CLOSE =====
def manual_close_trade(price):
    global current_trade

    if not current_trade:
        return None

    profit = (price - current_trade["entry"]) if current_trade["signal"] == "BUY" else (current_trade["entry"] - price)

    current_trade["exit"] = round(price, 2)
    current_trade["profit"] = round(profit, 2)
    current_trade["status"] = "CLOSED"

    trade_history.append(current_trade.copy())
    current_trade = None

    return {"status": "MANUAL_CLOSED"}

# ===== HISTORY =====
def get_trade_history():
    return trade_history