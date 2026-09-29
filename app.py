import yfinance as yf
import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    """Bereken de Relative Strength Index (RSI)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_stoxline_score(ticker_symbol):
    ticker_symbol = ticker_symbol.strip().upper()
    
    try:
        # 1. Haal historische marktdata op via yfinance
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y")

        if df.empty or len(df) < 50:
            print(f"\n❌ Geen of onvoldoende data gevonden voor ticker: {ticker_symbol}")
            return

        # 2. Bereken technische indicatoren
        # Moving Averages
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # RSI (14 periodes)
        df['RSI'] = calculate_rsi(df['Close'], 14)
        
        # MACD (12, 26, 9)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # Laatste datapunten ophalen
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close_price = latest['Close']
        price_change = close_price - prev['Close']
        pct_change = (price_change / prev['Close']) * 100

        # -------------------------------------------------------------
        # 3. KORTE TERMIJN SCORE (Short-Term: 1 tot 5 sterren)
        # -------------------------------------------------------------
        st_points = 0
        
        if close_price > latest['SMA_5']:
            st_points += 1.25
            
        if latest['SMA_5'] > prev['SMA_5']:
            st_points += 1.25
            
        if 45 <= latest['RSI'] <= 70:
            st_points += 1.25
        elif latest['RSI'] > 70:
            st_points += 0.5
            
        if latest['MACD'] > latest['MACD_Signal']:
            st_points += 1.25

        short_term_stars = int(round(st_points))
        short_term_stars = min(max(short_term_stars, 0), 5)

        # -------------------------------------------------------------
        # 4. MIDDELLANGE TERMIJN SCORE (Mid-Term: 1 tot 5 sterren)
        # -------------------------------------------------------------
        mt_points = 0
        
        if close_price > latest['SMA_20']:
            mt_points += 1.25
            
        if close_price > latest['SMA_50']:
            mt_points += 1.25
            
        if latest['SMA_20'] > latest['SMA_50']:
            mt_points += 1.25
            
        if latest['MACD'] > 0:
            mt_points += 1.25

        mid_term_stars = int(round(mt_points))
        mid_term_stars = min(max(mid_term_stars, 0), 5)

        # -------------------------------------------------------------
        # 5. RICHTING EN PIJL (Up / Down Arrow)
        # -------------------------------------------------------------
        if price_change > 0:
            arrow = "⬆️ (UP)"
        elif price_change < 0:
            arrow = "⬇️ (DOWN)"
        else:
            arrow = "➡️ (NEUTRAL)"

        # Resultaatweergave
        print(f"\n=============================================")
        print(f"  STOXLINE ANALYSE VOOR: {ticker_symbol}")
        print(f"=============================================")
        print(f"Huidige Koers    : ${close_price:.2f} ({price_change:+.2f} / {pct_change:+.2f}%) {arrow}")
        print(f"Short-Term Rating: {'★' * short_term_stars}{'☆' * (5 - short_term_stars)} ({short_term_stars}/5 sterren)")
        print(f"Mid-Term Rating  : {'★' * mid_term_stars}{'☆' * (5 - mid_term_stars)} ({mid_term_stars}/5 sterren)")
        print(f"---------------------------------------------")
        print(f"RSI (14)         : {latest['RSI']:.2f}")
        print(f"SMA 5 / 20 / 50  : {latest['SMA_5']:.2f} / {latest['SMA_20']:.2f} / {latest['SMA_50']:.2f}")
        print(f"=============================================\n")

    except Exception as e:
        print(f"❌ Er is een fout opgetreden bij het verwerken van {ticker_symbol}: {e}")

# =============================================================
# INTERACTIEVE INVOER
# =============================================================
if __name__ == "__main__":
    print("--- STOXLINE AI / TECHNICAL SCORE CALCULATOR ---")
    print("Voer een of meerdere tickers in (bijv: AMBA, NVDA, TSLA, ASML.AS).")
    print("Typ 'exit' of 'stop' om te stoppen.\n")

    while True:
        user_input = input("Voer ticker(s) in: ").strip()
        
        if user_input.lower() in ['exit', 'stop', 'quit', '']:
            print("Programma afgesloten.")
            break
            
        # Splits meerdere tickers op basis van een komma
        tickers = user_input.split(',')
        
        for ticker in tickers:
            if ticker.strip():
                get_stoxline_score(ticker)
