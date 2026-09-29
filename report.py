"""Per-stock forecasts with confidence gating, risk rating, illustrative sizing, and the ranking engine."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm

import config
import overlays
from features import family_of
from labels import fmt_value, label
from model import confidence, horizon_sigma, lookup_setup, move_from_prob, prob_max_above, rank_bucket

Z = norm.ppf(0.5 + config.BAND_COVERAGE / 2)
HZ_NAME = {"1d": "1 day", "1w": "1 week", "1m": "1 month", "3m": "3 months"}


def trend_of(row) -> str:
    d50, d200 = row.get("tech_dist_sma50"), row.get("tech_dist_sma200")
    r63, golden = row.get("tech_ret_63d"), row.get("tech_golden")
    if any(v is None or v != v for v in (d50, d200, r63)):
        return "Unclear"
    if d200 > 0 and golden == 1 and d50 > 0 and r63 > 0.10:
        return "Strong uptrend"
    if d200 > 0 and golden == 1:
        return "Uptrend"
    if d200 < 0 and golden == 0 and d50 < 0 and r63 < -0.10:
        return "Strong downtrend"
    if d200 < 0 and golden == 0:
        return "Downtrend"
    return "Sideways"


def exp_gain_loss(mu, s):
    s = max(s, 1e-6); z = mu / s
    gain = mu * norm.cdf(z) + s * norm.pdf(z)
    loss = -mu * norm.cdf(-z) + s * norm.pdf(z)
    return gain, loss


def _pct_rank(s: pd.Series, higher=True):
    r = s.rank(pct=True)
    return (r if higher else 1 - r).fillna(0.5)


def build(panel, feats, live_model, state, quality, risk_stats, live, extras, prices, membership, log=print) -> list[dict]:
    latest = panel.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    X = latest[feats].astype(float)
    preds = {h: live_model.predict(h, X) for h in config.HORIZONS}
    ranks = {h: pd.Series(preds[h]["p"]).rank(pct=True, method="average").to_numpy() for h in config.HORIZONS}
    lin = live_model.models["1m"].get("all_linear")
    contrib = None
    if lin is not None:
        imp, sc, lr = lin.named_steps.values()
        cols = live_model.comp_cols["all_linear"]
        contrib = pd.DataFrame(sc.transform(imp.transform(X[cols])) * lr.coef_[0], index=X.index, columns=cols)

    recs = []
    for i, t in enumerate(latest.index):
        row = latest.loc[t]
        f = quality.loc[t] if t in quality.index else pd.Series(dtype=object)
        lv = (live or {}).get(t)
        _s = lambda v: v if isinstance(v, str) and v.strip() else None
        rec = {"ticker": t, "name": (_s(f.get("longName")) or _s(f.get("shortName")) or t) if len(f) else t,
               "sector": _s(f.get("sector")) if len(f) else None, "groups": membership.get(t, []),
               "price": float(row["close"]), "date": str(pd.Timestamp(row["date"]).date()),
               "trend": trend_of(row), "regime": row.get("regime"), "horizons": {}}
        for h, hlen in config.HORIZONS.items():
            hs = state["horizons"][h]
            base = hs["base_rate"]
            gscale = {g["threshold"]: g.get("scale", 1.0) for g in hs.get("gain_calibration", [])}
            p_model = float(preds[h]["p"][i])
            p, shifts = overlays.adjust_probability(p_model, h, lv) if lv else (p_model, {})
            edge = p - base
            sigma = float(horizon_sigma(latest.loc[[t]], hlen)[0]); c = hs["band_c"]
            earn_in = bool((row.get("earn_days_to") or 999) <= hlen * 1.45)
            widen = 1.25 if earn_in else 1.0
            mu = float(move_from_prob(p, sigma, c)); s = c * sigma * widen
            bucket = rank_bucket(float(ranks[h][i]))
            setup = lookup_setup(hs["setup_table"], row.get("regime"), bucket)
            conf = confidence(edge, bucket, setup) if sum(hs["weights"].values()) > 0 else "Low"
            if earn_in and conf == "High":
                conf = "Medium"
            g, l = exp_gain_loss(mu, s)
            comp = preds[h]["components"].iloc[i]
            rec["horizons"][h] = {
                "p_up": p, "p_down": 1 - p, "p_model": p_model, "base_rate": base, "edge": edge, "overlay": shifts,
                "exp_move": mu, "band": [mu - Z * s, mu + Z * s], "confidence": conf,
                "published": conf in ("High", "Medium"), "earnings_in_window": earn_in,
                "rr": float(g / l) if l > 0 else None, "risk_adj": mu / s if s > 0 else 0.0,
                "p_gain": {str(k): float(min(1.0, prob_max_above(mu, s, k / 100) * gscale.get(k, 1.0))) for k in (5, 10, 20)},
                "setup": setup, "bucket": bucket, "rank": float(ranks[h][i]),
                "evidence": [{"component": k, "p": float(comp[k]), "weight": float(hs["weights"].get(k, 0))} for k in comp.index],
            }
        # explanations (linear contributions on the 1-month model)
        if contrib is not None:
            cc = contrib.loc[t]
            fam = cc.groupby([family_of(k) for k in cc.index]).sum().sort_values()
            pos = cc.sort_values(ascending=False).head(6); neg = cc.sort_values().head(6)
            bull = [f"{label(k)}: {fmt_value(k, row[k])}" for k, v in pos.items() if v > 0.02]
            bear = [f"{label(k)}: {fmt_value(k, row[k])}" for k, v in neg.items() if v < -0.02]
            rec["family_contrib"] = [{"family": k, "value": float(v)} for k, v in fam.items()]
            rec["top_drivers"] = [{"feature": label(k), "value": fmt_value(k, row[k]), "impact": float(v)}
                                  for k, v in cc.reindex(cc.abs().sort_values(ascending=False).index).head(8).items()]
        else:
            bull, bear, rec["family_contrib"], rec["top_drivers"] = [], [], [], []
        # fundamentals as factors
        if len(f):
            if (f.get("revenueGrowth") or 0) > 0.15: bull.append(f"Revenue growth {f['revenueGrowth'] * 100:.0f}% YoY")
            if (f.get("revenueGrowth") or 0) < 0: bear.append(f"Revenue shrinking ({f['revenueGrowth'] * 100:.0f}% YoY)")
            if (f.get("fcf_margin") or 0) > 0.2: bull.append(f"Free-cash-flow margin {f['fcf_margin'] * 100:.0f}%")
            if (f.get("returnOnEquity") or 0) > 0.25: bull.append(f"Return on equity {f['returnOnEquity'] * 100:.0f}%")
            if f.get("sector") != "Financial Services" and (f.get("debtToEquity") or 0) > 200: bear.append(f"High leverage (debt/equity {f['debtToEquity'] / 100:.1f}x)")
            if (f.get("forwardPE") or 0) > 45: bear.append(f"Rich valuation (forward P/E {f['forwardPE']:.0f})")
        if row.get("fund_last_surprise") == row.get("fund_last_surprise") and row.get("fund_last_surprise") is not None:
            (bull if row["fund_last_surprise"] > 3 else bear if row["fund_last_surprise"] < -3 else []).append(f"Last EPS surprise {row['fund_last_surprise']:+.1f}%")
        if lv:
            n, a, o, ins = lv.get("news", {}), lv.get("analyst", {}), lv.get("options", {}), lv.get("institutional", {})
            if n.get("score", 0) > 0.15: bull.append(f"Positive news sentiment ({n['score']:+.2f})")
            if n.get("score", 0) < -0.15: bear.append(f"Negative news sentiment ({n['score']:+.2f})")
            if a.get("net_upgrades_30d", 0) > 0: bull.append(f"{a['net_upgrades_30d']} net analyst upgrade(s) in 30 days")
            if a.get("net_upgrades_30d", 0) < 0: bear.append(f"{-a['net_upgrades_30d']} net analyst downgrade(s) in 30 days")
            if (a.get("target_upside") or 0) > 0.15: bull.append(f"Analyst target {a['target_upside'] * 100:+.0f}% vs price")
            if (o.get("put_call_vol") or 1) < 0.55: bull.append(f"Call-heavy options flow (P/C {o['put_call_vol']:.2f})")
            if (o.get("put_call_vol") or 0) > 1.1: bear.append(f"Put-heavy options flow (P/C {o['put_call_vol']:.2f})")
            if (ins.get("insider_net_6m") or 0) < -1e7: bear.append("Heavy insider selling (6 months)")
        rec["bullish"], rec["bearish"] = bull[:8], bear[:8]
        rec["live"] = lv
        rec["fundamentals"] = {k: (None if (v is None or (isinstance(v, float) and v != v)) else v) for k, v in f.items()
                               if k in ("marketCap", "revenueGrowth", "earningsGrowth", "returnOnEquity", "operatingMargins",
                                        "profitMargins", "fcf_margin", "debtToEquity", "currentRatio", "forwardPE", "pegRatio",
                                        "dividendYield", "industry", "country", "passes_screen",
                                        "growth", "profitability", "cash_flow", "balance_sheet", "stability", "valuation", "quality")}
        rs = risk_stats.loc[t] if t in risk_stats.index else None
        rec["risk_stats"] = {"vol_1y": float(rs["vol_1y"]) if rs is not None else None,
                             "max_dd_3y": float(rs["max_dd_3y"]) if rs is not None else None,
                             "cagr_5y": float(rs["cagr_5y"]) if rs is not None else None,
                             "beta": float(row.get("rel_beta63")) if row.get("rel_beta63") == row.get("rel_beta63") else None}
        px = prices[t]["close"].iloc[-400:]
        sl = slice(-180, None)
        rnd = lambda s: [None if v != v else round(float(v), 4) for v in s]
        rec["chart"] = {"dates": [str(d.date()) for d in px.index[sl]], "close": rnd(px.iloc[sl]),
                        "sma50": rnd(px.rolling(50).mean().iloc[sl]), "sma200": rnd(px.rolling(200).mean().iloc[sl]),
                        **extras.get(t, {}).get("sr", {})}
        rec["_row"] = row
        recs.append(rec)
    _risk_and_size(recs)
    _outlook_text(recs)
    for r in recs:
        r.pop("_row", None)
    return recs


def _risk_and_size(recs):
    df = pd.DataFrame({"t": [r["ticker"] for r in recs],
                       "vol": [r["risk_stats"]["vol_1y"] for r in recs],
                       "dd": [r["risk_stats"]["max_dd_3y"] for r in recs],
                       "beta": [r["_row"].get("rel_downside_beta") for r in recs],
                       "low": [r["horizons"][config.PRIMARY_HORIZON]["band"][0] for r in recs],
                       "de": [(r["fundamentals"].get("debtToEquity") if r["sector"] != "Financial Services" else None) for r in recs]}).set_index("t")
    df = df.apply(pd.to_numeric, errors="coerce")
    score = (_pct_rank(df["vol"]) * .35 + _pct_rank(df["dd"], higher=False) * .25 + _pct_rank(df["beta"]) * .15
             + _pct_rank(df["low"], higher=False) * .15 + _pct_rank(df["de"]) * .10)
    P = config.POSITION
    for r in recs:
        r["risk_rating"] = int(min(10, max(1, math.ceil(score[r["ticker"]] * 10))))
        hp = r["horizons"][config.PRIMARY_HORIZON]
        if hp["published"] and hp["edge"] > 0:
            downside = max(abs(min(hp["band"][0], 0)), 0.02)
            w = min(P["max_weight"], P["risk_per_idea"] / downside) * P["conf_mult"][hp["confidence"]]
            r["position"] = {"weight": float(w), "basis": f"{P['risk_per_idea'] * 100:.1f}% portfolio risk ÷ {downside * 100:.1f}% band downside × {hp['confidence'].lower()}-confidence factor"}
        else:
            r["position"] = {"weight": 0.0, "basis": "No published bullish forecast at the 1-month horizon"}


def _outlook_text(recs):
    for r in recs:
        parts = []
        for h in ("1w", "1m", "3m"):
            x = r["horizons"][h]
            tag = "" if x["published"] else " (below confidence threshold)"
            parts.append(f"{HZ_NAME[h]}: {x['p_up'] * 100:.0f}% up vs {x['base_rate'] * 100:.0f}% typical, median {x['exp_move'] * 100:+.1f}%{tag}")
        r["summary"] = f"{r['trend']} in a {str(r['regime']).lower()} market. " + "; ".join(parts) + "."
        fam = sorted(r.get("family_contrib", []), key=lambda d: -abs(d["value"]))[:2]
        r["explanation"] = ("Biggest factor groups: " + ", ".join(f"{d['family'].lower()} ({'bullish' if d['value'] > 0 else 'bearish'})" for d in fam) + ".") if fam else ""


# --------------------------------------------------------------------------- ranking engine
def rankings(recs: list[dict], n: int = 20) -> dict:
    P = config.PRIMARY_HORIZON
    rows = []
    for r in recs:
        fq, hp, h3 = r["fundamentals"], r["horizons"][P], r["horizons"]["3m"]
        row = r["_row"] if "_row" in r else {}
        rows.append({"ticker": r["ticker"], "name": r["name"], "risk": r["risk_rating"], "p_up": hp["p_up"], "edge": hp["edge"],
                     "published": hp["published"], "conf": hp["confidence"], "exp_move": hp["exp_move"], "low": hp["band"][0],
                     "risk_adj": hp["risk_adj"], "rr": hp["rr"] or 0, "edge3": h3["edge"], "exp3": h3["exp_move"],
                     "quality": fq.get("quality") or 50, "growth": fq.get("growth") or 50, "stability": fq.get("stability") or 50,
                     "profitability": fq.get("profitability") or 50, "cagr": r["risk_stats"].get("cagr_5y") or 0,
                     "trend": r["trend"], "watch": "Watchlist" in r["groups"]})
    df = pd.DataFrame(rows).set_index("ticker")
    conf_num = df["conf"].map({"High": 3, "Medium": 2, "Low": 1})
    # momentum score from the latest features (stored on recs via summary fields)
    mom = pd.Series({r["ticker"]: r.get("_mom", np.nan) for r in recs})
    df["momentum"] = mom.reindex(df.index)
    df["growth_stability"] = np.sqrt(df["growth"].clip(0) * df["stability"].clip(0))
    df["conf_score"] = conf_num * 100 + df["edge"].abs() * 100
    out = {}

    def pack(sub, why):
        return [{"ticker": t, "name": df.at[t, "name"], "p_up": df.at[t, "p_up"], "exp_move": df.at[t, "exp_move"],
                 "conf": df.at[t, "conf"], "risk": int(df.at[t, "risk"]), "quality": df.at[t, "quality"], "why": why(t)} for t in sub]

    lr = df[(df["risk"] <= 4) & (df["growth"] >= 50)].copy()
    lr["score"] = lr["growth"] * .4 + lr["quality"] * .3 + (100 - lr["risk"] * 10) * .3 + lr["edge3"] * 100
    out["low_risk_growth"] = pack(lr.sort_values("score", ascending=False).head(n).index,
                                  lambda t: f"Risk {df.at[t, 'risk']}/10 · growth score {df.at[t, 'growth']:.0f} · quality {df.at[t, 'quality']:.0f}")
    hp = df.sort_values(["published", "p_up"], ascending=[False, False])
    out["highest_probability"] = pack(hp.head(n).index, lambda t: f"{df.at[t, 'p_up'] * 100:.0f}% chance up in 1 month ({df.at[t, 'conf']} confidence)")
    mm = df[df["trend"].isin(["Strong uptrend", "Uptrend"])].sort_values("momentum", ascending=False)
    out["momentum"] = pack(mm.head(n).index, lambda t: f"{df.at[t, 'trend']} · momentum score {df.at[t, 'momentum']:.0f}/100")
    cp = df.copy(); cp["score"] = cp["quality"] * .45 + cp["profitability"] * .2 + cp["stability"] * .15 + _pct_rank(cp["cagr"]) * 100 * .2
    out["compounders"] = pack(cp.sort_values("score", ascending=False).head(n).index,
                              lambda t: f"Quality {df.at[t, 'quality']:.0f} · 5-yr CAGR {df.at[t, 'cagr'] * 100:.0f}% · stability {df.at[t, 'stability']:.0f}")
    op = df[df["published"] & (df["edge"] > 0)].copy()
    op["score"] = op["edge"] * 100 * conf_num.reindex(op.index) + op["risk_adj"] * 5 - op["risk"] * 0.5
    out["opportunities_30d"] = pack(op.sort_values("score", ascending=False).head(n).index,
                                    lambda t: f"{df.at[t, 'p_up'] * 100:.0f}% up (edge {df.at[t, 'edge'] * 100:+.1f} pts) · median {df.at[t, 'exp_move'] * 100:+.1f}% · R/R {df.at[t, 'rr']:.2f}")
    nt = df[~df["published"] & (df["edge"] > 0)].copy()
    out["near_threshold"] = pack(nt.sort_values("edge", ascending=False).head(10).index,
                                 lambda t: f"Not published: {df.at[t, 'p_up'] * 100:.0f}% up, edge {df.at[t, 'edge'] * 100:+.1f} pts")
    # ranking engine: full sortable table keys
    out["engine"] = {
        "probability": df.sort_values("p_up", ascending=False).index[:n].tolist(),
        "risk_adjusted": df.sort_values("risk_adj", ascending=False).index[:n].tolist(),
        "confidence": df.sort_values("conf_score", ascending=False).index[:n].tolist(),
        "lowest_downside": df.sort_values("low", ascending=False).index[:n].tolist(),
        "fundamental_quality": df.sort_values("quality", ascending=False).index[:n].tolist(),
        "growth_stability": df.sort_values("growth_stability", ascending=False).index[:n].tolist(),
    }
    return out


def attach_momentum(recs, panel):
    """Momentum score 0-100 from cross-sectional ranks of 12-1m momentum, 3m relative strength,
    distance above the 200-day average and 6-month Sharpe."""
    latest = panel.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    cols = [c for c in ("tech_mom_12_1", "rel_vs_mkt_63d", "tech_dist_sma200", "tech_sharpe_126") if c in latest]
    score = latest[cols].rank(pct=True).mean(axis=1) * 100
    for r in recs:
        r["_mom"] = float(score.get(r["ticker"], np.nan))
        r["momentum_score"] = r["_mom"]
