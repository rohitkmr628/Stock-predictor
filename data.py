"""Data loading: Yahoo Finance prices and earnings history, FRED macro, and a synthetic demo generator."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

import config


# --------------------------------------------------------------------------- prices
def _download(symbols, years):
    import yfinance as yf
    raw = yf.download(symbols, period=f"{years}y", interval="1d", auto_adjust=True, group_by="ticker",
                      progress=False, threads=True)
    out = {}
    for s in symbols:
        try:
            df = raw[s] if len(symbols) > 1 else raw
            df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])
        except (KeyError, TypeError):
            continue
        if len(df) > 260:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            out[s] = df
    return out


def load_prices(symbols: list[str], years: int = config.HISTORY_YEARS, chunk: int = 60) -> dict[str, pd.DataFrame]:
    """Daily OHLCV in batches; retries missing tickers with alternative symbols (e.g. FLT.V → FLT.TO)."""
    symbols = sorted(set(symbols))
    out = {}
    for i in range(0, len(symbols), chunk):
        batch = symbols[i:i + chunk]
        for attempt in range(3):
            try:
                out.update(_download(batch, years)); break
            except Exception as e:
                print(f"  ! batch {i // chunk + 1} failed ({e.__class__.__name__}), retrying")
                time.sleep(5 * (attempt + 1))
    missing = [s for s in symbols if s not in out]
    for s in missing:
        for alt in config.ALT_SYMBOLS.get(s, []):
            got = _download([alt], years)
            if alt in got:
                out[s] = got[alt]; print(f"  {s}: using {alt}"); break
    missing = [s for s in symbols if s not in out]
    if missing:
        print(f"  ! no price data for: {', '.join(missing)}")
    return out


def load_earnings_history(tickers: list[str], workers: int = 6) -> dict[str, list[dict]]:
    """Past/upcoming earnings dates with EPS surprise (point-in-time: known on the report date)."""
    import yfinance as yf

    def one(t):
        try:
            ed = yf.Ticker(t).get_earnings_dates(limit=48)
            if ed is None or ed.empty:
                return t, []
            ed = ed.copy(); ed.index = pd.to_datetime(ed.index).tz_localize(None).normalize()
            sur = pd.to_numeric(ed.get("Surprise(%)"), errors="coerce")
            return t, [{"date": str(d.date()), "surprise": (None if pd.isna(v) else float(v))} for d, v in sur.items()]
        except Exception:
            return t, []

    with ThreadPoolExecutor(workers) as ex:
        return dict(ex.map(one, tickers))


def load_fred(series: dict[str, str] = config.FRED_SERIES) -> pd.DataFrame:
    frames = {}
    for name, sid in series.items():
        try:
            s = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", index_col=0, parse_dates=True).iloc[:, 0]
            frames[name] = pd.to_numeric(s, errors="coerce")
        except Exception as e:
            print(f"  ! FRED {sid} unavailable ({e.__class__.__name__})")
    return transform_macro(frames)


def transform_macro(frames: dict[str, pd.Series]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    out = {}
    if "cpi" in frames:
        out["macro_cpi_yoy"] = frames["cpi"].pct_change(12, fill_method=None) * 100
        out["macro_cpi_3m_ann"] = ((frames["cpi"] / frames["cpi"].shift(3)) ** 4 - 1) * 100
    if "unrate" in frames:
        u = frames["unrate"]
        out["macro_unrate"] = u
        out["macro_sahm"] = u.rolling(3).mean() - u.rolling(12).min()          # recession signal
    if "fedfunds" in frames:
        out["macro_fedfunds"] = frames["fedfunds"]; out["macro_fedfunds_chg6m"] = frames["fedfunds"].diff(6)
    if "umcsent" in frames:
        out["macro_umcsent"] = frames["umcsent"]
    if "gdp" in frames:
        out["macro_gdp_yoy"] = frames["gdp"].pct_change(4, fill_method=None) * 100
    if "indpro" in frames:
        out["macro_indpro_yoy"] = frames["indpro"].pct_change(12, fill_method=None) * 100
    df = pd.DataFrame(out)
    df.index = df.index + pd.DateOffset(months=1) + pd.DateOffset(days=15)   # release lag
    return df.resample("D").ffill()


# --------------------------------------------------------------------------- synthetic demo
def synthetic_universe(n_stocks: int = 40, years: int = 10, seed: int = 7):
    """Simulated market for --demo runs. Includes two weak, genuine effects (post-earnings drift and
    12-1 month momentum) so the backtest can show whether the pipeline detects a real edge.
    These are NOT real prices."""
    rng = np.random.default_rng(seed)
    n = years * 252
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    # market with vol clustering and two crash episodes
    r_m = np.empty(n); v = 0.01; vol = np.empty(n)
    shocks = {int(n * 0.35): -0.012, int(n * 0.72): -0.006}
    drift = np.full(n, 0.0004)
    for s0, d in shocks.items():
        drift[s0:s0 + 40] = d
    for t in range(n):
        v = np.sqrt(2e-6 + 0.09 * (r_m[t - 1] ** 2 if t else 0) + 0.89 * v ** 2)
        vol[t] = v; r_m[t] = drift[t] + v * rng.standard_normal()
    sectors = list(config.SECTOR_ETF.items())
    prices, fund, earnings = {}, {}, {}

    def ohlcv(close, bv):
        prev = np.r_[close[0], close[:-1]]
        spread = np.abs(rng.normal(0, bv, len(close))) * close
        high = np.maximum(close, prev) + spread * .6; low = np.minimum(close, prev) - spread * .6
        op = prev * (1 + rng.normal(0, bv / 3, len(close)))
        volu = 1e6 * np.exp(rng.normal(0, .35, len(close))) * (1 + 20 * np.abs(np.diff(np.log(np.r_[close[0], close]))))
        return pd.DataFrame({"open": op, "high": np.maximum(high, op), "low": np.minimum(low, op), "close": close, "volume": volu}, index=idx)

    sec_ret = {}
    for name, etf in sectors:
        r = rng.uniform(.7, 1.3) * r_m + rng.normal(0, .005, n); sec_ret[etf] = r
        prices[etf] = ohlcv(100 * np.exp(np.cumsum(r)), .007)
    prices["SPY"] = ohlcv(400 * np.exp(np.cumsum(r_m)), .006)
    for k in ("QQQ", "DIA", "IWM", "SMH", "IGV", "UFO", "ITA", "ICLN", "LIT"):
        prices[k] = ohlcv(100 * np.exp(np.cumsum(1.1 * r_m + rng.normal(0, .004, n))), .007)

    for i in range(n_stocks):
        t = f"DEMO{i + 1:02d}"
        sec, etf = sectors[i % len(sectors)]
        beta = rng.uniform(.7, 1.5); idio = rng.uniform(.010, .028)
        # earnings every ~63 days with random surprise; drift after surprise decays over ~40 days
        e_days = np.arange(int(rng.integers(5, 60)), n + 90, 63)
        surprises = rng.normal(2, 8, len(e_days))
        pead = np.zeros(n)
        for d, s in zip(e_days, surprises):
            if d < n:
                pead[d:min(n, d + 40)] += 0.00018 * np.clip(s, -25, 25) * np.exp(-np.arange(min(n, d + 40) - d) / 25)
        r = np.empty(n); logp = np.zeros(n)
        for k in range(n):
            mom = 0.0
            if k > 252:
                mom = 0.006 * np.tanh((logp[k - 21] - logp[k - 252]) / 0.4) / 21
            r[k] = 0.0002 + .5 * sec_ret[etf][k] + .5 * beta * r_m[k] + pead[k] + mom + idio * rng.standard_t(4) / np.sqrt(2)
            logp[k] = (logp[k - 1] if k else 0) + r[k]
        prices[t] = ohlcv(rng.uniform(30, 500) * np.exp(logp), idio / 2)
        earnings[t] = [{"date": str(idx[d].date()) if d < n else str((idx[-1] + pd.tseries.offsets.BDay(d - n + 1)).date()),
                        "surprise": (float(s) if d < n else None)} for d, s in zip(e_days, surprises)]
        g = rng.normal(.1, .1)
        fund[t] = {"longName": f"Demo Company {i + 1}", "shortName": f"Demo {i + 1}", "sector": sec, "industry": sec,
                   "marketCap": float(rng.uniform(30e9, 2e12)), "revenueGrowth": g, "earningsGrowth": g + rng.normal(0, .1),
                   "returnOnEquity": rng.uniform(.05, .45), "returnOnAssets": rng.uniform(.02, .2),
                   "profitMargins": rng.uniform(.03, .35), "operatingMargins": rng.uniform(.05, .45),
                   "grossMargins": rng.uniform(.3, .8), "freeCashflow": float(rng.uniform(-1e9, 2e10)),
                   "totalRevenue": float(rng.uniform(1e10, 3e11)), "debtToEquity": rng.uniform(10, 200),
                   "currentRatio": rng.uniform(.8, 3), "trailingPE": rng.uniform(12, 50), "forwardPE": rng.uniform(10, 40),
                   "pegRatio": rng.uniform(.8, 3), "beta": beta, "dividendYield": None, "country": "Demo",
                   "currency": "USD", "quoteType": "EQUITY"}

    walk = lambda start, sd, dr=0: start * np.exp(np.cumsum(rng.normal(dr, sd, n)))
    macro_px = {"^VIX": np.clip(12 + 900 * (vol - vol.mean()) + rng.normal(0, 1, n), 9, 80),
                "^TNX": np.clip(2.5 + np.cumsum(rng.normal(0, .04, n)), .5, 7), "^IRX": np.clip(2 + np.cumsum(rng.normal(0, .03, n)), 0, 7),
                "CL=F": walk(70, .02), "GC=F": walk(1500, .009, .0002), "DX-Y.NYB": walk(98, .004), "HYG": walk(80, .003), "TLT": walk(120, .008)}
    for k, vv in macro_px.items():
        prices[k] = ohlcv(np.asarray(vv, float), .005)
    m_idx = pd.date_range(idx[0] - pd.DateOffset(years=2), idx[-1], freq="MS"); m = len(m_idx)
    frames = {"cpi": pd.Series(250 * np.exp(np.cumsum(rng.normal(.0025, .002, m))), m_idx),
              "unrate": pd.Series(np.clip(4 + np.cumsum(rng.normal(0, .1, m)), 3, 10), m_idx),
              "fedfunds": pd.Series(np.clip(2 + np.cumsum(rng.normal(0, .12, m)), 0, 6), m_idx),
              "umcsent": pd.Series(np.clip(85 + np.cumsum(rng.normal(0, 2, m)), 50, 110), m_idx),
              "indpro": pd.Series(100 * np.exp(np.cumsum(rng.normal(.001, .006, m))), m_idx)}
    q_idx = pd.date_range(m_idx[0], idx[-1], freq="QS")
    frames["gdp"] = pd.Series(20000 * np.exp(np.cumsum(rng.normal(.005, .006, len(q_idx)))), q_idx)
    return prices, transform_macro(frames), earnings, fund


def synthetic_live(tickers, seed=11):
    rng = np.random.default_rng(seed)
    out = {}
    for t in tickers:
        out[t] = {"news": {"score": float(np.clip(rng.normal(0, .35), -1, 1)), "n": int(rng.integers(3, 15)),
                           "headlines": [{"title": f"Sample headline {i + 1} for {t}", "source": "Demo", "url": "", "score": float(np.round(rng.normal(0, .5), 2))} for i in range(3)]},
                  "analyst": {"score": float(np.clip(rng.normal(.1, .4), -1, 1)), "target_upside": float(rng.normal(.1, .12)),
                              "net_upgrades_30d": int(rng.integers(-2, 3)), "rating": ["Buy", "Hold", "Strong Buy"][rng.integers(0, 3)]},
                  "options": {"score": float(np.clip(rng.normal(0, .3), -1, 1)), "put_call_vol": float(rng.uniform(.4, 1.3)),
                              "put_call_oi": float(rng.uniform(.5, 1.3)), "iv_atm": float(rng.uniform(.2, .6)),
                              "iv_vs_rv": float(rng.uniform(.8, 1.5)), "unusual": bool(rng.random() < .15)},
                  "institutional": {"score": float(np.clip(rng.normal(0, .3), -1, 1)), "inst_pct": float(rng.uniform(.5, .9)),
                                    "insider_net_6m": float(rng.normal(0, 2e6))}}
    return out
