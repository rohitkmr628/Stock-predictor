"""Stock universe: index constituents, fundamentals snapshot, quality score and screen."""
from __future__ import annotations

import io
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

import config

WIKI = {
    "sp500": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol"),
    "ndx": ("https://en.wikipedia.org/wiki/Nasdaq-100", "Ticker"),
    "dow": ("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average", "Symbol"),
}
FUND_FIELDS = ["longName", "shortName", "sector", "industry", "marketCap", "revenueGrowth", "earningsGrowth",
               "returnOnEquity", "returnOnAssets", "profitMargins", "operatingMargins", "grossMargins",
               "freeCashflow", "totalRevenue", "debtToEquity", "currentRatio", "trailingPE", "forwardPE",
               "pegRatio", "beta", "dividendYield", "country", "currency", "quoteType"]


def _read_wiki(url: str, col: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (odds-board research script)"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    for t in pd.read_html(io.StringIO(html)):
        if col in t.columns:
            return [str(s).strip().replace(".", "-") for s in t[col].dropna()]
    return []


def index_constituents() -> dict[str, list[str]]:
    out = {}
    if config.USE_WIKIPEDIA_CONSTITUENTS:
        for k, (url, col) in WIKI.items():
            try:
                out[k] = _read_wiki(url, col)
                print(f"  {k}: {len(out[k])} constituents")
            except Exception as e:
                print(f"  ! could not read {k} constituents ({e.__class__.__name__}); using built-in list")
    return out


def candidate_list() -> tuple[list[str], dict[str, list[str]]]:
    idx = index_constituents()
    cands = set(config.FALLBACK_UNIVERSE) | set(config.GLOBAL_BLUE_CHIPS)
    for v in idx.values():
        cands |= set(v)
    membership = {}
    for t in cands | set(config.WATCHLIST):
        m = [name for name, lst in (("S&P 500", idx.get("sp500", [])), ("Nasdaq-100", idx.get("ndx", [])),
                                    ("Dow 30", idx.get("dow", []))) if t in lst]
        if t in config.GLOBAL_BLUE_CHIPS:
            m.append("Global blue chip")
        if t in config.WATCHLIST:
            m.append("Watchlist")
        membership[t] = m
    return sorted(cands), membership


# --------------------------------------------------------------------------- fundamentals
def fetch_fundamentals(tickers: list[str], workers: int = 6) -> dict[str, dict]:
    import yfinance as yf

    def one(t):
        for attempt in range(3):
            try:
                info = yf.Ticker(t).info or {}
                return t, {k: info.get(k) for k in FUND_FIELDS}
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        return t, {}

    with ThreadPoolExecutor(workers) as ex:
        res = dict(ex.map(one, tickers))
    ok = sum(1 for v in res.values() if v.get("marketCap"))
    print(f"  fundamentals: {ok}/{len(tickers)} tickers")
    return res


def load_cached_fundamentals() -> dict:
    p = os.path.join(config.STATE_DIR, "fundamentals.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def save_fundamentals(f: dict):
    os.makedirs(config.STATE_DIR, exist_ok=True)
    json.dump(f, open(os.path.join(config.STATE_DIR, "fundamentals.json"), "w"))


def _pct_rank(s: pd.Series, higher_better=True) -> pd.Series:
    r = s.rank(pct=True)
    r = r if higher_better else 1 - r + 1 / max(len(s.dropna()), 1)
    return r.fillna(0.5)


def quality_scores(fund: dict[str, dict], risk_stats: pd.DataFrame | None = None) -> pd.DataFrame:
    """0-100 scores: growth, profitability, cash flow, balance sheet, stability and overall quality."""
    df = pd.DataFrame(fund).T
    for c in FUND_FIELDS:
        if c not in df:
            df[c] = np.nan
    num = ["marketCap", "revenueGrowth", "earningsGrowth", "returnOnEquity", "returnOnAssets", "profitMargins",
           "operatingMargins", "grossMargins", "freeCashflow", "totalRevenue", "debtToEquity", "currentRatio",
           "trailingPE", "forwardPE", "pegRatio", "beta"]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    df["fcf_margin"] = df["freeCashflow"] / df["totalRevenue"]
    fin = df["sector"].eq("Financial Services")
    de = df["debtToEquity"].where(~fin)          # leverage metrics aren't comparable for banks
    s = pd.DataFrame(index=df.index)
    s["growth"] = (_pct_rank(df["revenueGrowth"].clip(-0.5, 1.5)) * 0.5 + _pct_rank(df["earningsGrowth"].clip(-1, 3)) * 0.5)
    s["profitability"] = (_pct_rank(df["returnOnEquity"].clip(-1, 2)) * 0.4 + _pct_rank(df["operatingMargins"]) * 0.3
                          + _pct_rank(df["profitMargins"]) * 0.3)
    s["cash_flow"] = _pct_rank(df["fcf_margin"].clip(-1, 1))
    s["balance_sheet"] = (_pct_rank(de, higher_better=False) * 0.6 + _pct_rank(df["currentRatio"].clip(0, 5)) * 0.4)
    if risk_stats is not None and len(risk_stats):
        rs = risk_stats.reindex(df.index)
        s["stability"] = (_pct_rank(rs["vol_1y"], False) * 0.35 + _pct_rank(rs["max_dd_3y"], True) * 0.35
                          + _pct_rank(rs["pos_12m_share"]) * 0.30)
    else:
        s["stability"] = 0.5
    val = _pct_rank(df["forwardPE"].where(df["forwardPE"] > 0), higher_better=False)
    s["valuation"] = val
    s["quality"] = (s["growth"] * 0.25 + s["profitability"] * 0.25 + s["cash_flow"] * 0.2 + s["balance_sheet"] * 0.15
                    + s["stability"] * 0.15)
    s = (s * 100).round(1)
    return df.join(s)


def screen(q: pd.DataFrame, membership: dict) -> tuple[list[str], pd.DataFrame]:
    """Apply the quality screen; keep the top MAX_UNIVERSE by quality plus all watchlist names."""
    c = config.SCREEN
    fin = q["sector"].eq("Financial Services")
    ok = (q["marketCap"].fillna(0) >= config.MIN_MARKET_CAP)
    ok &= q["profitMargins"].fillna(-1) > c["min_profit_margin"]
    ok &= (q["freeCashflow"].fillna(-1) > c["min_fcf"]) | fin
    ok &= (q["debtToEquity"].fillna(0) <= c["max_debt_to_equity"]) | fin
    q = q.assign(passes_screen=ok)
    keep = q[ok].sort_values("quality", ascending=False).head(config.MAX_UNIVERSE).index.tolist()
    if len(keep) < config.MAX_UNIVERSE * 0.5:   # fundamentals partly unavailable (e.g. Yahoo rate limits): fall back to the built-in large-cap list
        extra = [t for t in config.FALLBACK_UNIVERSE if t not in keep and pd.isna(q["marketCap"].get(t))]
        print(f"  ! only {len(keep)} names passed with data; adding {min(len(extra), config.MAX_UNIVERSE - len(keep))} built-in large caps unscreened")
        keep += extra[:config.MAX_UNIVERSE - len(keep)]
    wl = list(config.WATCHLIST)
    universe = list(dict.fromkeys(keep + wl))
    print(f"  screen: {int(ok.sum())} pass → universe {len(universe)} (incl. {len(wl)} watchlist)")
    return universe, q


def risk_stats_from_prices(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = {}
    for t, df in prices.items():
        c = df["close"]
        if len(c) < 260:
            continue
        lr = np.log(c).diff()
        c3 = c.iloc[-756:]
        rows[t] = {"vol_1y": lr.iloc[-252:].std() * np.sqrt(252),
                   "max_dd_3y": float((c3 / c3.cummax() - 1).min()),
                   "pos_12m_share": float((c.pct_change(252, fill_method=None).dropna() > 0).mean()),
                   "cagr_5y": float((c.iloc[-1] / c.iloc[-min(len(c), 1260)]) ** (252 / min(len(c), 1260)) - 1)}
    return pd.DataFrame(rows).T
