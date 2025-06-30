def score_stock(df):
    """
    Assign a score to a stock based on momentum, trend, and volume.
    Higher is better.
    """
    try:
        score = 0
        latest = df.iloc[-1]

        # Price above moving averages
        if latest["close"] > latest["50dma"]:
            score += 1
        if latest["close"] > latest["150dma"]:
            score += 1
        if latest["close"] > latest["200dma"]:
            score += 1

        # Moving average stack
        if latest["50dma"] > latest["150dma"]:
            score += 1
        if latest["150dma"] > latest["200dma"]:
            score += 1

        # RSI boost
        if "rsi" in df.columns:
            if latest["rsi"] > 60:
                score += 1
            if latest["rsi"] > 70:
                score += 1

        # Volume boost
        if "volume" in df.columns and df["volume"].mean() > 1_000_000:
            score += 1

        return score

    except Exception:
        return 0
