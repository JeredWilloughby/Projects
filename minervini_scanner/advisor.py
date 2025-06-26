import numpy as np
import ta  # Technical Analysis library

def generate_trade_advice(df):
    """
    Generate basic swing trade advice using ATR and price levels.
    Returns a markdown string with trade levels and strategy notes.
    """
    # Ensure columns are lowercase
    df.columns = [c.lower() for c in df.columns]

    # Calculate ATR if missing
    if 'atr' not in df.columns:
        df['atr'] = ta.volatility.average_true_range(
            df['high'], df['low'], df['close'], window=14
        )

    # Use the most recent close price
    entry = round(df['close'].iloc[-1], 2)
    atr = df['atr'].iloc[-1]
    stop = round(entry - 1.5 * atr, 2)
    target = round(entry * 1.25, 2)

    return f"""
🔖 **Entry Price:** {entry}  
🔻 **Stop Loss:** {stop}  *(~{round(100*(entry - stop)/entry):.0f}% below entry)*  
🎯 **Profit Target:** {target}  *(25% above entry)*

📘 **Strategy Notes:**
- Consider partial profit at 15–20% gains.
- Raise stop to breakeven after a 10–12% gain.
- Exit or reevaluate if price closes below 50DMA or breaks trend.
- Stop-loss dynamically adjusts based on ATR (current: {round(atr, 2)}).
- Sizing can use ATR or % risk.
- Ideal for swing setups with technical confirmation.
"""
