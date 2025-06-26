import streamlit as st
import datetime
import pandas as pd
from io import StringIO
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import traceback

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

SKIPPED_FILE = "skipped_tickers.txt"

def scan_single_ticker(
    ticker, start_date, end_date, use_standard, use_advanced, today,
    max_retries=3
):
    session = Session()
    try:
        existing = session.query(ScanResult).filter_by(ticker=ticker, scan_date=today).first()
        if existing:
            if existing.error_msg:
                return None, existing.error_msg
            if existing.filter_passed:
                df = pd.read_json(StringIO(existing.data_json))
                return {"Ticker": ticker, "Score": existing.score, "Rules": existing.rules_passed, "Data": df}, None
            else:
                return None, None

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
            record = ScanResult(
                ticker=ticker, scan_date=today, score=None, filter_passed=False,
                rules_passed=None, data_json=None, error_msg=str(last_error)
            )
            session.merge(record)
            session.commit()
            print(f"[ERROR] {ticker}: {last_error}")
            return None, f"ERROR: {last_error}"

        if df is None or df.empty:
            record = ScanResult(
                ticker=ticker, scan_date=today, score=None, filter_passed=False,
                rules_passed=None, data_json=None, error_msg="No data"
            )
            session.merge(record)
            session.commit()
            return None, None

        df.columns = [col.lower() for col in df.columns]
        df.dropna(subset=["close"], inplace=True)
        df.index = pd.to_datetime(df.index)
        df["50dma"] = df["close"].rolling(window=50).mean()
        df["150dma"] = df["close"].rolling(window=150).mean()
        df["200dma"] = df["close"].rolling(window=200).mean()


        score = score_stock(df) if passed else None

        # Save to DB
        record = ScanResult(
            ticker=ticker,
            scan_date=today,
            score=score,
            filter_passed=bool(passed),
            rules_passed=rules_type,
            data_json=df.to_json() if passed else None,
            error_msg=None
        )
        session.merge(record)
        session.commit()

        if passed:
            return {"Ticker": ticker, "Score": score, "Rules": rules_type, "Data": df}, None
        else:
            return None, None
    except Exception as e:
        session.rollback()
        record = ScanResult(
            ticker=ticker, scan_date=today, score=None, filter_passed=False,
            rules_passed=None, data_json=None, error_msg=f"FATAL: {e}"
        )
        session.merge(record)
        session.commit()
        print(f"[FATAL] {ticker}: {e}")
        traceback.print_exc()
        return None, f"FATAL: {e}"
    finally:
        session.close()

def run_market_scan(
    tickers, start_date, end_date, use_standard, use_advanced,
    max_workers=8, max_retries=3
):
    today = datetime.datetime.utcnow().date()
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
                max_retries
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
                    print(f"[SKIPPED] {tickers[completed]}: {skip_reason}")
            except Exception as err:
                ticker = tickers[completed]
                skipped_tickers.append((ticker, f"FUTURE ERROR: {err}"))
                print(f"[THREAD ERROR] {ticker}: {err}")
            completed += 1
            progress.progress(min(completed / total, 1.0), text=f"Scanned {completed}/{total}")

    print(f"run_market_scan completed: {completed} of {total}")
    print(f"Results: {len(score_table)} | Skipped: {len(skipped_tickers)}")

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

def get_today_results(top_n=None):
    session = Session()
    today = datetime.datetime.utcnow().date()
    query = session.query(ScanResult).filter(
        ScanResult.scan_date == today,
        ScanResult.filter_passed == True
    ).order_by(ScanResult.score.desc())
    if top_n:
        query = query.limit(top_n)
    results = []
    for row in query:
        df = pd.read_json(StringIO(row.data_json))
        results.append({
            "Ticker": row.ticker,
            "Score": row.score,
            "Rules": row.rules_passed,
            "Data": df
        })
    session.close()
    return results

with tab1:
    st.title("📈 Top Momentum Stocks — S&P 500 + NASDAQ 100")
    start_date = st.text_input("Start Date", value="2024/01/01")
    end_date = st.text_input("End Date", value=pd.Timestamp.today().strftime("%Y/%m/%d"))
    use_standard = st.checkbox("Apply Standard Minervini Rules", value=True)
    use_advanced = st.checkbox("Apply Advanced Rules (Volume, RSI, etc.)", value=True)
    top_n_options = ["10", "20", "30", "All"]
    top_n_choice = st.selectbox("Number of Top Stocks to Show", top_n_options, index=0)
    top_n = None if top_n_choice == "All" else int(top_n_choice)

    run_scan = st.button("Run Full Market Scan")


    if run_scan:
        tickers = get_index_tickers()
        st.session_state.top_results = []
        run_market_scan(
            tickers, start_date, end_date, use_standard, use_advanced,
            max_workers=8, max_retries=3
        )
        st.session_state.top_results = get_today_results(top_n)
        st.success(f"✅ Scan complete! {len(st.session_state.top_results)} stocks shown.")



    if st.session_state.top_results:
        df_results = pd.DataFrame([
            {
                "Symbol": item["Ticker"],
                "Score": item["Score"],
                "Rules Passed": (
                    "Basic & Advanced" if item["Rules"] == "both"
                    else "Advanced" if item["Rules"] == "advanced"
                    else "Basic" if item["Rules"] == "basic"
                    else item["Rules"].capitalize()
                ),
            }
            for item in st.session_state.top_results
        ])

        # --- AgGrid for fully interactive selection ---
        gb = GridOptionsBuilder.from_dataframe(df_results)
        gb.configure_selection('single', use_checkbox=False, pre_selected_rows=[0])
        grid_options = gb.build()

        grid_response = AgGrid(
            df_results,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False,
            height=350,
            width='100%',
            fit_columns_on_grid_load=True,
            theme='streamlit'
        )

        selected_rows = grid_response['selected_rows']
        if isinstance(selected_rows, list) and len(selected_rows) > 0:
            selected_symbol = selected_rows[0]['Symbol']
        else:
            selected_symbol = None

        if selected_symbol:
            selected = next((item for item in st.session_state.top_results if item["Ticker"] == selected_symbol), None)
            if selected:
                label = (
                    "Basic & Advanced"
                    if selected["Rules"] == "both" else
                    ("Advanced" if selected["Rules"] == "advanced" else
                     ("Basic" if selected["Rules"] == "basic" else selected["Rules"].capitalize()))
                )
                st.subheader(f"📊 {selected['Ticker']} (Score: {selected['Score']:.2f}) — {label}")
                fig = plot_price_chart(selected["Data"], selected["Ticker"])
                st.plotly_chart(fig)
                st.markdown(f"**Passed rules:** {label}")
                st.markdown("### 💡 Trade Strategy")
                st.markdown(generate_trade_advice(selected["Data"]))
        else:
            st.info("Click a symbol in the table to view its chart and advice.")

    else:
        st.info("Run the scan to see results.")

    st.markdown(
    """
    <hr>
    <div style='text-align: center; color: #999; margin-top: 18px; font-size: 14px;'>
        Created by <b>Jered Willoughby</b>
    </div>
    """,
    unsafe_allow_html=True
    )

with tab2:
    
    st.header("📖 Strategy & Rules Summary")

    st.markdown("""
    <style>
    .checkmark-green {color: #21ba45;}
    .cross-red {color: #db2828;}
    .star {color: #fbbd08;}
    </style>
    """, unsafe_allow_html=True)

    st.subheader("📌 Mark Minervini – Trend Template Rules")

    st.markdown("""
    - <span class="checkmark-green">✔️</span> **Price > 150DMA > 200DMA**  
    <span style="color:gray">*Why? Strong uptrend. Stocks making new highs often keep going as new buyers rush in.*</span>
    - <span class="checkmark-green">✔️</span> **50DMA > 150DMA**  
    <span style="color:gray">*Shows momentum is accelerating upward, not fading.*</span>
    - <span class="checkmark-green">✔️</span> **Price > 50DMA and 200DMA**  
    <span style="color:gray">*Confirms strength above long and intermediate trend lines.*</span>
    - <span class="checkmark-green">✔️</span> **200DMA trending up last 1 month**  
    <span style="color:gray">*Avoids “fake breakouts” in stocks just recovering from long declines.*</span>
    - <span class="star">⭐</span> **RS line in top 30% preferred**  
    <span style="color:gray">*Leaders outperform the broad market and peers.*</span>
    - <span class="cross-red">✖️</span> **Avoid low-volume, illiquid stocks**  
    <span style="color:gray">*Thinly traded names are easily manipulated and harder to exit.*</span>
    """, unsafe_allow_html=True)

    st.divider()

    st.subheader("📊 Score Breakdown (Example)")

    st.markdown("""
    Here’s how a top-ranked stock might score using these rules:
    """)
    st.markdown("""
    | Rule                                      | Pass/Fail | Points |
    |-------------------------------------------|:---------:|:------:|
    | Price > 50DMA                             | ✅        |   +1   |
    | Price > 150DMA                            | ✅        |   +1   |
    | Price > 200DMA                            | ✅        |   +1   |
    | 50DMA > 150DMA                            | ✅        |   +1   |
    | 150DMA > 200DMA                           | ✅        |   +1   |
    | RSI > 60                                  | ✅        |   +1   |
    | Volume (avg > 1M shares)                  | ✅        |   +1   |
    | 200DMA rising (last 21 days)              | ✅        |   +1   |
    | **Total**                                 |           | **8**  |
    """, unsafe_allow_html=True)

    st.caption("The more green checkmarks, the stronger the technical setup.")

    st.divider()

    st.subheader("🌟 Classic Example: Minervini Winner")

    st.markdown("""
    **Monster Beverage (MNST) 2014–2015**
    - *Breakout from long base, all moving averages stacked bullishly*
    - Volume surge on breakout, price ran +100% in less than a year
    - [View annotated chart (Minervini’s Twitter)](https://twitter.com/markminervini/status/1366406313482674184)
    """)

    st.markdown("""
    **Current Market Leader Example:**
    - *Apple Inc. (AAPL)* – Has often fit all template rules at various stages.
    - [See AAPL on Finviz](https://finviz.com/quote.ashx?t=AAPL)
    """)

    st.divider()

    st.subheader("🤔 Why Do These Rules Work?")

    st.markdown("""
    - **Momentum begets momentum**: Winners attract more buyers.
    - **Strong stocks often get stronger**: High-volume breakouts rarely “fizzle” immediately.
    - **Avoiding laggards protects capital**: Downtrending or sideways stocks rarely deliver leadership returns.
    - **The template rules** are designed to stack the odds so only the strongest, most persistent trends make your shortlist.
    """)

    st.subheader("📈 Minervini’s Performance")
    st.markdown("""
    **Return Rate:** 220% CAGR (1994–2000)  
    **Books:**  
    - *Trade Like a Stock Market Wizard*  
    - *Think & Trade Like a Champion*
    """)
    st.subheader("📚 Other Influences in Advisor")
    st.markdown("""
    - **William O’Neil (CANSLIM)**  
    - **Van Tharp (Position Sizing)**  
    - **Ralph Vince (Optimal f)**  
    - **Edwards & Magee (Charting)**  
    - **ATR-Based Stops**
    """)
    st.success("The strategy module uses a fusion of these methods to provide conservative yet high-upside trade setups.")

    st.markdown(
    """
    <hr>
    <div style='text-align: center; color: #999; margin-top: 18px; font-size: 14px;'>
        Created by <b>Jered Willoughby</b>
    </div>
    """,
    unsafe_allow_html=True
)