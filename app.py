import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Pagina configuratie
st.set_page_config(page_title="Stoxline Multi-Stock Scanner", layout="wide")

st.title("📈 Stoxline AI Rating Scanner")
st.caption("Voer meerdere tickers in gescheiden door een komma (bijv: AMBA, NVDA, TSLA, ASML.AS)")

def calculate_rsi(series, period=14):
    """Bereken RSI (14)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_star_html(rating):
    """Genereert HTML voor gekleurde sterren op basis van de score:
       5 & 4: Groen (#28a745)
       3 & 2: Blauw (#007bff)
       1 & 0: Rood (#dc3545)
    """
    if rating in [4, 5]:
        color = "#28a745"  # Groen
    elif rating in [2, 3]:
        color = "#007bff"  # Blauw
    else:
        color = "#dc3545"  # Rood

    filled_stars = "★" * rating
    empty_stars = "☆" * (5 - rating)
    
    return f'<span style="color: {color}; font-weight: bold;">{filled_stars}{empty_stars} ({rating}/5)</span>'

def get_rsi_html(rsi):
    """Genereert HTML voor RSI met specifieke kleuring:
       > 55: Groen
       < 45: Rood
       Tussen 45 en 55: Grijs
    """
    if rsi > 55:
        color = "#28a745"  # Groen
    elif rsi < 45:
        color = "#dc3545"  # Rood
    else:
        color = "#6c757d"  # Grijs

    return f'<span style="color: {color}; font-weight: bold;">{rsi:.1f}</span>'

@st.cache_data(ttl=600)
def fetch_stock_data(symbol):
    """Haalt data op via yfinance met een timeout om vastlopen te voorkomen"""
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y", timeout=10)
        return df
    except Exception:
        return None

def analyze_ticker(symbol):
    df = fetch_stock_data(symbol)
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
        arrow = "➡️️ NEUTRAL"

    return {
        "symbol": symbol,
        "close": close_price,
        "change": price_change,
        "pct_change": pct_change,
        "arrow": arrow,
        "st_stars": st_stars,
        "mt_stars": mt_stars,
        "rsi": latest['RSI']
    }

# --- GEBRUIKERSINVOER ---
input_tickers = st.text_input("Voer ticker(s) in:", "AMBA, NVDA, TSLA, ASML.AS")

if st.button("🔍 Scan Aandelen") or input_tickers:
    tickers_list = [t.strip().upper() for t in input_tickers.split(",") if t.strip()]

    if not tickers_list:
        st.warning("Voer minimaal één geldige ticker in.")
    else:
        results = []
        with st.spinner("Aandelen analyseren..."):
            for symbol in tickers_list:
                res = analyze_ticker(symbol)
                if res:
                    results.append(res)
                else:
                    st.error(f"❌ Geen data gevonden voor **{symbol}**")

        if results:
            st.markdown("---")
            st.subheader("📊 Resultaten Overzicht")

            # 1. Geformatteerde tabel met HTML en kleuren
            summary_data = []
            for r in results:
                summary_data.append({
                    "Ticker": f"<b>{r['symbol']}</b>",
                    "Koers": f"${r['close']:.2f}",
                    "Verandering": f"<span style='color: {'#28a745' if r['change'] > 0 else '#dc3545'};'>{r['pct_change']:+.2f}%</span>",
                    "Richting": r["arrow"],
                    "Short-Term Rating": get_star_html(r['st_stars']),
                    "Mid-Term Rating": get_star_html(r['mt_stars']),
                    "RSI (14)": get_rsi_html(r['rsi'])
                })
            
            # Zet om naar DataFrame en render als HTML-tabel
            df_html = pd.DataFrame(summary_data).to_html(escape=False, index=False)
            st.markdown(df_html, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🔍 Gedetailleerde Kaarten")

            # 2. Detailkaarten per aandeel (2 kolommen per rij)
            cols = st.columns(2)
            for idx, r in enumerate(results):
                col = cols[idx % 2]
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {r['symbol']} &nbsp; {r['arrow']}")
                        st.metric("Huidige Koers", f"${r['close']:.2f}", f"{r['change']:+.2f} ({r['pct_change']:+.2f}%)")
                        
                        st.write("**Short-Term Rating:**")
                        st.markdown(get_star_html(r['st_stars']), unsafe_allow_html=True)

                        st.write("**Mid-Term Rating:**")
                        st.markdown(get_star_html(r['mt_stars']), unsafe_allow_html=True)
                        
                        st.write("**RSI (14):**")
                        st.markdown(get_rsi_html(r['rsi']), unsafe_allow_html=True)
