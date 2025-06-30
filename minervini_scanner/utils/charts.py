import plotly.graph_objs as go

def plot_price_chart(data, symbol):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["open"], high=data["high"], low=data["low"], close=data["close"],
        name="Price"
    ))
    if "50dma" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["50dma"],
            name="50DMA",
            line=dict(color='blue', width=2)
        ))
    if "150dma" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["150dma"],
            name="150DMA",
            line=dict(color='green', width=2)
        ))
    if "200dma" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["200dma"],
            name="200DMA",
            line=dict(color='red', width=2)
        ))
    fig.update_layout(title=f"{symbol} Price Chart", xaxis_title="Date", yaxis_title="Price")
    return fig
