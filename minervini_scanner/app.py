import streamlit as st
import datetime
import pandas as pd
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from data_loader import get_ohlcv, get_index_tickers
from minervini_filters import apply_minervini_filter
from ranking import score_stock
from advisor import generate_trade_advice
from utils.charts import plot_price_chart
from db import ScanResult, Session

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(page_title="Minervini Scanner", layout="wide")

tab1, tab2 = st.tabs(["📉 Scanner", "📘 Strategy Info"])

if "top_results" not in st.session_state:
    st.session_state.top_results = []
if "table_df" not in st.session_state:
    st.session_state.table_df = pd.DataFrame()
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = None

SKIPPED_FILE = "skipped_tickers.txt"

def scan_single_ticker(
    ticker, start_date, end_date, use_standard, use_advanced, today,
    max_retries=3, debug_bypass_filter=False
):
    session = Session()
    try:
        df = None
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                df = get_ohlcv(ticker, start_date, end_date)
                break
            except Exception as fetch_err:
                last_error = fetch_err
                time.sleep(1 + attempt)
        else:
            print(f"[ERROR] {ticker}: {last_error}")
            return None, f"ERROR: {last_error}"

        if df is None or df.empty:
            print(f"[EMPTY] {ticker}: No data")
            return None, None

        df.columns = [col.lower() for col in df.columns]
        df.dropna(subset=["close"], inplace=True)
        df.index = pd.to_datetime(df.index)
        df["50dma"] = df["close"].rolling(window=50).mean()
        df["150dma"] = df["close"].rolling(window=150).mean()
        df["200dma"] = df["close"].rolling(window=200).mean()

        if debug_bypass_filter:
            passed = True
        else:
            passed = apply_minervini_filter(df, standard=use_standard, advanced=use_advanced)

        if passed:
            score = score_stock(df)
            rules = []
            if use_standard:
                rules.append("Basic")
            if use_advanced:
                rules.append("Advanced")
            return {"Ticker": ticker, "Score": score, "Data": df, "Rules": " & ".join(rules)}, None
        else:
            return None, None
    except Exception as e:
        traceback.print_exc()
        return None, f"FATAL: {e}"
    finally:
        session.close()

def run_market_scan(
    tickers, start_date, end_date, use_standard, use_advanced,
    max_workers=8, max_retries=3, debug_bypass_filter=False
):
    today = datetime.datetime.now(datetime.UTC).date()  # UTC-safe
    score_table = []
    skipped_tickers = []
    st.info(f"Scanning {len(tickers)} tickers in parallel (workers: {max_workers})...")
    progress = st.progress(0, text="Starting parallel scan...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                scan_single_ticker,
                ticker,
                start_date,
                end_date,
                use_standard,
                use_advanced,
                today,
                max_retries,
                debug_bypass_filter
            ) for ticker in tickers
        ]
        total = len(futures)
        completed = 0
        for future in as_completed(futures):
            try:
                result, skip_reason = future.result(timeout=60)
                if result is not None:
                    score_table.append(result)
                elif skip_reason and (
                    "timeout" in str(skip_reason).lower() or
                    "error" in str(skip_reason).lower() or
                    "fatal" in str(skip_reason).lower()
                ):
                    skipped_tickers.append((tickers[completed], skip_reason))
            except Exception as err:
                ticker = tickers[completed]
                skipped_tickers.append((ticker, f"FUTURE ERROR: {err}"))
                print(f"[THREAD ERROR] {ticker}: {err}")
            completed += 1
            progress.progress(min(completed / total, 1.0), text=f"Scanned {completed}/{total}")

    print("run_market_scan completed:", completed, "of", total)
    print("Results:", len(score_table), "Skipped:", len(skipped_tickers))

    if skipped_tickers:
        with open(SKIPPED_FILE, "w") as f:
            for ticker, reason in skipped_tickers:
                f.write(f"{ticker}: {reason}\n")
        st.warning(f"Skipped {len(skipped_tickers)} tickers. See '{SKIPPED_FILE}' for details.")
    else:
        if os.path.exists(SKIPPED_FILE):
            os.remove(SKIPPED_FILE)
    return score_table

def get_skipped_tickers_from_file():
    if not os.path.exists(SKIPPED_FILE):
        return []
    with open(SKIPPED_FILE, "r") as f:
        return [line.split(":")[0].strip() for line in f if line.strip() and not line.startswith("#")]

with tab1:
    st.title("📈 Top Momentum Stocks — S&P 500 + NASDAQ 100")
    start_date = st.text_input("Start Date", value="2024/01/01")
    end_date = st.text_input("End Date", value=pd.Timestamp.today().strftime("%Y/%m/%d"))
    use_standard = st.checkbox("Apply Standard Minervini Rules", value=True)
    use_advanced = st.checkbox("Apply Advanced Rules (Volume, RSI, etc.)", value=True)
    top_n_options = ["10", "20", "30", "All"]
    top_n_choice = st.selectbox("Number of Top Stocks to Show", top_n_options, index=0)
    top_n = None if top_n_choice == "All" else int(top_n_choice)

    col1, _ = st.columns(2)
    with col1:
        run_scan = st.button("Run Full Market Scan")

    if run_scan:
        tickers = get_index_tickers()
        st.session_state.top_results = []
        score_table = run_market_scan(
            tickers, start_date, end_date, use_standard, use_advanced,
            max_workers=8, max_retries=3
        )
        if score_table:
            sorted_results = sorted(score_table, key=lambda x: x["Score"], reverse=True)
            if top_n:
                sorted_results = sorted_results[:top_n]
            st.session_state.top_results = sorted_results
            st.success(f"✅ Scan complete! {len(sorted_results)} stocks shown.")
        else:
            st.warning("⚠️ No stocks passed the filters. Try adjusting your rules or date range.")

    # Prepare DataFrame for AgGrid
    if st.session_state.top_results:
        table_data = [
            {
                "Symbol": item["Ticker"],
                "Score": item["Score"],
                "Rules Passed": item.get("Rules", "")
            }
            for item in st.session_state.top_results
        ]
        table_df = pd.DataFrame(table_data)
        st.session_state.table_df = table_df
    else:
        table_df = st.session_state.table_df

        if not table_df.empty:
            st.subheader(f"📊 Scanned Results ({len(table_df)})")
            gb = GridOptionsBuilder.from_dataframe(table_df)
            gb.configure_selection('single', use_checkbox=False)
            gb.configure_column("Symbol", headerCheckboxSelection=False)
            grid_options = gb.build()
    
            aggrid_response = AgGrid(
                table_df,
                gridOptions=grid_options,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True,
                theme="streamlit",
                height=350,
                enable_enterprise_modules=False,
            )
    
            selected_symbol = None
            selected_rows = aggrid_response.get("selected_rows")
    
            # Robust selection extraction, no KeyError possible:
            if isinstance(selected_rows, list) and len(selected_rows) > 0:
                first = selected_rows[0]
                # Sometimes AgGrid gives a dict, sometimes a pandas Series (rare)
                if isinstance(first, dict):
                    selected_symbol = first.get("Symbol") or first.get("symbol")
                elif hasattr(first, "get"):  # pandas Series
                    selected_symbol = first.get("Symbol") or first.get("symbol")
            elif hasattr(selected_rows, "empty") and not selected_rows.empty:
                # DataFrame style
                if "Symbol" in selected_rows.columns:
                    selected_symbol = selected_rows.iloc[0]["Symbol"]
                elif "symbol" in selected_rows.columns:
                    selected_symbol = selected_rows.iloc[0]["symbol"]
    
            if selected_symbol is None:
                # Persist last selection if present
                selected_symbol = st.session_state.get("selected_symbol", None)
            else:
                st.session_state["selected_symbol"] = selected_symbol
    
            # Chart/advice for the selected symbol
            if selected_symbol:
                item = next((item for item in st.session_state.top_results if item["Ticker"] == selected_symbol), None)
                if item:
                    st.markdown(f"### 📊 {item['Ticker']} (Score: {item['Score']}, Passed: {item.get('Rules', '')})")
                    st.markdown("**Price Chart**")
                    fig = plot_price_chart(item["Data"], item["Ticker"])
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown("### 💡 Trade Strategy")
                    st.markdown(generate_trade_advice(item["Data"]))


    # Branding footer
    st.markdown(
        "<hr style='margin-top: 40px; margin-bottom: 10px;'/><div style='text-align: center; color: gray;'>Created by Jered Willoughby</div>",
        unsafe_allow_html=True
    )

with tab2:
    st.header("📓 Strategy & Rules Summary")
    st.markdown("""
### 📊 Score Breakdown

The score for each stock is based on the following factors:

| Criteria | Points |
| --- | --- |
| Price > 50DMA | 1 |
| Price > 150DMA | 1 |
| Price > 200DMA | 1 |
| 50DMA > 150DMA | 1 |
| 150DMA > 200DMA | 1 |
| RSI > 60 | 1 |
| RSI > 70 | 1 |
| Avg. Volume > 1M | 1 |

Higher scores = stronger technical momentum.

---

### 📈 Visual Example:

[<img src="https://pbs.twimg.com/media/EA2IYZTUEAIk51h?format=jpg&name=large" width="500"/>](https://x.com/ProdigalTrader/status/1156115610532634624/photo/1)
<sub>Sample Minervini Trend Template</sub>

---

### 💡 Why These Rules Work

- **Price above moving averages** shows uptrend strength and institutional demand.
- **Moving averages stacked in order** (50DMA > 150DMA > 200DMA) reflects sustained momentum.
- **RSI & volume** help confirm breakouts are real, not random.
- **These rules** filter for stocks most likely to outperform in uptrending markets.

---

### 📚 Classic Examples

- [Minervini's Risk Management (Case Study)](https://traderlion.com/investing-champions/mark-minervinis-risk-management/)
- [CANSLIM: How to Make Money in Stocks by William O’Neil](https://www.financialwisdomtv.com/post/how-to-make-money-in-stocks-by-william-o-neil)

---

### 🏆 Strategy Influences

- Mark Minervini (Trend Template)
- William O’Neil (CANSLIM)
- Van Tharp (Position Sizing)
- Ralph Vince (Optimal f)
- Edwards & Magee (Charting)
- ATR-Based Stops

---

> The strategy module uses a fusion of these methods to provide conservative yet high-upside trade setups.

---

<div style='text-align: center; color: gray; margin-top: 36px;'>Created by Jered Willoughby</div>
""", unsafe_allow_html=True)
