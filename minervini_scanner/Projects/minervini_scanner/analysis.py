def generate_analysis(df):
    latest = df.iloc[-1]
    insights = []

    distance = (latest['close'] - latest['50DMA']) / latest['50DMA'] * 100
    if distance > 10:
        insights.append(f"📈 Price is extended {distance:.1f}% above 50DMA — watch for pullback.")
    elif distance < -5:
        insights.append(f"📉 Price is trading well below 50DMA — weak trend.")
    else:
        insights.append("✅ Price is in strong trend zone near 50DMA.")

    slope_check = df['200DMA'].iloc[-1] > df['200DMA'].iloc[-30]
    if slope_check:
        insights.append("✅ 200DMA is sloping upward.")
    else:
        insights.append("⚠️ 200DMA is flat or declining — trend may be weakening.")

    return "\n".join(insights)
