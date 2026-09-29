import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Stoxline Rating Calculator", layout="centered")

st.title("📈 Stoxline AI Rating Calculator")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=600)
def fetch_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y", timeout=10)
        return df
    except Exception:
        return None

ticker_input = st.text_input("Voer ticker in (bijv. AMBA, NVDA, ASML.AS):", "AMBA")

if st.button("Bereken Rating") or ticker_input:
    symbol = ticker_input.strip().upper()
    
    with st.spinner(f"Data ophalen voor {symbol}..."):
        df = fetch_data(symbol)

    if df is None or df.empty or len(df) < 50:
        st.error(f"Koorne/data kon niet worden opgehaald voor {symbol}. Yahoo Finance reageert niet of de ticker bestaat niet.")
    else:
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

        # Short-Term Score
        st_points = 0
        if close_price > latest['SMA_5']: st_points += 1.25
        if latest['SMA_5'] > prev['SMA_5']: st_points += 1.25
        if 45 <= latest['RSI'] <= 70: st_points += 1.25
        elif latest['RSI'] > 70: st_points += 0.5
        if latest['MACD'] > latest['MACD_Signal']: st_points += 1.25
        st_stars = min(max(int(round(st_points)), 0), 5)

        # Mid-Term Score
        mt_points = 0
        if close_price > latest['SMA_20']: mt_points += 1.25
        if close_price > latest['SMA_50']: mt_points += 1.25
        if latest['SMA_20'] > latest['SMA_50']: mt_points += 1.25
        if latest['MACD'] > 0: mt_points += 1.25
        mt_stars = min(max(int(round(mt_points)), 0), 5)

        arrow = "⬆️" if price_change > 0 else ("⬇️" if price_change < 0 else "➡️")

        # Resultaten tonen
        st.subheader(f"Analyse voor {symbol}")
        col1, col2 = st.columns(2)
        col1.metric("Koers", f"${close_price:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        col2.write(f"**Richting:** {arrow}")

        st.markdown("---")
        st.write(f"**Short-Term Rating:** {'★' * st_stars}{'☆' * (5 - st_stars)} ({st_stars}/5)")
        st.write(f"**Mid-Term Rating:** {'★' * mt_stars}{'☆' * (5 - mt_stars)} ({mt_stars}/5)")
