def generate_trade_advice(df):
    """
    Return a markdown string with trade advice based on the stock DataFrame.
    """
    advice = []
    latest = df.iloc[-1]

    # Basic template
    if latest["close"] > latest["50dma"]:
        advice.append("- Price is above 50DMA, confirming short-term uptrend.")
    if latest["close"] > latest["150dma"]:
        advice.append("- Price is above 150DMA, confirming medium-term strength.")
    if latest["close"] > latest["200dma"]:
        advice.append("- Price is above 200DMA, confirming long-term trend.")

    if "rsi" in df.columns:
        if latest["rsi"] > 70:
            advice.append("- RSI is above 70: overbought, but strong momentum.")
        elif latest["rsi"] > 60:
            advice.append("- RSI above 60: healthy trend.")

    if "volume" in df.columns:
        if df["volume"].mean() > 1_000_000:
            advice.append("- Strong trading volume (liquidity OK for swing/position trades).")
        else:
            advice.append("- Low volume: may be harder to enter/exit positions.")

    advice.append("*Set stops near the 50DMA or below recent support. Consider partial profits at new highs.*")
    return "\n".join(advice)
