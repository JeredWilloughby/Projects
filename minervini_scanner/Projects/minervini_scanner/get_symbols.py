import pandas as pd

# Get S&P 500 symbols
sp500_df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
sp500 = sp500_df['Symbol'].tolist()

# Get NASDAQ-100 symbols
nasdaq_df = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")[4]
nasdaq = nasdaq_df['Ticker'].tolist()

# Merge and deduplicate
all_tickers = sorted(set(sp500 + nasdaq))
all_tickers = [s.replace('.', '-') for s in all_tickers]  # Yahoo uses '-' instead of '.'

# Export to static file or print
print(all_tickers)
