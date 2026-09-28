"""Run the full pipeline and write the dashboard.

    python run.py                 # real data (needs internet + yfinance)
    python run.py --demo          # synthetic data, no internet needed
    python run.py --tickers NVDA AMD MU --no-backtest
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import config
import data
import dashboard
import features
import model
import report


def run_pipeline(tickers=None, demo=False, backtest=True, live_signals=True, log=print) -> dict:
    """Run everything and return the results dict (used by run.py and streamlit_app.py)."""
    t0 = time.time()
    tickers = list(tickers or config.WATCHLIST)
    log("1/6 Loading data…")
    if demo:
        tickers = tickers if tickers != config.WATCHLIST else [f"SAMPLE{i:02d}" for i in range(1, 13)]
        for i, t in enumerate(tickers):   # give demo tickers a sector
            config.SECTOR_MAP.setdefault(t, ["SMH", "IGV", "XLC", "UFO"][i % 4])
        prices, macro, earnings = data.synthetic_universe(tickers)
    else:
        syms = set(tickers) | set(config.MARKET.values()) | set(config.MACRO_MARKET.values())
        syms |= {config.SECTOR_MAP.get(t, config.DEFAULT_SECTOR) for t in tickers}
        prices = data.load_prices(sorted(syms))
        macro = data.load_fred()
        earnings = {t: data.load_earnings_dates(t) for t in tickers}
        tickers = [t for t in tickers if t in prices]
        if not tickers:
            raise RuntimeError("No price data downloaded; check the tickers and your internet connection.")

    log("2/6 Building features and chart patterns…")
    panel, extras = features.build_panel(prices, macro, earnings, tickers)
    feats = [f for f in features.feature_columns(panel) if panel[f].notna().mean() > 0.5]
    log(f"  {len(panel):,} rows × {len(feats)} features")

    bt = {}
    if backtest:
        log("3/6 Walk-forward backtest (the slow part)…")
        bt = model.walk_forward(panel, feats)
    else:
        log("3/6 Backtest skipped")

    log("4/6 Training final models…")
    models = model.fit_all(panel, feats)
    importance = {}
    for h in config.HORIZONS:
        d = panel[panel[f"y_up_{h}"].notna()]
        importance[h] = model.feature_importance(models[h]["dir"], d[feats], d[f"y_up_{h}"])
        for f in importance[h]["features"]:
            f["label"] = report.label(f["feature"])

    log("5/6 Live signals (news, analysts, options, institutions)…")
    latest = panel.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    if not live_signals:
        live = {}
    elif demo:
        live = data.synthetic_live(tickers)
    else:
        import overlays
        live = overlays.collect_live(tickers, latest["close"].to_dict(), latest["tech_vol_21d"].to_dict())

    log("6/6 Building predictions…")
    preds = report.build_predictions(panel, feats, models, bt, live, extras, prices)
    results = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "data_date": str(pd.Timestamp(panel["date"].max()).date()),
        "demo": bool(demo), "horizons": config.HORIZONS,
        "thresholds": [int(x * 100) for x in config.GAIN_THRESHOLDS],
        "n_features": len(feats), "n_rows": int(len(panel)),
        "predictions": preds, "rankings": report.rankings(preds),
        "backtest": {h: v["metrics"] for h, v in bt.items()},
        "importance": importance, "market": _market_snapshot(prices),
    }
    log(f"Finished in {time.time() - t0:.0f}s")
    return json.loads(json.dumps(results, default=_json_default))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use synthetic data (no internet)")
    ap.add_argument("--tickers", nargs="*", help="override the watchlist")
    ap.add_argument("--no-backtest", action="store_true", help="skip the walk-forward backtest (faster)")
    ap.add_argument("--no-live", action="store_true", help="skip news/options/analyst overlays")
    ap.add_argument("--out", default="site", help="output folder for index.html and results.json")
    args = ap.parse_args()
    results = run_pipeline(args.tickers, args.demo, not args.no_backtest, not args.no_live)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump(results, fh)
    dashboard.write(results, os.path.join(args.out, "index.html"))
    print(f"Dashboard → {os.path.join(args.out, 'index.html')}")


def _market_snapshot(prices):
    snap = []
    names = {"SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq 100 (QQQ)", "DIA": "Dow (DIA)", "IWM": "Russell 2000 (IWM)",
             "^VIX": "VIX", "^TNX": "10-yr yield", "CL=F": "Oil (WTI)", "GC=F": "Gold", "DX-Y.NYB": "Dollar index"}
    for s, n in names.items():
        if s in prices and len(prices[s]) > 22:
            c = prices[s]["close"]
            snap.append({"name": n, "last": float(c.iloc[-1]), "chg1d": float(c.iloc[-1] / c.iloc[-2] - 1),
                         "chg1m": float(c.iloc[-1] / c.iloc[-22] - 1)})
    return snap


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return str(o)


if __name__ == "__main__":
    main()
