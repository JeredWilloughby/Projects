import pandas as pd

def save_sp500_tickers(filename="sp500_tickers.txt"):
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    tickers = df['Symbol'].tolist()
    # Convert e.g. BRK.B to BRK-B for most data providers (if needed)
    tickers = [s.replace('.', '-') for s in tickers]
    with open(filename, "w") as f:
        for t in tickers:
            f.write(t + "\n")
    print(f"Saved {len(tickers)} S&P 500 tickers to {filename}")

if __name__ == "__main__":
    save_sp500_tickers()
