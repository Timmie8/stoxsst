import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# -------------------------------------------------------------
# GEFIXTE DATA-FETCH FUNCTIES (Geen UnserializableReturnValueError)
# -------------------------------------------------------------

@st.cache_data(ttl=600)
def fetch_stock_data(symbol):
    """Slaat ALLEEN serialiseerbare data op (DataFrame + dict van info)"""
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y", timeout=10)
        
        # Haal alleen nodige info velden op in een simpele dict
        info_data = {}
        try:
            info_data['shortPercentOfFloat'] = stock.info.get('shortPercentOfFloat', None)
        except Exception:
            info_data['shortPercentOfFloat'] = None
            
        return df, info_data
    except Exception:
        return None, {}

def get_put_call_ratio(symbol):
    """Haalt Put/Call ratio direct op zonder caching van complexe Ticker objecten"""
    try:
        stock = yf.Ticker(symbol)
        options = stock.options
        if not options:
            return None
        opt = stock.option_chain(options[0])
        total_calls = opt.calls['volume'].sum()
        total_puts = opt.puts['volume'].sum()
        if total_calls > 0:
            return total_puts / total_calls
    except Exception:
        pass
    return None

def analyze_ticker(symbol):
    df, info = fetch_stock_data(symbol)
    if df is None or df.empty or len(df) < 50:
        return None

    # Indicatoren berekenen
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['RSI'] = calculate_rsi(df['Close'], 14)

    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    close_price = latest['Close']
    price_change = close_price - prev['Close']
    pct_change = (price_change / prev['Close']) * 100

    # Support & Resistance Berekening (Laatste 60 handelsdagen)
    recent_df = df.tail(60)
    support_level = recent_df['Low'].min()
    resistance_level = recent_df['High'].max()
    
    support_pct = ((support_level - close_price) / close_price) * 100
    resistance_pct = ((resistance_level - close_price) / close_price) * 100

    # Short Float & Put/Call Ratio ophalen
    short_float = info.get('shortPercentOfFloat', None)
    pcr = get_put_call_ratio(symbol)

    # 1. Korte Termijn Score (1-5)
    st_points = 0
    if close_price > latest['SMA_5']: st_points += 1.25
    if latest['SMA_5'] > prev['SMA_5']: st_points += 1.25
    if 45 <= latest['RSI'] <= 70: st_points += 1.25
    elif latest['RSI'] > 70: st_points += 0.5
    if latest['MACD'] > latest['MACD_Signal']: st_points += 1.25
    st_stars = min(max(int(round(st_points)), 0), 5)

    # 2. Middellange Termijn Score (1-5)
    mt_points = 0
    if close_price > latest['SMA_20']: mt_points += 1.25
    if close_price > latest['SMA_50']: mt_points += 1.25
    if latest['SMA_20'] > latest['SMA_50']: mt_points += 1.25
    if latest['MACD'] > 0: mt_points += 1.25
    mt_stars = min(max(int(round(mt_points)), 0), 5)

    # 3. Richting Pijl
    if price_change > 0:
        arrow = "⬆️ UP"
    elif price_change < 0:
        arrow = "⬇️ DOWN"
    else:
        arrow = "➡️ NEUTRAL"

    return {
        "symbol": symbol,
        "close": close_price,
        "change": price_change,
        "pct_change": pct_change,
        "arrow": arrow,
        "st_stars": st_stars,
        "mt_stars": mt_stars,
        "rsi": latest['RSI'],
        "pcr": pcr,
        "short_float": short_float,
        "support": support_level,
        "support_pct": support_pct,
        "resistance": resistance_level,
        "resistance_pct": resistance_pct
    }
