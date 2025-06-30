import pandas as pd

def clean_ohlcv(df):
    """
    Lowercase column names, remove duplicates.
    """
    df.columns = [col.lower() for col in df.columns]
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()]
    return df


def flatten_close_column(df):
    """
    Ensures 'close' column is a numeric Series, flattening dicts, lists, or DataFrames if needed.
    """
    # If 'close' is a DataFrame, take the first column
    if isinstance(df["close"], pd.DataFrame):
        df["close"] = df["close"].iloc[:, 0]

    # If any element is a dict, extract 'adjClose' or 'close'
    if any(isinstance(x, dict) for x in df["close"]):
        df["close"] = df["close"].apply(
            lambda x: x.get("adjClose", x.get("close")) if isinstance(x, dict) else x
        )

    # If any element is a list, get the first value
    if any(isinstance(x, list) for x in df["close"]):
        df["close"] = df["close"].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x
        )

    # If 'close' is still a DataFrame (rare, but possible), take first column
    if isinstance(df["close"], pd.DataFrame):
        df["close"] = df["close"].iloc[:, 0]

    # Force everything to numeric
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df