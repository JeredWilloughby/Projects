import pandas as pd
import ta

def apply_minervini_filter(df, standard=True, advanced=False):
    """
    Apply Minervini trend template filter rules.
    :param df: DataFrame with required columns
    :param standard: Apply base rules (DMA crossovers etc.)
    :param advanced: Apply volume, RSI, ATR enhancements
    :return: True if stock passes filter
    """
    try:
        latest = df.iloc[-1]

        # --- Standard Rules ---
        if standard:
            cond1 = latest["close"] > latest["150dma"] > latest["200dma"]
            cond2 = latest["50dma"] > latest["150dma"]
            cond3 = latest["close"] > latest["50dma"]
            cond4 = latest["close"] > latest["200dma"]
            dma_20_days_ago = df["200dma"].shift(20).iloc[-1]
            cond5 = latest["200dma"] > dma_20_days_ago

            if not all([cond1, cond2, cond3, cond4, cond5]):
                return False

        # --- Advanced Rules ---
        if advanced:
            if "volume" in df.columns and df["volume"].mean() < 500_000:
                return False
            if "rsi" in df.columns and latest["rsi"] < 50:
                return False

        return True

    except Exception as e:
        print(f"[Filter Error] {e}")
        return False
