def canslim_c_score(eps_growth):
    """
    Assign CANSLIM 'C' score based on EPS growth (quarterly, ideally >20%).
    Returns: 2 for strong growth, 1 for moderate, 0 for weak/negative.
    """
    if eps_growth is None:
        return 0
    if eps_growth > 0.25:
        return 2
    if eps_growth > 0.10:
        return 1
    return 0

def score_stock(df):
    """
    Assign a score to a stock based on Minervini momentum, trend, and volume.
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
    except Exception as e:
        print(f"[Score Error] {e}")
        return 0
