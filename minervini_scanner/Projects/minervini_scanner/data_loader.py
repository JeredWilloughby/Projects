import requests
import pandas as pd
import os

def get_ohlcv(ticker, start_date, end_date):
    """
    Fetch OHLCV data from Tiingo for the given ticker and date range.
    Returns a DataFrame indexed by date.
    """
    api_key = "a598a521123b14988fe9ec80356c65b767223576"

    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "format": "json",
        "resampleFreq": "daily",
        "columns": "open,high,low,close,volume"
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if df.empty or "date" not in df.columns:
            return pd.DataFrame()
        df.set_index('date', inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def get_index_tickers(source="sp500"):
    """
    Returns a list of tickers for the given source.
    For now, only supports S&P 500, loaded from sp500_tickers.txt.
    """
    if source == "sp500":
        ticker_file = "sp500_tickers.txt"
    else:
        raise ValueError("Only 'sp500' source currently supported.")

    if not os.path.exists(ticker_file):
        raise FileNotFoundError(
            f"{ticker_file} not found. Run build_ticker_file.py to create it."
        )

    with open(ticker_file, "r") as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers
