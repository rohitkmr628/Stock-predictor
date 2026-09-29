"""Current-only signals: news sentiment, analyst revisions, options market, institutional/insider activity.

These have no reliable free history, so they can't be backtested. They are scored to [-1, +1]
and nudge the backtested model probability by a small, capped amount (see config.OVERLAY_WEIGHTS).
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

import config

# How much each overlay matters at each horizon (news fades fast, analyst/institutional build slowly).
HORIZON_SCALE = {
    "news_sentiment": {"1d": 1.0, "1w": 0.7, "1m": 0.4, "3m": 0.2},
    "analyst": {"1d": 0.3, "1w": 0.6, "1m": 1.0, "3m": 1.0},
    "options": {"1d": 1.0, "1w": 0.8, "1m": 0.5, "3m": 0.3},
    "institutional": {"1d": 0.2, "1w": 0.5, "1m": 1.0, "3m": 1.0},
}
SOURCE_KEY = {"news_sentiment": "news", "analyst": "analyst", "options": "options", "institutional": "institutional"}

# Small finance lexicon used when VADER isn't installed.
POS = {"beat", "beats", "surge", "surges", "soar", "soars", "jump", "jumps", "rally", "rallies", "record", "upgrade",
       "upgraded", "raises", "raised", "strong", "growth", "gain", "gains", "outperform", "bullish", "buy", "wins",
       "win", "approval", "approved", "partnership", "contract", "expands", "boost", "boosts", "higher", "tops", "profit",
       "breakthrough", "rebound", "rebounds", "buyback", "accelerates", "exceeds", "optimistic"}
NEG = {"miss", "misses", "plunge", "plunges", "fall", "falls", "drop", "drops", "slump", "slumps", "downgrade",
       "downgraded", "cut", "cuts", "lowers", "lowered", "weak", "loss", "losses", "lawsuit", "probe", "investigation",
       "recall", "bearish", "sell", "warning", "warns", "delay", "delayed", "decline", "declines", "lower", "fraud",
       "halt", "halts", "layoffs", "tariff", "tariffs", "ban", "risk", "concerns", "slows", "resigns", "sinks", "tumbles"}


def _sentiment(text: str) -> float:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        return float(SentimentIntensityAnalyzer().polarity_scores(text)["compound"])
    except Exception:
        words = re.findall(r"[a-z]+", text.lower())
        p = sum(w in POS for w in words); n = sum(w in NEG for w in words)
        return 0.0 if p + n == 0 else (p - n) / (p + n)


def _squash(x: float, scale: float) -> float:
    return float(np.tanh(x / scale)) if x == x else 0.0


# --------------------------------------------------------------------------- collectors
def news_signal(tk) -> dict:
    items = []
    try:
        for it in (tk.news or [])[:20]:
            c = it.get("content", it)
            title = c.get("title") or ""
            summary = c.get("summary") or ""
            url = (c.get("canonicalUrl") or {}).get("url") or c.get("link") or ""
            src = (c.get("provider") or {}).get("displayName") or c.get("publisher") or ""
            if title:
                items.append({"title": title, "source": src, "url": url, "score": round(_sentiment(f"{title}. {summary}"), 2)})
    except Exception:
        pass
    score = float(np.mean([i["score"] for i in items])) if items else 0.0
    return {"score": float(np.clip(score * 1.5, -1, 1)), "n": len(items), "headlines": items[:5]}


def analyst_signal(tk, price: float) -> dict:
    out = {"score": 0.0, "target_upside": None, "net_upgrades_30d": 0, "rating": None}
    parts = []
    try:
        pt = tk.analyst_price_targets or {}
        mean = pt.get("mean") or pt.get("median")
        if mean and price:
            out["target_upside"] = float(mean / price - 1)
            parts.append(_squash(out["target_upside"], 0.25))
    except Exception:
        pass
    try:
        ud = tk.upgrades_downgrades
        if ud is not None and len(ud):
            ud.index = pd.to_datetime(ud.index).tz_localize(None)
            recent = ud[ud.index >= pd.Timestamp.today() - pd.Timedelta(days=30)]
            act = recent.get("Action", pd.Series(dtype=str)).str.lower()
            net = int((act == "up").sum() - (act == "down").sum())
            out["net_upgrades_30d"] = net
            parts.append(_squash(net, 2))
    except Exception:
        pass
    try:
        rec = (tk.info or {}).get("recommendationMean")   # 1 = strong buy ... 5 = sell
        if rec:
            out["rating"] = {1: "Strong Buy", 2: "Buy", 3: "Hold", 4: "Underperform", 5: "Sell"}[int(round(rec))]
            parts.append(float(np.clip((3 - rec) / 2, -1, 1)) * 0.5)
    except Exception:
        pass
    out["score"] = float(np.clip(np.mean(parts), -1, 1)) if parts else 0.0
    return out


def options_signal(tk, price: float, realized_vol: float) -> dict:
    out = {"score": 0.0, "put_call_vol": None, "put_call_oi": None, "iv_atm": None, "iv_vs_rv": None, "unusual": False}
    try:
        exps = tk.options
        if not exps:
            return out
        today = pd.Timestamp.today().normalize()
        exp = next((e for e in exps if (pd.Timestamp(e) - today).days >= 7), exps[0])
        ch = tk.option_chain(exp)
        calls, puts = ch.calls.fillna(0), ch.puts.fillna(0)
        cv, pv = calls["volume"].sum(), puts["volume"].sum()
        co, po = calls["openInterest"].sum(), puts["openInterest"].sum()
        out["put_call_vol"] = float(pv / cv) if cv else None
        out["put_call_oi"] = float(po / co) if co else None
        atm = calls.iloc[(calls["strike"] - price).abs().argsort()[:3]]
        iv = float(atm["impliedVolatility"].mean())
        out["iv_atm"] = iv
        out["iv_vs_rv"] = float(iv / realized_vol) if realized_vol else None
        big = lambda d: ((d["volume"] > 5 * d["openInterest"].clip(lower=1)) & (d["volume"] > 1000))
        uc, up_ = big(calls).sum(), big(puts).sum()
        out["unusual"] = bool(uc + up_ > 0)
        parts = []
        if out["put_call_vol"]:
            parts.append(-_squash(math.log(out["put_call_vol"] / 0.7), 0.5))   # lots of puts = bearish positioning
        if uc + up_:
            parts.append(float(np.sign(uc - up_)) * 0.5)
        out["score"] = float(np.clip(np.mean(parts), -1, 1)) if parts else 0.0
    except Exception:
        pass
    return out


def institutional_signal(tk) -> dict:
    out = {"score": 0.0, "inst_pct": None, "insider_net_6m": None}
    parts = []
    try:
        info = tk.info or {}
        out["inst_pct"] = info.get("heldPercentInstitutions")
    except Exception:
        pass
    try:
        it = tk.insider_transactions
        if it is not None and len(it):
            it = it.copy()
            it["Start Date"] = pd.to_datetime(it["Start Date"])
            it = it[it["Start Date"] >= pd.Timestamp.today() - pd.Timedelta(days=182)]
            txt = it["Text"].fillna("").str.lower()
            val = it["Value"].fillna(0)
            net = float(val[txt.str.contains("purchase")].sum() - val[txt.str.contains("sale")].sum())
            out["insider_net_6m"] = net
            parts.append(_squash(net, 5e6) * 0.6)
    except Exception:
        pass
    out["score"] = float(np.clip(np.mean(parts), -1, 1)) if parts else 0.0
    return out


def collect_live(tickers: list[str], last_close: dict[str, float], realized_vol: dict[str, float]) -> dict:
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    def one(t):
        try:
            tk = yf.Ticker(t); px = last_close.get(t)
            return t, {"news": news_signal(tk), "analyst": analyst_signal(tk, px),
                       "options": options_signal(tk, px, realized_vol.get(t)), "institutional": institutional_signal(tk)}
        except Exception:
            return t, None

    with ThreadPoolExecutor(6) as ex:
        live = {t: v for t, v in ex.map(one, tickers) if v}
    print(f"  live signals: {len(live)}/{len(tickers)} tickers")
    return live


# --------------------------------------------------------------------------- apply
def adjust_probability(p: float, horizon: str, live: dict | None) -> tuple[float, dict]:
    """Shift the model probability in log-odds space by the weighted overlay scores."""
    if not live:
        return p, {}
    logit = math.log(p / (1 - p))
    shifts = {}
    for key, w in config.OVERLAY_WEIGHTS.items():
        src = SOURCE_KEY.get(key)
        if not w or not src or src not in live:
            continue
        s = float(live[src].get("score") or 0.0)
        shifts[key] = w * HORIZON_SCALE[key][horizon] * s
    logit += sum(shifts.values())
    return 1 / (1 + math.exp(-logit)), shifts
