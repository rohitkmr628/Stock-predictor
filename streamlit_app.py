"""Streamlit wrapper: shows the latest scheduled run (site/results.json) and can trigger a fast daily run.

    streamlit run streamlit_app.py
"""
import json
import os

import streamlit as st
import streamlit.components.v1 as components

import dashboard

st.set_page_config(page_title="Odds Board", layout="wide")

with st.sidebar:
    st.header("Odds Board")
    st.caption("Illustrative research, not investment advice.")
    go = st.button("Run a fresh daily update (≈10–20 min)")
    st.markdown("The weekly full rebuild (universe screen + backtest) runs on GitHub Actions; this app reuses its saved state.")

results = None
if go:
    from run import run
    with st.spinner("Downloading data, retraining and forecasting…"):
        try:
            results = run("daily", demo=False, live_signals=True, out_dir="site", log=lambda *_: None)
        except Exception as e:
            st.error(f"The run failed: {e}")
if results is None and os.path.exists("site/results.json"):
    results = json.load(open("site/results.json"))

if results:
    html = dashboard.TEMPLATE.replace("__DATA__", json.dumps(results).replace("</", "<\\/"))
    components.html(html, height=3000, scrolling=True)
else:
    st.info("No results yet. Run the GitHub workflow once (mode: full), or press the button in the sidebar.")
