"""Turn model outputs into per-stock predictions, explanations, risk and rankings."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import config
import overlays
from features import family_of

LABELS = {
    "tech_ret_5d": "5-day return", "tech_ret_21d": "1-month return", "tech_ret_63d": "3-month return",
    "tech_ret_126d": "6-month return", "tech_ret_1d": "Yesterday's move", "tech_ret_10d": "10-day return",
    "tech_rsi14": "RSI(14)", "tech_rsi2": "RSI(2)", "tech_macd_hist": "MACD histogram", "tech_macd": "MACD",
    "tech_bb_pctb": "Bollinger %B", "tech_bb_width": "Bollinger band width", "tech_bb_squeeze": "Bollinger squeeze",
    "tech_dist_sma20": "Distance from 20-day MA", "tech_dist_sma50": "Distance from 50-day MA",
    "tech_dist_sma200": "Distance from 200-day MA", "tech_dist_sma10": "Distance from 10-day MA",
    "tech_dist_sma100": "Distance from 100-day MA", "tech_golden": "50-day MA above 200-day",
    "tech_stoch_k": "Stochastic %K", "tech_stoch_d": "Stochastic %D", "tech_adx": "ADX trend strength",
    "tech_di_diff": "Directional movement (+DI − −DI)", "tech_vol_z": "Volume vs 50-day average",
    "tech_obv_slope": "On-balance volume trend", "tech_cmf": "Chaikin money flow", "tech_atr_pct": "ATR (% of price)",
    "tech_52w_high_dist": "Distance from 52-week high", "tech_52w_low_dist": "Distance from 52-week low",
    "tech_vol_21d": "1-month volatility", "tech_vol_ratio": "Short vs long volatility",
    "pat_double_top": "Double top", "pat_double_bottom": "Double bottom", "pat_head_shoulders": "Head & shoulders",
    "pat_inv_head_shoulders": "Inverse head & shoulders", "pat_cup_handle": "Cup & handle",
    "pat_bull_flag": "Bull flag", "pat_bear_flag": "Bear flag", "pat_tri_sym": "Symmetrical triangle",
    "pat_tri_asc": "Ascending triangle", "pat_tri_desc": "Descending triangle",
    "pat_res_dist_atr": "Room to resistance (ATRs)", "pat_sup_dist_atr": "Cushion to support (ATRs)",
    "pat_breakout_20": "20-day breakout", "pat_breakdown_20": "20-day breakdown",
    "pat_trend20_slope": "20-day trendline slope", "pat_trend60_slope": "60-day trendline slope",
    "rel_vs_sector_21d": "1-month return vs sector", "rel_vs_mkt_21d": "1-month return vs S&P 500",
    "rel_vs_sector_5d": "5-day return vs sector", "rel_vs_mkt_5d": "5-day return vs S&P 500",
    "rel_sector_ret21": "Sector 1-month return", "rel_sector_ret5": "Sector 5-day return", "rel_beta63": "Beta to S&P 500",
    "mkt_spx_ret21": "S&P 500 1-month return", "mkt_ndx_ret21": "Nasdaq 100 1-month return",
    "mkt_spx_dist200": "S&P 500 vs 200-day MA", "mkt_rut_ret21": "Russell 2000 1-month return",
    "x_vix": "VIX level", "x_vix_chg5": "VIX 5-day change", "x_tnx": "10-yr yield", "x_tnx_chg21": "10-yr yield 1-month change",
    "x_oil_ret21": "Oil 1-month change", "x_dxy_ret21": "Dollar 1-month change", "x_curve_10y_3m": "Yield curve (10y−3m)",
    "macro_cpi_yoy": "CPI inflation (YoY)", "macro_unrate": "Unemployment rate", "macro_fedfunds": "Fed funds rate",
    "macro_umcsent": "Consumer sentiment", "macro_gdp_yoy": "Real GDP growth",
    "earn_days_to": "Days to next earnings", "earn_in_21d": "Earnings within a month",
    "ts_ewma_vol": "Forecast volatility (EWMA)", "ts_drift_63": "3-month drift", "ts_ar1": "Return autocorrelation",
}
PCT_FEATS = ("_ret", "dist_", "rel_", "_vol", "atr_pct", "52w", "slope", "gap", "breadth")


ASSET = {"spx": "S&P 500", "ndx": "Nasdaq 100", "dow": "Dow", "rut": "Russell 2000", "vix": "VIX", "tnx": "10-yr yield",
         "irx": "3-month T-bill yield", "oil": "Oil", "gold": "Gold", "dxy": "Dollar", "hyg": "High-yield bonds"}
SUFFIX = {"ret5": "5-day return", "ret21": "1-month return", "dist200": "vs 200-day MA", "vol21": "1-month volatility",
          "chg5": "5-day change", "chg21": "1-month change", "z": "vs 1-year average (z-score)"}


def label(f: str) -> str:
    if f in LABELS:
        return LABELS[f]
    parts = f.split("_")
    if parts[0] in ("mkt", "x") and len(parts) >= 2 and parts[1] in ASSET:
        suf = "_".join(parts[2:])
        return f"{ASSET[parts[1]]} {SUFFIX.get(suf, suf.replace('_', ' '))}".strip()
    extra = {"macro_unrate_chg3m": "Unemployment 3-month change", "macro_fedfunds_chg6m": "Fed funds 6-month change",
             "mkt_breadth_proxy": "Small caps vs S&P 500 (1 month)", "tech_close_loc": "Close position in day's range",
             "rel_corr63": "Correlation with S&P 500", "rel_sector_dist50": "Sector vs its 50-day MA",
             "rel_vs_sector_63d": "3-month return vs sector", "rel_vs_mkt_63d": "3-month return vs S&P 500",
             "tech_williams_r": "Williams %R", "tech_cci": "Commodity Channel Index", "tech_gap": "Opening gap",
             "tech_body": "Candle body", "tech_up_days_10": "Up days in last 10", "tech_updown_vol": "Up vs down volume",
             "tech_vol_10d": "10-day volatility", "tech_vol_63d": "3-month volatility", "tech_macd_cross_up": "MACD bullish cross",
             "tech_sma50_slope": "50-day MA slope", "pat_sr_touches": "Touches of resistance level",
             "pat_trend20_r2": "20-day trend straightness", "pat_trend60_r2": "60-day trend straightness",
             "earn_days_since": "Days since earnings", "earn_in_5d": "Earnings within a week"}
    return extra.get(f, f.split("_", 1)[-1].replace("_", " ").capitalize())


def fmt_value(f: str, v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    if f.startswith("pat_") and f not in ("pat_res_dist_atr", "pat_sup_dist_atr", "pat_sr_touches") and "slope" not in f and "r2" not in f:
        return "confirmed" if v >= 1 else ("forming" if v > 0 else "none")
    if f in ("tech_rsi14", "tech_rsi2", "tech_stoch_k", "tech_stoch_d", "tech_adx", "x_vix", "macro_umcsent"):
        return f"{v:.0f}"
    if f.startswith(("x_tnx", "x_irx", "x_curve", "macro_")):
        return f"{v:.2f}"
    if f.startswith(("x_vix", "tech_vol_z", "tech_obv", "tech_cmf", "tech_updown", "rel_beta", "rel_corr", "ts_ar1", "ts_drift")) or f.endswith("_r2"):
        return f"{v:.2f}"
    if any(k in f for k in PCT_FEATS) or "dist" in f or "_ret" in f or f.startswith("mkt_") or "vol" in f:
        return f"{v * 100:+.1f}%"
    return f"{v:.2f}"


def _risk(row: pd.Series, h: str, live: dict | None, q: np.ndarray) -> dict:
    vol = float(row.get("tech_vol_63d") or np.nan)
    level = "Low" if vol < 0.25 else "Medium" if vol < 0.45 else "High" if vol < 0.75 else "Very high"
    earn_days = row.get("earn_days_to")
    notes = []
    if earn_days == earn_days and earn_days is not None and earn_days <= 30:
        notes.append(f"Earnings in ~{int(earn_days)} days: expect a larger move than usual.")
    if row.get("tech_rsi14", 50) > 75:
        notes.append("RSI above 75: stretched short term, pullbacks are common from here.")
    if row.get("tech_rsi14", 50) < 25:
        notes.append("RSI below 25: deeply oversold, rebounds are sharp but unreliable.")
    if row.get("x_vix", 0) and row.get("x_vix", 0) > 25:
        notes.append("VIX above 25: market-wide swings are elevated.")
    if live and live.get("options", {}).get("iv_vs_rv") and live["options"]["iv_vs_rv"] > 1.3:
        notes.append("Options imply much more volatility than recent trading: traders expect an event.")
    if (row.get("rel_beta63") or 0) > 1.6:
        notes.append(f"High beta ({row['rel_beta63']:.1f}): moves amplify the market's direction.")
    return {"level": level, "vol_annual": vol, "atr_pct": float(row.get("tech_atr_pct") or np.nan),
            "beta": float(row.get("rel_beta63") or np.nan), "downside_q10": float(q[0]), "notes": notes}


def _confidence(p: float, auc: float, earnings_in_window: bool) -> str:
    strength, skill = abs(p - 0.5), max((auc or 0.5) - 0.5, 0)
    if strength >= 0.12 and skill >= 0.04 and not earnings_in_window:
        return "High"
    if strength >= 0.06 and skill >= 0.02:
        return "Medium"
    return "Low"


def _lean(p: float) -> str:
    return ("Strongly bullish" if p >= 0.65 else "Bullish" if p >= 0.56 else "Slightly bullish" if p > 0.52 else
            "Neutral" if p >= 0.48 else "Slightly bearish" if p >= 0.44 else "Bearish" if p > 0.35 else "Strongly bearish")


def skill_factor(auc) -> float:
    """How much to trust the model's deviation from the base rate, from its out-of-sample AUC.
    AUC 0.50 (no skill) keeps 15% of the deviation; AUC 0.60+ keeps all of it."""
    if auc is None or auc != auc:
        return 0.3
    return float(np.clip((auc - 0.5) / 0.10, 0.15, 1.0))


def build_predictions(panel, feats, models, backtest, live, extras, prices) -> list[dict]:
    latest = panel.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    out = []
    for t, row in latest.iterrows():
        X = row[feats].to_frame().T.astype(float)
        rec = {"ticker": t, "date": str(pd.Timestamp(row["date"]).date()), "price": float(row["close"]),
               "horizons": {}, "live": (live or {}).get(t)}
        contrib_all = {}
        for h in config.HORIZONS:
            m = models[h]
            bt = backtest.get(h, {}).get("metrics", {})
            base = bt.get("base_rate", float(panel[f"y_up_{h}"].mean()))
            k_dir = skill_factor(bt.get("auc"))
            p_raw = float(m["dir"].predict_proba(X)[0])
            p_model = base + (p_raw - base) * k_dir            # shrink toward the base rate by proven skill
            p_final, shifts = overlays.adjust_probability(p_model, h, rec["live"])
            q = m["q"].predict(X)[0]
            med_hist = float(panel[f"y_ret_{h}"].median())
            q_mid = med_hist + (q[1] - med_hist) * k_dir
            sc = bt.get("range_scale", 1.0)
            q = np.array([q_mid - (q[1] - q[0]) * sc, q_mid, q_mid + (q[2] - q[1]) * sc])
            earn_in = bool(row.get("earn_days_to", 999) <= config.HORIZONS[h] * 1.45)
            if earn_in:  # widen the range for an earnings event
                q = np.array([q[1] - (q[1] - q[0]) * 1.3, q[1], q[1] + (q[2] - q[1]) * 1.3])
            auc = backtest.get(h, {}).get("metrics", {}).get("auc", 0.5)
            gains = {}
            for k, tm in m["thr"].items():
                key = str(int(k * 100)); tb = bt.get("thresholds", {}).get(key, {})
                b0 = tb.get("base_rate", float(panel[f"y_gain{key}_{h}"].mean()))
                gains[key] = float(np.clip(b0 + (float(tm.predict_proba(X)[0]) - b0) * skill_factor(tb.get("auc")), 0, 1))
            sigma = max((q[2] - q[0]) / 2.563, 1e-4)
            contrib = m["dir"].contributions(X).iloc[0]
            contrib_all[h] = contrib
            rec["horizons"][h] = {
                "p_up": p_final, "p_down": 1 - p_final, "p_model": p_model, "p_raw": p_raw, "skill_factor": k_dir, "overlay_shifts": shifts,
                "exp_move": float(q[1]), "range": [float(q[0]), float(q[2])],
                "confidence": _confidence(p_final, auc, earn_in), "lean": _lean(p_final),
                "p_gain": gains, "risk_adj": float(q[1] / sigma), "earnings_in_window": earn_in,
            }
        # explanations from the 1-week model (short) and the 1-month model (medium)
        c = (contrib_all["1w"] + contrib_all["1m"]) / 2
        fam = c.groupby([family_of(k) for k in c.index]).sum().sort_values()
        top_pos = c.sort_values(ascending=False).head(6); top_neg = c.sort_values().head(6)
        bull = [f"{label(k)}: {fmt_value(k, row[k])}" for k, v in top_pos.items() if v > 0.01]
        bear = [f"{label(k)}: {fmt_value(k, row[k])}" for k, v in top_neg.items() if v < -0.01]
        lv = rec["live"] or {}
        if lv:
            n = lv.get("news", {}); a = lv.get("analyst", {}); o = lv.get("options", {}); ins = lv.get("institutional", {})
            if n.get("score", 0) > 0.15: bull.append(f"News sentiment positive ({n['score']:+.2f}, {n.get('n', 0)} articles)")
            if n.get("score", 0) < -0.15: bear.append(f"News sentiment negative ({n['score']:+.2f}, {n.get('n', 0)} articles)")
            if (a.get("target_upside") or 0) > 0.15: bull.append(f"Analyst target {a['target_upside'] * 100:+.0f}% above price")
            if (a.get("target_upside") or 0) < 0: bear.append(f"Price above analyst target ({a['target_upside'] * 100:+.0f}%)")
            if a.get("net_upgrades_30d", 0) > 0: bull.append(f"{a['net_upgrades_30d']} net analyst upgrade(s) in 30 days")
            if a.get("net_upgrades_30d", 0) < 0: bear.append(f"{-a['net_upgrades_30d']} net analyst downgrade(s) in 30 days")
            if (o.get("put_call_vol") or 1) < 0.55: bull.append(f"Call-heavy options flow (put/call {o['put_call_vol']:.2f})")
            if (o.get("put_call_vol") or 0) > 1.1: bear.append(f"Put-heavy options flow (put/call {o['put_call_vol']:.2f})")
            if (ins.get("insider_net_6m") or 0) > 1e6: bull.append("Net insider buying over 6 months")
            if (ins.get("insider_net_6m") or 0) < -5e6: bear.append("Heavy net insider selling over 6 months")
        rec["bullish"] = bull[:7]; rec["bearish"] = bear[:7]
        rec["family_contrib"] = [{"family": k, "value": float(v)} for k, v in fam.items()]
        rec["top_drivers"] = [{"feature": label(k), "value": fmt_value(k, row[k]), "impact": float(v)}
                              for k, v in c.reindex(c.abs().sort_values(ascending=False).index).head(8).items()]
        hs = rec["horizons"]
        rec["risk"] = _risk(row, "1w", lv, np.array([hs["1w"]["range"][0], hs["1w"]["exp_move"], hs["1w"]["range"][1]]))
        top_fams = ", ".join(k.lower() for k in fam.abs().sort_values(ascending=False).head(2).index)
        rec["short_outlook"] = (f"{hs['1w']['lean']} over the next 1–5 days: {hs['1w']['p_up'] * 100:.0f}% chance of a higher close in a week "
                                f"(tomorrow {hs['1d']['p_up'] * 100:.0f}%), typical range {hs['1w']['range'][0] * 100:+.1f}% to {hs['1w']['range'][1] * 100:+.1f}%. "
                                f"Mostly driven by {top_fams}.")
        rec["medium_outlook"] = (f"{hs['1m']['lean']} over 1–4 weeks: {hs['1m']['p_up'] * 100:.0f}% chance of being higher in a month, "
                                 f"median move {hs['1m']['exp_move'] * 100:+.1f}% (range {hs['1m']['range'][0] * 100:+.1f}% to {hs['1m']['range'][1] * 100:+.1f}%). "
                                 f"Chance of a +10% run within the month: {hs['1m']['p_gain']['10'] * 100:.0f}%.")
        rec["explanation"] = _explain(rec, fam)
        # chart data: last 180 closes + moving averages + S/R
        px = prices[t]["close"].iloc[-260:]
        rec["chart"] = {"dates": [str(d.date()) for d in px.index[-180:]], "close": [round(float(v), 4) for v in px.iloc[-180:]],
                        "sma20": [None if np.isnan(v) else round(float(v), 4) for v in px.rolling(20).mean().iloc[-180:]],
                        "sma50": [None if np.isnan(v) else round(float(v), 4) for v in px.rolling(50).mean().iloc[-180:]],
                        **extras.get(t, {}).get("sr", {})}
        out.append(rec)
    return out


def _explain(rec, fam) -> str:
    parts = []
    pos = [k for k, v in fam.items() if v > 0.02][::-1][:2]
    neg = [k for k, v in fam.items() if v < -0.02][:2]
    if pos: parts.append("pushing up: " + " and ".join(p.lower() for p in pos))
    if neg: parts.append("pushing down: " + " and ".join(n.lower() for n in neg))
    sh = rec["horizons"]["1w"]["overlay_shifts"]
    if sh:
        big = max(sh, key=lambda k: abs(sh[k]))
        if abs(sh[big]) > 0.01:
            parts.append(f"largest live adjustment from {big.replace('_', ' ')} ({'+' if sh[big] > 0 else '−'}{abs(sh[big]):.2f} log-odds)")
    return ("Factor groups " + "; ".join(parts) + ".") if parts else "No factor group stands out; the model sees this close to a coin flip."


def rankings(preds: list[dict]) -> dict:
    """Stocks most likely to gain >5/10/20% per horizon, ranked by probability and by risk-adjusted return."""
    r = {}
    for h in config.HORIZONS:
        r[h] = {}
        for thr in config.GAIN_THRESHOLDS:
            k = str(int(thr * 100))
            rows = [{"ticker": p["ticker"], "p_gain": p["horizons"][h]["p_gain"][k], "exp_move": p["horizons"][h]["exp_move"],
                     "risk_adj": p["horizons"][h]["risk_adj"], "p_up": p["horizons"][h]["p_up"]} for p in preds]
            rows.sort(key=lambda x: x["p_gain"], reverse=True)
            r[h][k] = rows[:10]
        ra = [{"ticker": p["ticker"], "risk_adj": p["horizons"][h]["risk_adj"], "exp_move": p["horizons"][h]["exp_move"],
               "p_up": p["horizons"][h]["p_up"], "range": p["horizons"][h]["range"]} for p in preds]
        r[h]["risk_adjusted"] = sorted(ra, key=lambda x: x["risk_adj"], reverse=True)
    return r
