"""Feature engineering: technical indicators, chart patterns, relative strength, market and macro.
Every feature at date t uses only information available at the close of t (no look-ahead)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config

# Feature families, used to group importance and explanations.
FAMILY_PREFIX = {
    "tech_": "Technical indicators",
    "pat_": "Chart patterns",
    "rel_": "Sector & relative strength",
    "mkt_": "Market & index trend",
    "x_": "Rates, volatility & commodities",
    "macro_": "Macroeconomic",
    "earn_": "Earnings calendar",
    "ts_": "Time-series forecast",
}


def family_of(col: str) -> str:
    for p, fam in FAMILY_PREFIX.items():
        if col.startswith(p):
            return fam
    return "Other"


# --------------------------------------------------------------------------- indicators
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rolling_slope_r2(y: pd.Series, n: int) -> tuple[pd.Series, pd.Series]:
    """Slope (per bar) and R^2 of a linear fit over the last n points, vectorised."""
    x = np.arange(n, dtype=float); x -= x.mean(); sxx = (x ** 2).sum()
    vals = y.to_numpy(float)
    slope = np.full(len(vals), np.nan); r2 = np.full(len(vals), np.nan)
    if len(vals) >= n:
        win = np.lib.stride_tricks.sliding_window_view(vals, n)
        ym = win.mean(axis=1, keepdims=True)
        b = ((win - ym) * x).sum(axis=1) / sxx
        ss_tot = ((win - ym) ** 2).sum(axis=1)
        ss_res = ((win - ym - b[:, None] * x) ** 2).sum(axis=1)
        slope[n - 1:] = b
        r2[n - 1:] = 1 - ss_res / np.where(ss_tot == 0, np.nan, ss_tot)
    return pd.Series(slope, y.index), pd.Series(r2, y.index)


def technical_features(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    f = pd.DataFrame(index=df.index)
    lr = np.log(c).diff()
    for n in (1, 5, 10, 21, 63, 126):
        f[f"tech_ret_{n}d"] = c.pct_change(n, fill_method=None)
    for n in (10, 21, 63):
        f[f"tech_vol_{n}d"] = lr.rolling(n).std() * np.sqrt(252)
    f["tech_vol_ratio"] = f["tech_vol_10d"] / f["tech_vol_63d"]
    a = atr(df)
    f["tech_atr_pct"] = a / c
    f["tech_rsi14"] = rsi(c, 14)
    f["tech_rsi2"] = rsi(c, 2)
    ema12, ema26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26; sig = macd.ewm(span=9, adjust=False).mean()
    f["tech_macd"] = macd / c
    f["tech_macd_hist"] = (macd - sig) / c
    f["tech_macd_cross_up"] = ((macd > sig) & (macd.shift() <= sig.shift())).astype(float)
    ma20, sd20 = c.rolling(20).mean(), c.rolling(20).std()
    f["tech_bb_pctb"] = (c - (ma20 - 2 * sd20)) / (4 * sd20)
    f["tech_bb_width"] = 4 * sd20 / ma20
    f["tech_bb_squeeze"] = (f["tech_bb_width"] <= f["tech_bb_width"].rolling(126).quantile(0.1)).astype(float)
    for n in (10, 20, 50, 100, 200):
        f[f"tech_dist_sma{n}"] = c / c.rolling(n).mean() - 1
    f["tech_golden"] = (c.rolling(50).mean() > c.rolling(200).mean()).astype(float)
    f["tech_sma50_slope"] = c.rolling(50).mean().pct_change(10, fill_method=None)
    ll, hh = l.rolling(14).min(), h.rolling(14).max()
    k = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    f["tech_stoch_k"] = k
    f["tech_stoch_d"] = k.rolling(3).mean()
    f["tech_williams_r"] = -100 * (hh - c) / (hh - ll).replace(0, np.nan)
    tp = (h + l + c) / 3
    f["tech_cci"] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True))
    # ADX (trend strength)
    up_m, dn_m = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0), df.index)
    ndm = pd.Series(np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0), df.index)
    pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / a
    ndi = 100 * ndm.ewm(alpha=1 / 14, adjust=False).mean() / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    f["tech_adx"] = dx.ewm(alpha=1 / 14, adjust=False).mean()
    f["tech_di_diff"] = pdi - ndi
    # volume
    lv = np.log(v.replace(0, np.nan))
    f["tech_vol_z"] = (lv - lv.rolling(50).mean()) / lv.rolling(50).std()
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    f["tech_obv_slope"] = (obv - obv.shift(20)) / v.rolling(20).mean() / 20
    mfv = ((c - l) - (h - c)) / (h - l).replace(0, np.nan) * v
    f["tech_cmf"] = mfv.rolling(20).sum() / v.rolling(20).sum()
    f["tech_updown_vol"] = (v.where(c.diff() > 0, 0).rolling(20).sum() / v.where(c.diff() < 0, 0).rolling(20).sum().replace(0, np.nan))
    f["tech_updown_vol"] = np.log(f["tech_updown_vol"].clip(0.1, 10))
    # range / candles
    f["tech_52w_high_dist"] = c / h.rolling(252, min_periods=120).max() - 1
    f["tech_52w_low_dist"] = c / l.rolling(252, min_periods=120).min() - 1
    f["tech_gap"] = df["open"] / c.shift() - 1
    f["tech_body"] = (c - df["open"]) / (h - l).replace(0, np.nan)
    f["tech_close_loc"] = (c - l) / (h - l).replace(0, np.nan)
    f["tech_up_days_10"] = (c.diff() > 0).rolling(10).mean()
    # time-series component: EWMA (RiskMetrics) volatility forecast and AR(1) drift
    ewv = (lr ** 2).ewm(alpha=0.06, adjust=False).mean()
    f["ts_ewma_vol"] = np.sqrt(ewv * 252)
    f["ts_ar1"] = lr.rolling(63).apply(lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if np.std(x) > 0 else 0, raw=True)
    f["ts_drift_63"] = lr.rolling(63).mean() / lr.rolling(63).std()
    s20, r20 = rolling_slope_r2(np.log(c), 20)
    s60, r60 = rolling_slope_r2(np.log(c), 60)
    f["pat_trend20_slope"], f["pat_trend20_r2"] = s20 * 252, r20
    f["pat_trend60_slope"], f["pat_trend60_r2"] = s60 * 252, r60
    return f.copy()


# --------------------------------------------------------------------------- chart patterns
def _pivots(series: np.ndarray, k: int, kind: str) -> np.ndarray:
    """Boolean array: True at i if series[i] is the max/min of [i-k, i+k]. Confirmed only at i+k."""
    s = pd.Series(series)
    roll = s.rolling(2 * k + 1, center=True)
    ext = roll.max() if kind == "high" else roll.min()
    return (s == ext).to_numpy().copy()


def pattern_features(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Rule-based detection of classic chart patterns and support/resistance.
    Values: 1 = confirmed (breakout/breakdown happened), 0.5 = forming, 0 = absent."""
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    n = len(c)
    a = atr(df).to_numpy(float)
    ph, pl = _pivots(h, k, "high"), _pivots(l, k, "low")
    cols = ["pat_double_top", "pat_double_bottom", "pat_head_shoulders", "pat_inv_head_shoulders",
            "pat_cup_handle", "pat_bull_flag", "pat_bear_flag", "pat_tri_sym", "pat_tri_asc", "pat_tri_desc",
            "pat_res_dist_atr", "pat_sup_dist_atr", "pat_breakout_20", "pat_breakdown_20", "pat_sr_touches"]
    out = np.zeros((n, len(cols))); out[:] = np.nan
    hi_idx, lo_idx = [], []
    hh5 = pd.Series(h).rolling(5).max().to_numpy(); ll5 = pd.Series(l).rolling(5).min().to_numpy()
    prior_hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
    prior_lo20 = pd.Series(l).rolling(20).min().shift(1).to_numpy()
    for t in range(n):
        j = t - k                              # pivot at j becomes known at t
        if j >= 0 and ph[j]: hi_idx.append(j)
        if j >= 0 and pl[j]: lo_idx.append(j)
        if t < 130:
            continue
        row = dict.fromkeys(cols, 0.0)
        px = c[t]
        H = [i for i in hi_idx if i >= t - 120]
        L = [i for i in lo_idx if i >= t - 120]
        # double top / bottom
        if len(H) >= 2:
            p1, p2 = H[-2], H[-1]
            if t - p1 <= 70 and abs(h[p1] - h[p2]) / max(h[p1], h[p2]) < 0.03:
                trough = l[p1:p2 + 1].min()
                if trough < min(h[p1], h[p2]) * 0.95:
                    row["pat_double_top"] = 1.0 if px < trough else (0.5 if px < max(h[p1], h[p2]) else 0.0)
        if len(L) >= 2:
            q1, q2 = L[-2], L[-1]
            if t - q1 <= 70 and abs(l[q1] - l[q2]) / min(l[q1], l[q2]) < 0.03:
                peak = h[q1:q2 + 1].max()
                if peak > max(l[q1], l[q2]) * 1.05:
                    row["pat_double_bottom"] = 1.0 if px > peak else (0.5 if px > min(l[q1], l[q2]) else 0.0)
        # head & shoulders (and inverse)
        if len(H) >= 3:
            s1, hd, s2 = H[-3], H[-2], H[-1]
            if h[hd] > 1.03 * max(h[s1], h[s2]) and abs(h[s1] - h[s2]) / h[hd] < 0.05:
                neck = (l[s1:hd + 1].min() + l[hd:s2 + 1].min()) / 2
                row["pat_head_shoulders"] = 1.0 if px < neck else (0.5 if px < h[s2] else 0.0)
        if len(L) >= 3:
            s1, hd, s2 = L[-3], L[-2], L[-1]
            if l[hd] < 0.97 * min(l[s1], l[s2]) and abs(l[s1] - l[s2]) / l[hd] < 0.05:
                neck = (h[s1:hd + 1].max() + h[hd:s2 + 1].max()) / 2
                row["pat_inv_head_shoulders"] = 1.0 if px > neck else (0.5 if px > l[s2] else 0.0)
        # cup and handle over the last ~120 bars
        w = c[t - 120:t + 1]
        rim_l = w[:40].max(); bottom = w[40:90].min(); right = w[90:].max()
        depth = 1 - bottom / rim_l
        if 0.12 <= depth <= 0.45 and right >= 0.95 * rim_l:
            recent_max = w[-15:].max(); pull = 1 - px / recent_max
            if 0.02 <= pull <= 0.12 and px > (rim_l + bottom) / 2:
                row["pat_cup_handle"] = 0.5
            elif px > rim_l:
                row["pat_cup_handle"] = 1.0
        # flags: strong 10-bar pole, then tight 5-bar consolidation
        pole = c[t - 5] / c[t - 15] - 1
        cons_range = (h[t - 4:t + 1].max() - l[t - 4:t + 1].min()) / c[t - 5]
        if pole > 0.12 and cons_range < 0.5 * pole and c[t] <= c[t - 5] * 1.02:
            row["pat_bull_flag"] = 1.0 if c[t] > h[t - 5:t].max() else 0.5
        if pole < -0.12 and cons_range < 0.5 * abs(pole) and c[t] >= c[t - 5] * 0.98:
            row["pat_bear_flag"] = 1.0 if c[t] < l[t - 5:t].min() else 0.5
        # triangles from the slope of rolling highs / lows over 40 bars
        xs = np.arange(40.0)
        sh = np.polyfit(xs, hh5[t - 39:t + 1], 1)[0] / px * 40
        sl = np.polyfit(xs, ll5[t - 39:t + 1], 1)[0] / px * 40
        thr = 0.03
        if sh < -thr and sl > thr: row["pat_tri_sym"] = 1.0
        elif abs(sh) <= thr / 2 and sl > thr: row["pat_tri_asc"] = 1.0
        elif sh < -thr and abs(sl) <= thr / 2: row["pat_tri_desc"] = 1.0
        # support / resistance from pivots over the past year
        Hy = [h[i] for i in hi_idx if i >= t - 250 and h[i] > px]
        Ly = [l[i] for i in lo_idx if i >= t - 250 and l[i] < px]
        atr_t = a[t] if a[t] > 0 else np.nan
        res = min(Hy) if Hy else h[max(0, t - 250):t + 1].max()
        sup = max(Ly) if Ly else l[max(0, t - 250):t + 1].min()
        row["pat_res_dist_atr"] = min((res - px) / atr_t, 20)
        row["pat_sup_dist_atr"] = min((px - sup) / atr_t, 20)
        levels = np.array([h[i] for i in hi_idx if i >= t - 250] + [l[i] for i in lo_idx if i >= t - 250])
        row["pat_sr_touches"] = float((np.abs(levels - res) / res < 0.015).sum()) if len(levels) else 0.0
        row["pat_breakout_20"] = float(px > prior_hi20[t])
        row["pat_breakdown_20"] = float(px < prior_lo20[t])
        out[t] = [row[cn] for cn in cols]
    return pd.DataFrame(out, index=df.index, columns=cols)


def support_resistance_levels(df: pd.DataFrame, k: int = 5, lookback: int = 250) -> dict:
    """Current nearest support/resistance prices, for the dashboard chart."""
    d = df.iloc[-lookback:]
    ph, pl = _pivots(d["high"].to_numpy(), k, "high"), _pivots(d["low"].to_numpy(), k, "low")
    ph[-k:] = False; pl[-k:] = False
    px = d["close"].iloc[-1]
    highs = d["high"].to_numpy()[ph]; lows = d["low"].to_numpy()[pl]
    res = sorted(x for x in highs if x > px)[:2]; sup = sorted((x for x in lows if x < px), reverse=True)[:2]
    return {"resistance": [float(x) for x in res], "support": [float(x) for x in sup]}


# --------------------------------------------------------------------------- market / macro
def market_features(prices: dict[str, pd.DataFrame], macro: pd.DataFrame) -> pd.DataFrame:
    spy = prices[config.MARKET["spx"]]["close"]
    f = pd.DataFrame(index=spy.index)
    for key, sym in config.MARKET.items():
        if sym in prices:
            c = prices[sym]["close"].reindex(f.index).ffill()
            f[f"mkt_{key}_ret5"] = c.pct_change(5, fill_method=None)
            f[f"mkt_{key}_ret21"] = c.pct_change(21, fill_method=None)
            f[f"mkt_{key}_dist200"] = c / c.rolling(200).mean() - 1
    f["mkt_breadth_proxy"] = (f.get("mkt_rut_ret21", 0) - f.get("mkt_spx_ret21", 0))
    f["mkt_spx_vol21"] = np.log(spy).diff().rolling(21).std() * np.sqrt(252)
    for key, sym in config.MACRO_MARKET.items():
        if sym not in prices:
            continue
        c = prices[sym]["close"].reindex(f.index).ffill()
        if key in ("vix", "tnx", "irx"):
            f[f"x_{key}"] = c
            f[f"x_{key}_chg5"] = c.diff(5)
            f[f"x_{key}_chg21"] = c.diff(21)
        else:
            f[f"x_{key}_ret5"] = c.pct_change(5, fill_method=None)
            f[f"x_{key}_ret21"] = c.pct_change(21, fill_method=None)
    if "x_tnx" in f and "x_irx" in f:
        f["x_curve_10y_3m"] = f["x_tnx"] - f["x_irx"]
    if "x_vix" in f:
        f["x_vix_z"] = (f["x_vix"] - f["x_vix"].rolling(252).mean()) / f["x_vix"].rolling(252).std()
    if not macro.empty:
        f = f.join(macro.reindex(f.index, method="ffill"))
    return f


def relative_features(stock: pd.DataFrame, sector: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    c = stock["close"]
    s = sector["close"].reindex(c.index).ffill(); m = market["close"].reindex(c.index).ffill()
    f = pd.DataFrame(index=c.index)
    for n in (5, 21, 63):
        f[f"rel_vs_sector_{n}d"] = c.pct_change(n, fill_method=None) - s.pct_change(n, fill_method=None)
        f[f"rel_vs_mkt_{n}d"] = c.pct_change(n, fill_method=None) - m.pct_change(n, fill_method=None)
    f["rel_sector_ret5"] = s.pct_change(5, fill_method=None)
    f["rel_sector_ret21"] = s.pct_change(21, fill_method=None)
    f["rel_sector_dist50"] = s / s.rolling(50).mean() - 1
    rs, rm = np.log(c).diff(), np.log(m).diff()
    f["rel_beta63"] = rs.rolling(63).cov(rm) / rm.rolling(63).var()
    f["rel_corr63"] = rs.rolling(63).corr(rm)
    return f


def earnings_features(index: pd.DatetimeIndex, dates: list[pd.Timestamp]) -> pd.DataFrame:
    f = pd.DataFrame(index=index)
    if not dates:
        f["earn_days_since"] = np.nan; f["earn_days_to"] = np.nan; f["earn_in_5d"] = np.nan; f["earn_in_21d"] = np.nan
        return f
    d = np.array(sorted(dates), dtype="datetime64[ns]")
    ix = index.to_numpy()
    pos = np.searchsorted(d, ix, side="right")
    prev = np.where(pos > 0, d[np.clip(pos - 1, 0, len(d) - 1)], np.datetime64("NaT"))
    nxt = np.where(pos < len(d), d[np.clip(pos, 0, len(d) - 1)], np.datetime64("NaT"))
    since = (ix - prev).astype("timedelta64[D]").astype(float)
    to = (nxt - ix).astype("timedelta64[D]").astype(float)
    f["earn_days_since"] = np.clip(since, 0, 120)
    f["earn_days_to"] = np.clip(to, 0, 120)
    f["earn_in_5d"] = (to <= 7).astype(float)
    f["earn_in_21d"] = (to <= 30).astype(float)
    return f


# --------------------------------------------------------------------------- targets
def targets(close: pd.Series) -> pd.DataFrame:
    t = pd.DataFrame(index=close.index)
    for name, h in config.HORIZONS.items():
        fwd = close.shift(-h) / close - 1
        t[f"y_ret_{name}"] = fwd
        t[f"y_up_{name}"] = (fwd > 0).astype(float).where(fwd.notna())
        fmax = pd.concat([close.shift(-i) for i in range(1, h + 1)], axis=1).max(axis=1) / close - 1
        fmax = fmax.where(close.shift(-h).notna())
        for thr in config.GAIN_THRESHOLDS:
            t[f"y_gain{int(thr * 100)}_{name}"] = (fmax > thr).astype(float).where(fmax.notna())
    return t


def build_panel(prices: dict[str, pd.DataFrame], macro: pd.DataFrame,
                earnings: dict[str, list], tickers: list[str]) -> tuple[pd.DataFrame, dict]:
    """Stacked (date, ticker) panel of features + targets for all tickers."""
    mkt = market_features(prices, macro)
    frames, extras = [], {}
    for t in tickers:
        if t not in prices:
            continue
        df = prices[t]
        sec = prices.get(config.SECTOR_MAP.get(t, config.DEFAULT_SECTOR), prices[config.MARKET["spx"]])
        f = pd.concat([technical_features(df), pattern_features(df),
                       relative_features(df, sec, prices[config.MARKET["spx"]]),
                       earnings_features(df.index, earnings.get(t, []))], axis=1)
        f = f.join(mkt, how="left")
        f = f.join(targets(df["close"])).copy()
        f["ticker"] = t
        f["close"] = df["close"]
        frames.append(f.iloc[200:])     # drop warm-up rows
        extras[t] = {"sr": support_resistance_levels(df)}
    panel = pd.concat(frames).reset_index(names="date").sort_values(["date", "ticker"]).reset_index(drop=True)
    panel = panel.replace([np.inf, -np.inf], np.nan)
    return panel, extras


def feature_columns(panel: pd.DataFrame) -> list[str]:
    return [c for c in panel.columns if any(c.startswith(p) for p in FAMILY_PREFIX)]
