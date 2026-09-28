"""Data loading: Yahoo Finance prices, FRED macro, and a synthetic demo generator."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


# --------------------------------------------------------------------------- real data
def load_prices(symbols: list[str], years: int = config.HISTORY_YEARS) -> dict[str, pd.DataFrame]:
    """Download daily OHLCV for each symbol. Returns {symbol: DataFrame[open, high, low, close, volume]}."""
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    raw = yf.download(sorted(set(symbols)), period=f"{years}y", interval="1d",
                      auto_adjust=True, group_by="ticker", progress=False, threads=True)
    for s in set(symbols):
        try:
            df = raw[s].rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])
        except (KeyError, TypeError):
            continue
        if len(df) > 60:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            out[s] = df
    missing = set(symbols) - set(out)
    if missing:
        print(f"  ! no price data for: {', '.join(sorted(missing))}")
    return out


def load_fred(series: dict[str, str] = config.FRED_SERIES) -> pd.DataFrame:
    """Download FRED series as CSV (no API key needed). Returns a daily, forward-filled, release-lagged frame."""
    frames = {}
    for name, sid in series.items():
        try:
            s = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}",
                            index_col=0, parse_dates=True).iloc[:, 0]
            frames[name] = pd.to_numeric(s, errors="coerce")
        except Exception as e:  # network / format issues -> skip that series
            print(f"  ! FRED {sid} unavailable ({e.__class__.__name__})")
    return transform_macro(frames)


def transform_macro(frames: dict[str, pd.Series]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    out = {}
    if "cpi" in frames:
        out["macro_cpi_yoy"] = frames["cpi"].pct_change(12, fill_method=None) * 100
    if "unrate" in frames:
        out["macro_unrate"] = frames["unrate"]
        out["macro_unrate_chg3m"] = frames["unrate"].diff(3)
    if "fedfunds" in frames:
        out["macro_fedfunds"] = frames["fedfunds"]
        out["macro_fedfunds_chg6m"] = frames["fedfunds"].diff(6)
    if "umcsent" in frames:
        out["macro_umcsent"] = frames["umcsent"]
    if "gdp" in frames:
        out["macro_gdp_yoy"] = frames["gdp"].pct_change(4, fill_method=None) * 100
    df = pd.DataFrame(out)
    # A month's value is published ~2-6 weeks later: shift the index forward so a
    # value is only visible after it would have been released.
    df.index = df.index + pd.DateOffset(months=1) + pd.DateOffset(days=15)
    return df.resample("D").ffill()


def load_earnings_dates(symbol: str) -> list[pd.Timestamp]:
    """Past and upcoming earnings dates (best effort)."""
    try:
        import yfinance as yf
        ed = yf.Ticker(symbol).get_earnings_dates(limit=40)
        return sorted(pd.to_datetime(ed.index).tz_localize(None).normalize().unique())
    except Exception:
        return []


# --------------------------------------------------------------------------- demo data
def synthetic_universe(tickers: list[str], years: int = 6, seed: int = 7):
    """Random-walk prices with volatility regimes, market beta, sector co-movement and mild
    momentum/mean-reversion so the pipeline has something realistic (but not predictable)
    to learn from. Used only for --demo runs; these are NOT real prices."""
    rng = np.random.default_rng(seed)
    n = years * 252
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)

    # market factor with GARCH-like vol clustering
    vol = np.empty(n); r_m = np.empty(n); v = 0.01
    for t in range(n):
        v = np.sqrt(1e-6 + 0.08 * (r_m[t - 1] ** 2 if t else 0) + 0.9 * v ** 2)
        vol[t] = v
        r_m[t] = 0.0004 + v * rng.standard_normal()
    mkt_close = 400 * np.exp(np.cumsum(r_m))

    def ohlcv(close, base_vol):
        prev = np.r_[close[0], close[:-1]]
        spread = np.abs(rng.normal(0, base_vol, len(close))) * close
        high = np.maximum(close, prev) + spread * 0.6
        low = np.minimum(close, prev) - spread * 0.6
        open_ = prev * (1 + rng.normal(0, base_vol / 3, len(close)))
        volume = (1e6 * np.exp(rng.normal(0, 0.35, len(close))) * (1 + 20 * np.abs(np.diff(np.log(np.r_[close[0], close])))))
        return pd.DataFrame({"open": open_, "high": np.maximum(high, open_), "low": np.minimum(low, open_),
                             "close": close, "volume": volume}, index=idx)

    prices = {}
    sectors = sorted(set(config.SECTOR_MAP.get(t, config.DEFAULT_SECTOR) for t in tickers) | set(config.MARKET.values()))
    sec_ret = {}
    for s in sectors:
        beta = rng.uniform(0.8, 1.4)
        r = beta * r_m + rng.normal(0, 0.006, n)
        sec_ret[s] = r
        prices[s] = ohlcv(100 * np.exp(np.cumsum(r)), 0.008)
    prices["SPY"] = ohlcv(mkt_close, 0.007)

    for t in tickers:
        sec = config.SECTOR_MAP.get(t, config.DEFAULT_SECTOR)
        beta = rng.uniform(0.9, 1.8); idio = rng.uniform(0.012, 0.035)
        mom = rng.uniform(-0.04, 0.06)
        r = np.empty(n); prev = 0.0
        for i in range(n):
            r[i] = 0.0003 + 0.6 * sec_ret[sec][i] + 0.4 * beta * r_m[i] + mom * prev + idio * rng.standard_t(4) / np.sqrt(2)
            prev = r[i]
        prices[t] = ohlcv(rng.uniform(20, 600) * np.exp(np.cumsum(r)), idio / 2)

    # cross-asset series
    walk = lambda start, sd, drift=0: start * np.exp(np.cumsum(rng.normal(drift, sd, n)))
    vix = np.clip(12 + 900 * (vol - vol.mean()) + rng.normal(0, 1, n), 9, 80)
    macro_px = {"^VIX": vix, "^TNX": np.clip(3.5 + np.cumsum(rng.normal(0, 0.04, n)), 0.5, 7),
                "^IRX": np.clip(3.0 + np.cumsum(rng.normal(0, 0.03, n)), 0, 7),
                "CL=F": walk(75, 0.02), "GC=F": walk(1900, 0.009, 0.0002), "DX-Y.NYB": walk(100, 0.004),
                "HYG": walk(80, 0.003)}
    for k, v in macro_px.items():
        prices[k] = ohlcv(np.asarray(v, float), 0.005)
    for k in ("QQQ", "DIA", "IWM"):
        prices.setdefault(k, prices["SPY"].copy())

    m_idx = pd.date_range(idx[0] - pd.DateOffset(years=2), idx[-1], freq="MS")
    m = len(m_idx)
    frames = {"cpi": pd.Series(250 * np.exp(np.cumsum(rng.normal(0.0025, 0.002, m))), m_idx),
              "unrate": pd.Series(np.clip(4 + np.cumsum(rng.normal(0, 0.1, m)), 3, 9), m_idx),
              "fedfunds": pd.Series(np.clip(3 + np.cumsum(rng.normal(0, 0.12, m)), 0, 6), m_idx),
              "umcsent": pd.Series(np.clip(80 + np.cumsum(rng.normal(0, 2, m)), 50, 110), m_idx)}
    q_idx = pd.date_range(m_idx[0], idx[-1], freq="QS")
    frames["gdp"] = pd.Series(20000 * np.exp(np.cumsum(rng.normal(0.005, 0.006, len(q_idx)))), q_idx)
    macro = transform_macro(frames)

    earnings = {t: list(pd.bdate_range(idx[0], idx[-1] + pd.Timedelta(days=90), freq="91D")
                        + pd.Timedelta(days=int(rng.integers(0, 60)))) for t in tickers}
    return prices, macro, earnings


def synthetic_live(tickers: list[str], seed: int = 11) -> dict[str, dict]:
    """Fake current-only signals for the demo dashboard."""
    rng = np.random.default_rng(seed)
    out = {}
    for t in tickers:
        out[t] = {
            "news": {"score": float(np.clip(rng.normal(0, 0.35), -1, 1)), "n": int(rng.integers(3, 15)),
                     "headlines": [{"title": f"Sample headline {i + 1} for {t}", "score": float(np.round(rng.normal(0, .5), 2))} for i in range(3)]},
            "analyst": {"score": float(np.clip(rng.normal(0.1, 0.4), -1, 1)), "target_upside": float(rng.normal(0.12, 0.15)),
                        "net_upgrades_30d": int(rng.integers(-2, 3)), "rating": ["Buy", "Hold", "Strong Buy", "Hold"][rng.integers(0, 4)]},
            "options": {"score": float(np.clip(rng.normal(0, 0.35), -1, 1)), "put_call_vol": float(rng.uniform(0.4, 1.4)),
                        "put_call_oi": float(rng.uniform(0.5, 1.3)), "iv_atm": float(rng.uniform(0.3, 0.9)),
                        "iv_vs_rv": float(rng.uniform(0.8, 1.5)), "unusual": bool(rng.random() < 0.2)},
            "institutional": {"score": float(np.clip(rng.normal(0, 0.3), -1, 1)), "inst_pct": float(rng.uniform(0.3, 0.85)),
                              "insider_net_6m": float(rng.normal(0, 1e6))},
        }
    return out
