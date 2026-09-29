"""Odds Board v2 — run the pipeline and write the dashboard.

    python run.py --mode full      # weekly: universe screen + fundamentals + multi-cycle backtest + forecasts
    python run.py --mode daily     # twice daily: reuse the saved backtest state, retrain, forecast (fast)
    python run.py --demo           # synthetic data end-to-end, no internet
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import config
import dashboard
import data
import features
import model
import report
import universe


def _json_default(o):
    if isinstance(o, (np.floating, float)):
        return None if o != o or o in (float("inf"), float("-inf")) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return str(o)


def _clean(obj):
    """Replace NaN/inf with None everywhere so the JSON is valid."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return None if (obj != obj or obj in (float("inf"), float("-inf"))) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def market_snapshot(prices):
    names = {"SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq 100 (QQQ)", "DIA": "Dow (DIA)", "IWM": "Russell 2000 (IWM)",
             "^VIX": "VIX", "^TNX": "10-yr yield", "CL=F": "Oil (WTI)", "GC=F": "Gold", "DX-Y.NYB": "Dollar index"}
    out = []
    for s, n in names.items():
        if s in prices and len(prices[s]) > 22:
            c = prices[s]["close"]
            out.append({"name": n, "last": float(c.iloc[-1]), "chg1d": float(c.iloc[-1] / c.iloc[-2] - 1), "chg1m": float(c.iloc[-1] / c.iloc[-22] - 1)})
    return out


def run(mode="daily", demo=False, live_signals=True, out_dir="site", log=print) -> dict:
    t0 = time.time()
    if demo:
        config.STATE_DIR = os.path.join(out_dir, "_demo_state")
    state = None if mode == "full" else model.load_state()
    if state is None and mode == "daily":
        log("No saved backtest state found → running the full pipeline once.")
        mode = "full"

    # ------------------------------------------------------------------ 1. universe + fundamentals
    log("1/7 Universe and fundamentals…")
    if demo:
        prices, macro, earnings, fund = data.synthetic_universe()
        tickers = [t for t in fund]
        membership = {t: (["S&P 500"] if i % 3 else ["Nasdaq-100", "S&P 500"]) + (["Watchlist"] if i < 5 else []) for i, t in enumerate(tickers)}
        screen_info = {"candidates": len(tickers), "passed": len(tickers), "universe": len(tickers)}
    else:
        if mode == "full":
            cands, membership = universe.candidate_list()
            fund = universe.fetch_fundamentals(sorted(set(cands) | set(config.WATCHLIST)))
            q0 = universe.quality_scores(fund)
            tickers, q0 = universe.screen(q0, membership)
            screen_info = {"candidates": len(cands), "passed": int(q0["passes_screen"].sum()), "universe": len(tickers)}
            fund = {t: fund.get(t, {}) for t in tickers}
            universe.save_fundamentals({"tickers": tickers, "membership": {t: membership.get(t, []) for t in tickers},
                                        "fund": fund, "screen": screen_info})
        else:
            cache = universe.load_cached_fundamentals()
            tickers, membership, fund, screen_info = cache["tickers"], cache["membership"], cache["fund"], cache.get("screen", {})
        log("2/7 Prices, earnings history and macro data…")
        etfs = set(config.MARKET.values()) | set(config.MACRO_MARKET.values()) | set(config.SECTOR_ETF.values()) | set(config.INDUSTRY_ETF_OVERRIDE.values())
        prices = data.load_prices(sorted(set(tickers) | etfs))
        tickers = [t for t in tickers if t in prices]
        earnings = data.load_earnings_history(tickers)
        macro = data.load_fred()

    risk_stats = universe.risk_stats_from_prices({t: prices[t] for t in tickers})
    quality = universe.quality_scores(fund, risk_stats)

    # ------------------------------------------------------------------ 2. features
    log("3/7 Features: technicals, patterns, regime, breadth, sector rotation, earnings…")
    panel, extras, mkt = features.build_panel(prices, macro, earnings, fund, tickers)
    feats = [f for f in features.feature_columns(panel) if panel[f].notna().mean() > 0.5]
    log(f"  {len(panel):,} rows × {len(feats)} features · {panel['ticker'].nunique()} stocks")

    # ------------------------------------------------------------------ 3. backtest (full mode)
    if mode == "full":
        log("4/7 Walk-forward backtest across market cycles (slow part)…")
        bt = model.walk_forward(panel, feats, log=log)
        state = model.build_state(bt, panel, feats, log=log)
        log("  feature importance…")
        state["importance"] = model.feature_importance(panel, feats, config.PRIMARY_HORIZON)
        for fi in state["importance"]["features"]:
            fi["label"] = report.label(fi["feature"])
        model.save_state(state)
    else:
        log("4/7 Using saved backtest from " + state.get("generated", "?"))

    # ------------------------------------------------------------------ 4. final models
    log("5/7 Training final ensemble on all history…")
    live_model = model.LiveModel(panel, feats, state, log=log)

    # ------------------------------------------------------------------ 5. live overlays for the top names
    log("6/7 Live signals (news, analysts, options, insiders)…")
    latest = panel.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    if not live_signals:
        live = {}
    elif demo:
        live = data.synthetic_live(tickers[:config.LIVE_SIGNAL_LIMIT])
    else:
        import overlays
        pre = live_model.predict(config.PRIMARY_HORIZON, latest[feats].astype(float))["p"]
        order = latest.index[np.argsort(-np.abs(pre - state["horizons"][config.PRIMARY_HORIZON]["base_rate"]))]
        pick = list(dict.fromkeys([t for t in config.WATCHLIST if t in latest.index] + list(order)))[:config.LIVE_SIGNAL_LIMIT + len(config.WATCHLIST)]
        live = overlays.collect_live(pick, latest["close"].to_dict(), latest["tech_vol_21d"].to_dict())

    # ------------------------------------------------------------------ 6. outputs
    log("7/7 Forecasts, rankings, dashboard…")
    recs = report.build(panel, feats, live_model, state, quality, risk_stats, live, extras, prices, membership, log=log)
    report.attach_momentum(recs, panel)
    ranks = report.rankings(recs)
    for r in recs:
        r.pop("_mom", None)
    now = mkt.iloc[-1]
    regime_now = {"regime": "Bull" if now.get("regime_bull") == 1 else "Bear" if now.get("regime_bear") == 1 else "Sideways",
                  "high_vol": bool(now.get("regime_highvol") == 1), "spx_drawdown": now.get("regime_spx_dd"),
                  "breadth_above200": now.get("breadth_above200"), "vix": now.get("x_vix"), "ten_year": now.get("x_tnx")}
    results = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "mode": mode, "demo": demo,
        "data_date": str(pd.Timestamp(panel["date"].max()).date()), "backtest_generated": state.get("generated"),
        "horizons": config.HORIZONS, "primary": config.PRIMARY_HORIZON, "n_features": len(feats), "universe": screen_info,
        "regime_now": regime_now, "market": market_snapshot(prices),
        "predictions": recs, "rankings": ranks,
        "backtest": {h: {k: v for k, v in hs.items() if k not in ("iso_x", "iso_y", "setup_table")} for h, hs in state["horizons"].items()},
        "importance": state.get("importance", {}),
        "rules": {"confidence": config.CONFIDENCE, "position": config.POSITION, "band": config.BAND_COVERAGE,
                  "overlays": config.OVERLAY_WEIGHTS},
    }
    results = _clean(json.loads(json.dumps(results, default=_json_default)))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w") as fh:
        json.dump(results, fh)
    dashboard.write(results, os.path.join(out_dir, "index.html"))
    log(f"Done in {time.time() - t0:.0f}s → {os.path.join(out_dir, 'index.html')}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "daily"], default="daily")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--no-live", action="store_true")
    ap.add_argument("--out", default="site")
    a = ap.parse_args()
    run("full" if a.demo else a.mode, a.demo, not a.no_live, a.out)
