def score_stock(df):
    """
    Assign a more nuanced score to a stock based on Minervini/CANSLIM-style signals.
    Higher is better. Range: -10 to 20+
    """
    try:
        score = 0
        latest = df.iloc[-1]

        # Price above moving averages (reward by % above)
        for ma in ["50dma", "150dma", "200dma"]:
            if ma in latest and latest[ma] > 0:
                pct = (latest["close"] - latest[ma]) / latest[ma] * 100
                score += max(0, min(4, pct / 2))  # Up to +4 for way above

        # Moving average stack
        if latest["50dma"] > latest["150dma"]:
            score += 2
        if latest["150dma"] > latest["200dma"]:
            score += 2

        # 200dma trending up over past 21 days (~1 month)
        if "200dma" in df.columns and len(df) > 21:
            if df["200dma"].iloc[-1] > df["200dma"].iloc[-21]:
                score += 2

        # Bonus for price near 52wk high (within 5%)
        high_52w = df["close"].rolling(window=252, min_periods=20).max().iloc[-1]
        if latest["close"] >= 0.95 * high_52w:
            score += 2

        # RSI boost (reward high, penalize low)
        if "rsi" in df.columns:
            if latest["rsi"] > 60:
                score += 1
            if latest["rsi"] > 70:
                score += 1
            if latest["rsi"] < 45:
                score -= 1

        # Volume boost (reward > 1M avg volume, penalize < 250k)
        if "volume" in df.columns:
            avg_vol = df["volume"].tail(90).mean()
            if avg_vol > 1_000_000:
                score += 1
            elif avg_vol < 250_000:
                score -= 1

        return round(score, 2)
    except Exception as e:
        print(f"[Score Error] {e}")
        return 0
