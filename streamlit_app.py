"""Interactive web app: pick tickers, run the model, see the dashboard.

Deploy free on Streamlit Community Cloud (see README), or run locally:
    streamlit run streamlit_app.py
"""
import json
import os

import streamlit as st
import streamlit.components.v1 as components

import config
import dashboard
from run import run_pipeline

st.set_page_config(page_title="Odds Board", layout="wide")
st.title("Odds Board")
st.caption("Probabilities from a backtested model, not financial advice.")

with st.sidebar:
    st.header("Run the model")
    tickers = st.text_area("Tickers (Yahoo symbols, space or comma separated)",
                           " ".join(config.WATCHLIST), height=140)
    backtest = st.checkbox("Include walk-forward backtest (adds ~5–15 min)", value=False)
    live = st.checkbox("Include news, analyst, options and insider signals", value=True)
    go = st.button("Run", type="primary")
    st.markdown("If a nightly run from GitHub Actions exists in `site/results.json`, it is shown until you run a new one.")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_run(tick_tuple, backtest, live):
    return run_pipeline(list(tick_tuple), demo=False, backtest=backtest, live_signals=live, log=lambda *_: None)


results = None
if go:
    tick = tuple(t.strip().upper() for t in tickers.replace(",", " ").split() if t.strip())
    with st.spinner(f"Downloading data and training on {len(tick)} tickers…"):
        try:
            results = cached_run(tick, backtest, live)
        except Exception as e:
            st.error(f"The run failed: {e}")
elif os.path.exists("site/results.json"):
    results = json.load(open("site/results.json"))
    st.info(f"Showing the scheduled run from {results['generated']}. Use the sidebar to run a fresh one.")

if results:
    html = dashboard.TEMPLATE.replace("__DATA__", json.dumps(results).replace("</", "<\\/"))
    components.html(html, height=2600, scrolling=True)
    st.download_button("Download results.json", json.dumps(results), "results.json", "application/json")
else:
    st.write("Pick tickers in the sidebar and press **Run**. The first run takes a few minutes.")
