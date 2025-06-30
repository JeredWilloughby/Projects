def apply_minervini_filter(df, standard=True, advanced=True):
    """
    Return True if the DataFrame passes Minervini trend template rules.
    """
    if df is None or df.empty:
        return False

    latest = df.iloc[-1]
    conditions = [
        latest["close"] > latest["150dma"] > latest["200dma"],
        latest["50dma"] > latest["150dma"],
        latest["50dma"] > latest["200dma"],
        latest["close"] > latest["50dma"],
        latest["close"] > latest["200dma"],
        df["200dma"].iloc[-1] > df["200dma"].iloc[-21],  # 1 month upward
    ]
    if not all(conditions):
        return False

    # Optionally add advanced checks
    if advanced:
        if "rsi" in df.columns and latest["rsi"] < 60:
            return False
        if "volume" in df.columns and df["volume"].mean() < 1_000_000:
            return False

    return True
