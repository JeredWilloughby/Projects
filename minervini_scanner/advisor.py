import numpy as np

def generate_trade_advice(df, ticker=""):
    advice = []
    latest = df.iloc[-1]
    close = latest["close"]

    # 1. Entry Signal Confirmation
    if close > latest["50dma"] and close > latest["150dma"] and close > latest["200dma"]:
        advice.append("✅ **Strong entry signal:** Price is above all major moving averages, suggesting a strong trend.")
    else:
        advice.append("⚠️ **Entry Caution:** Price is not above all moving averages. Consider waiting for stronger confirmation.")

    # 2. Volume Confirmation
    if "volume" in df.columns and df["volume"].mean() > 2_000_000:
        advice.append("💡 **Institutional volume detected:** Higher trading volume confirms institutional interest.")
    else:
        advice.append("⚠️ **Low trading volume:** Beware of low liquidity, which can lead to increased risk.")

    # 3. Stop-Loss Calculation (using ATR if available, else fixed %)
    atr = None
    if "atr" in df.columns:
        atr = latest["atr"]
    else:
        # Calculate simple ATR if not present
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)
        tr = np.maximum(high - low, np.maximum(abs(high - prev_close), abs(low - prev_close)))
        atr = tr.rolling(window=14).mean().iloc[-1]
    stop_loss = close - (2 * atr if atr is not None else 0.05 * close)
    advice.append(f"🛑 **Risk Management:** Set initial stop-loss at **${stop_loss:.2f}** (2 ATR below entry price). Limit risk to 1% of portfolio per trade.")

    # 4. Position Sizing (Van Tharp Model: % risk per trade)
    portfolio_size = 100_000  # Example size, can be user-configured
    risk_per_trade = 0.01 * portfolio_size  # 1% risk
    position_size = risk_per_trade / (close - stop_loss)
    shares = int(position_size)
    advice.append(f"📊 **Position Sizing:** Buy **{shares} shares** (max) to keep risk at 1% of your portfolio.")

    # 5. Trailing Stops & Profit Taking
    advice.append("🔁 **Trailing Stop:** As price moves up, trail stop to 1 ATR below latest close. Lock in gains, let winners run.")
    advice.append("💰 **Profit Target:** Consider taking partial profits at previous highs or after 20%+ moves. Never let a winner turn into a loss.")

    # 6. Market Environment Check
    advice.append("🌎 **Market Context:** Ensure market indexes are trending up. Consider sector strength and recent earnings/events.")

    # 7. Diversification & Portfolio
    advice.append("📈 **Diversify:** Avoid over-concentration. Limit exposure to one sector or correlated stocks.")

    # 8. Resources
    advice.append(
        "🔗 [CANSLIM Explained](https://www.youtube.com/watch?v=5Bnz9yiyc14) — Learn O'Neil’s top growth trading method for further edge."
    )

    # Wrap-up
    advice.append("> **Pro tip:** Review your trade journal, and only take A+ setups. Risk management beats prediction.")

    return "\n\n".join(advice)
