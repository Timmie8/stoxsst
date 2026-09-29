import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Pagina configuratie
st.set_page_config(page_title="Stoxline Multi-Stock Scanner Advanced", layout="wide")

st.title("📈 Stoxline AI Rating Scanner (Advanced)")
st.caption("Voer meerdere tickers in gescheiden door een komma (bijv: AMBA, NVDA, TSLA, ASML.AS)")

def calculate_rsi(series, period=14):
    """Bereken RSI (14)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_star_html(rating):
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
    if rsi > 55:
        color = "#28a745"  # Groen
    elif rsi < 45:
        color = "#dc3545"  # Rood
    else:
        color = "#6c757d"  # Grijs
    return f'<span style="color: {color}; font-weight: bold;">{rsi:.1f}</span>'

def get_pcr_html(pcr):
    if pcr is None or np.isnan(pcr):
        return "<span style='color: #6c757d;'>N/A</span>"
    # PCR < 0.8 is bullish (Groen), > 1.0 is bearish (Rood)
    if pcr < 0.8:
        color = "#28a745"
    elif pcr > 1.0:
        color = "#dc3545"
    else:
        color = "#6c757d"
    return f'<span style="color: {color}; font-weight: bold;">{pcr:.2f}</span>'

def get_short_float_html(sf):
    if sf is None or np.isnan(sf):
        return "<span style='color: #6c757d;'>N/A</span>"
    sf_pct = sf * 100 if sf < 1 else sf  # Corrigeer indien meegegeven als decimaal
    # Short float < 5% is bullish/veilig (Groen), > 15% is hoog risico/bearish (Rood)
    if sf_pct < 5.0:
        color = "#28a745"
    elif sf_pct > 15.0:
        color = "#dc3545"
    else:
        color = "#6c757d"
    return f'<span style="color: {color}; font-weight: bold;">{sf_pct:.2f}%</span>'

@st.cache_data(ttl=600)
def fetch_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y", timeout=10)
        info = stock.info
        return df, info, stock
    except Exception:
        return None, None, None

def get_put_call_ratio(stock_obj):
    try:
        options = stock_obj.options
        if not options:
            return None
        # Haal de dichtstbijzijnde optie-expiratie op
        opt = stock_obj.option_chain(options[0])
        total_calls_volume = opt.calls['volume'].sum()
        total_puts_volume = opt.puts['volume'].sum()
        if total_calls_volume > 0:
            return total_puts_volume / total_calls_volume
    except Exception:
        pass
    return None

def analyze_ticker(symbol):
    df, info, stock_obj = fetch_stock_data(symbol)
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
    short_float = info.get('shortPercentOfFloat', None) if info else None
    pcr = get_put_call_ratio(stock_obj) if stock_obj else None

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

# --- GEBRUIKERSINVOER ---
input_tickers = st.text_input("Voer ticker(s) in:", "AMBA, NVDA, TSLA, ASML.AS")

if st.button("🔍 Scan Aandelen") or input_tickers:
    tickers_list = [t.strip().upper() for t in input_tickers.split(",") if t.strip()]

    if not tickers_list:
        st.warning("Voer minimaal één geldige ticker in.")
    else:
        results = []
        with st.spinner("Aandelen en optiedata analyseren..."):
            for symbol in tickers_list:
                res = analyze_ticker(symbol)
                if res:
                    results.append(res)
                else:
                    st.error(f"❌ Geen data gevonden voor **{symbol}**")

        if results:
            st.markdown("---")
            st.subheader("📊 Resultaten Overzicht")

            # Geformatteerde tabel
            summary_data = []
            for r in results:
                summary_data.append({
                    "Ticker": f"<b>{r['symbol']}</b>",
                    "Koers": f"${r['close']:.2f}",
                    "Verandering": f"<span style='color: {'#28a745' if r['change'] > 0 else '#dc3545'};'>{r['pct_change']:+.2f}%</span>",
                    "Richting": r["arrow"],
                    "Short-Term": get_star_html(r['st_stars']),
                    "Mid-Term": get_star_html(r['mt_stars']),
                    "RSI (14)": get_rsi_html(r['rsi']),
                    "Put/Call Ratio": get_pcr_html(r['pcr']),
                    "Short Float": get_short_float_html(r['short_float']),
                    "Support (60d)": f"${r['support']:.2f} (<span style='color:#dc3545;'>{r['support_pct']:.1f}%</span>)",
                    "Resistance (60d)": f"${r['resistance']:.2f} (<span style='color:#28a745;'>{r['resistance_pct']:+.1f}%</span>)"
                })
            
            df_html = pd.DataFrame(summary_data).to_html(escape=False, index=False)
            st.markdown(df_html, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("🔍 Gedetailleerde Kaarten")

            cols = st.columns(2)
            for idx, r in enumerate(results):
                col = cols[idx % 2]
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {r['symbol']} &nbsp; {r['arrow']}")
                        st.metric("Huidige Koers", f"${r['close']:.2f}", f"{r['change']:+.2f} ({r['pct_change']:+.2f}%)")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write("**Short-Term Rating:**")
                            st.markdown(get_star_html(r['st_stars']), unsafe_allow_html=True)
                            st.write("**Mid-Term Rating:**")
                            st.markdown(get_star_html(r['mt_stars']), unsafe_allow_html=True)
                            st.write("**RSI (14):**")
                            st.markdown(get_rsi_html(r['rsi']), unsafe_allow_html=True)
                        
                        with col_b:
                            st.write("**Put/Call Ratio:**")
                            st.markdown(get_pcr_html(r['pcr']), unsafe_allow_html=True)
                            st.write("**Short Float:**")
                            st.markdown(get_short_float_html(r['short_float']), unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.write(f"**Support:** ${r['support']:.2f} ({r['support_pct']:.1f}%)")
                        st.write(f"**Resistance:** ${r['resistance']:.2f} ({r['resistance_pct']:+.1f}%)")
