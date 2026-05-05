import MetaTrader5 as mt5
import pandas as pd

SYMBOL = "XAUUSD"

timeframes = {
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1
}

def connect():
    if not mt5.initialize():
        return False
    return True

# RSI Calculation
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]

# ATR Calculation
def calculate_atr(df, period=14):
    df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
    atr = df['tr'].rolling(period).mean()
    return atr.iloc[-1]

def get_multi_tf_data():
    if not connect():
        return {"error": "MT5 not connected"}

    result = {}

    for name, tf in timeframes.items():
        rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, 100)

        if rates is None:
            continue

        df = pd.DataFrame(rates)

        rsi = calculate_rsi(df)
        atr = calculate_atr(df)

        result[name] = {
            "rsi": round(rsi, 2),
            "atr": round(atr, 2)
        }

    return result

def get_signal():
    data = get_multi_tf_data()

    if "error" in data:
        return data

    # Simple sentiment logic
    bullish = sum(1 for tf in data if data[tf]["rsi"] > 50)
    bearish = sum(1 for tf in data if data[tf]["rsi"] < 50)

    sentiment = "BULLISH" if bullish > bearish else "BEARISH"

    price = mt5.symbol_info_tick(SYMBOL).bid

    return {
        "price": round(price, 2),
        "sentiment": sentiment,
        "timeframes": data
    }