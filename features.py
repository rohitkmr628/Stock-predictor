"""Feature engineering: technical indicators, chart patterns, relative strength, market and macro.
Every feature at date t uses only information available at the close of t (no look-ahead)."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import config

# Feature families, used to group importance and explanations.
FAMILY_PREFIX = {
    "xs_": "Cross-sectional rank",
    "tech_": "Technical indicators",
    "pat_": "Chart patterns",
    "rel_": "Sector & relative strength",
    "mkt_": "Market & index trend",
    "x_": "Rates, volatility & commodities",
    "macro_": "Macroeconomic",
    "earn_": "Earnings calendar",
    "ts_": "Time-series forecast",
    "regime_": "Market regime",
    "breadth_": "Market breadth & sentiment",
    "sect_": "Sector rotation",
    "fund_": "Earnings results",
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


# --------------------------------------------------------------------------- market / macro / regime
def market_features(prices: dict[str, pd.DataFrame], macro: pd.DataFrame, universe: list[str]) -> pd.DataFrame:
    spy = prices[config.MARKET["spx"]]["close"]
    f = pd.DataFrame(index=spy.index)
    for key, sym in config.MARKET.items():
        if sym in prices:
            c = prices[sym]["close"].reindex(f.index).ffill()
            f[f"mkt_{key}_ret5"] = c.pct_change(5, fill_method=None)
            f[f"mkt_{key}_ret21"] = c.pct_change(21, fill_method=None)
            f[f"mkt_{key}_dist200"] = c / c.rolling(200).mean() - 1
    f["mkt_small_vs_large21"] = f.get("mkt_rut_ret21", 0) - f.get("mkt_spx_ret21", 0)
    f["mkt_growth_vs_blend21"] = f.get("mkt_ndx_ret21", 0) - f.get("mkt_spx_ret21", 0)
    lr = np.log(spy).diff()
    f["mkt_spx_vol21"] = lr.rolling(21).std() * np.sqrt(252)
    for key, sym in config.MACRO_MARKET.items():
        if sym not in prices:
            continue
        c = prices[sym]["close"].reindex(f.index).ffill()
        if key in ("vix", "tnx", "irx"):
            f[f"x_{key}"] = c; f[f"x_{key}_chg5"] = c.diff(5); f[f"x_{key}_chg21"] = c.diff(21)
        else:
            f[f"x_{key}_ret5"] = c.pct_change(5, fill_method=None); f[f"x_{key}_ret21"] = c.pct_change(21, fill_method=None)
    if "x_tnx" in f and "x_irx" in f:
        f["x_curve_10y_3m"] = f["x_tnx"] - f["x_irx"]
    if "x_vix" in f:
        f["x_vix_z"] = (f["x_vix"] - f["x_vix"].rolling(252).mean()) / f["x_vix"].rolling(252).std()
        f["breadth_vix_term"] = f["x_vix"] / f["x_vix"].rolling(63).mean()
    # ---- market regime (rule-based, point-in-time)
    dd = spy / spy.rolling(252, min_periods=60).max() - 1
    r126 = spy.pct_change(126, fill_method=None)
    above200 = spy > spy.rolling(200).mean()
    volpct = f["mkt_spx_vol21"].rolling(756, min_periods=252).rank(pct=True)
    f["regime_bull"] = (above200 & (r126 > 0)).astype(float)
    f["regime_bear"] = ((~above200) & ((r126 < -0.05) | (dd < -0.15))).astype(float)
    f["regime_spx_dd"] = dd
    f["regime_vol_pct"] = volpct
    f["regime_highvol"] = ((volpct > 0.8) | (f.get("x_vix", pd.Series(0, index=f.index)) > 25)).astype(float)
    # ---- breadth across the universe (share of stocks in uptrends)
    closes = pd.DataFrame({t: prices[t]["close"] for t in universe if t in prices}).reindex(f.index)
    if closes.shape[1] >= 5:
        f["breadth_above50"] = (closes > closes.rolling(50).mean()).sum(axis=1) / closes.notna().sum(axis=1)
        f["breadth_above200"] = (closes > closes.rolling(200).mean()).sum(axis=1) / closes.notna().sum(axis=1)
        f["breadth_up21"] = (closes.pct_change(21, fill_method=None) > 0).sum(axis=1) / closes.notna().sum(axis=1)
        f["breadth_new_high_share"] = (closes >= closes.rolling(252, min_periods=120).max()).sum(axis=1) / closes.notna().sum(axis=1)
    # ---- sector rotation: each SPDR sector's 3-month return vs S&P, ranked
    sect = {}
    for name, etf in config.SECTOR_ETF.items():
        if etf in prices:
            sect[etf] = prices[etf]["close"].reindex(f.index).ffill().pct_change(63, fill_method=None) - spy.pct_change(63, fill_method=None)
    sect_df = pd.DataFrame(sect)
    defensive = [e for e in ("XLP", "XLU", "XLV") if e in sect_df]
    cyclical = [e for e in ("XLK", "XLY", "XLI", "XLF") if e in sect_df]
    if defensive and cyclical:
        f["sect_risk_on"] = sect_df[cyclical].mean(axis=1) - sect_df[defensive].mean(axis=1)
    if not macro.empty:
        f = f.join(macro.reindex(f.index, method="ffill"))
    labels = pd.DataFrame(index=f.index)
    labels["regime"] = np.where(f["regime_bull"] == 1, "Bull", np.where(f["regime_bear"] == 1, "Bear", "Sideways"))
    labels["vol_regime"] = np.where(f["regime_highvol"] == 1, "High volatility", "Normal volatility")
    downturn = (dd < -0.2)
    if "macro_sahm" in f:
        downturn |= f["macro_sahm"] >= 0.5
    if "macro_gdp_yoy" in f:
        downturn |= f["macro_gdp_yoy"] < 0
    labels["downturn"] = downturn.fillna(False)
    return f, sect_df.rank(axis=1, pct=True), labels


def relative_features(stock: pd.DataFrame, sector: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    c = stock["close"]
    s = sector["close"].reindex(c.index).ffill(); m = market["close"].reindex(c.index).ffill()
    f = pd.DataFrame(index=c.index)
    for n in (5, 21, 63, 126):
        f[f"rel_vs_sector_{n}d"] = c.pct_change(n, fill_method=None) - s.pct_change(n, fill_method=None)
        f[f"rel_vs_mkt_{n}d"] = c.pct_change(n, fill_method=None) - m.pct_change(n, fill_method=None)
    f["rel_sector_ret5"] = s.pct_change(5, fill_method=None)
    f["rel_sector_ret21"] = s.pct_change(21, fill_method=None)
    f["rel_sector_dist50"] = s / s.rolling(50).mean() - 1
    rs, rm = np.log(c).diff(), np.log(m).diff()
    f["rel_beta63"] = rs.rolling(63).cov(rm) / rm.rolling(63).var()
    f["rel_corr63"] = rs.rolling(63).corr(rm)
    f["rel_downside_beta"] = rs.where(rm < 0).rolling(126, min_periods=40).cov(rm.where(rm < 0)) / rm.where(rm < 0).rolling(126, min_periods=40).var()
    return f


def earnings_features(index: pd.DatetimeIndex, events: list[dict]) -> tuple[pd.DataFrame, pd.Series]:
    """Days to/since earnings and the last reported EPS surprises (only after the report date)."""
    f = pd.DataFrame(index=index)
    cols = ["earn_days_since", "earn_days_to", "earn_in_5d", "earn_in_21d", "fund_last_surprise", "fund_surprise_avg4", "fund_beat_streak"]
    if not events:
        for c in cols:
            f[c] = np.nan
        return f, pd.Series(False, index=index)
    ev = pd.DataFrame(events)
    ev["date"] = pd.to_datetime(ev["date"]); ev = ev.sort_values("date").drop_duplicates("date")
    d = ev["date"].to_numpy(dtype="datetime64[ns]"); ix = index.to_numpy()
    pos = np.searchsorted(d, ix, side="right")
    prev = np.where(pos > 0, d[np.clip(pos - 1, 0, len(d) - 1)], np.datetime64("NaT"))
    nxt = np.where(pos < len(d), d[np.clip(pos, 0, len(d) - 1)], np.datetime64("NaT"))
    since = (ix - prev).astype("timedelta64[D]").astype(float); to = (nxt - ix).astype("timedelta64[D]").astype(float)
    f["earn_days_since"] = np.clip(since, 0, 120); f["earn_days_to"] = np.clip(to, 0, 120)
    f["earn_in_5d"] = (to <= 7).astype(float); f["earn_in_21d"] = (to <= 30).astype(float)
    rep = ev.dropna(subset=["surprise"]).set_index("date")["surprise"].clip(-100, 100)
    if len(rep):
        s = rep.reindex(index.union(rep.index)).ffill().reindex(index)
        f["fund_last_surprise"] = s
        f["fund_surprise_avg4"] = rep.rolling(4, min_periods=1).mean().reindex(index.union(rep.index)).ffill().reindex(index)
        streak = (rep > 0).astype(int); streak = streak.groupby((streak != streak.shift()).cumsum()).cumsum() * np.where(rep > 0, 1, -1)
        f["fund_beat_streak"] = pd.Series(streak.values, rep.index).reindex(index.union(rep.index)).ffill().reindex(index)
        f.loc[f["earn_days_since"] > 100, ["fund_last_surprise"]] = np.nan   # stale
    else:
        f["fund_last_surprise"] = np.nan; f["fund_surprise_avg4"] = np.nan; f["fund_beat_streak"] = np.nan
    season = pd.Series(since <= 10, index=index)
    return f, season


def extra_momentum(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]; f = pd.DataFrame(index=df.index)
    f["tech_mom_12_1"] = c.shift(21) / c.shift(252) - 1
    f["tech_mom_6_1"] = c.shift(21) / c.shift(126) - 1
    lr = np.log(c).diff()
    f["tech_sharpe_126"] = lr.rolling(126).mean() / lr.rolling(126).std() * np.sqrt(252)
    f["tech_max_dd_126"] = c / c.rolling(126).max() - 1
    return f


# --------------------------------------------------------------------------- targets
def targets(close: pd.Series) -> pd.DataFrame:
    t = pd.DataFrame(index=close.index)
    for name, h in config.HORIZONS.items():
        fwd = close.shift(-h) / close - 1
        t[f"y_ret_{name}"] = fwd
        t[f"y_up_{name}"] = (fwd > 0).astype(float).where(fwd.notna())
        fmax = pd.concat([close.shift(-i) for i in range(1, h + 1)], axis=1).max(axis=1) / close - 1
        t[f"y_maxret_{name}"] = fmax.where(fwd.notna())
    return t


# --------------------------------------------------------------------------- panel
def sector_etf_for(t: str, fund: dict) -> tuple[str, str]:
    """(SPDR sector ETF, relative-strength ETF) for a ticker."""
    sec = (fund.get(t) or {}).get("sector")
    spdr = config.SECTOR_ETF.get(sec, config.DEFAULT_SECTOR)
    return spdr, config.INDUSTRY_ETF_OVERRIDE.get(t, spdr)


def _stock_block(args):
    t, df, sec_df, mkt_df, events = args
    tf = technical_features(df)
    pf = pattern_features(df)
    mf = extra_momentum(df)
    rf = relative_features(df, sec_df, mkt_df)
    ef, season = earnings_features(df.index, events)
    out = pd.concat([tf, pf, mf, rf, ef, targets(df["close"])], axis=1)
    out["earn_season"] = season.values
    return t, out, support_resistance_levels(df)


def build_panel(prices, macro, earnings, fund, tickers) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    from concurrent.futures import ProcessPoolExecutor
    mkt, sect_rank, labels = market_features(prices, macro, tickers)
    spx = prices[config.MARKET["spx"]]
    jobs = []
    for t in tickers:
        if t not in prices:
            continue
        spdr, rel_etf = sector_etf_for(t, fund)
        jobs.append((t, prices[t], prices.get(rel_etf, spx), spx, earnings.get(t, [])))
    frames, extras = [], {}
    workers = os.cpu_count() if config.N_JOBS == -1 else config.N_JOBS
    with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
        for t, f, sr in ex.map(_stock_block, jobs, chunksize=4):
            spdr, _ = sector_etf_for(t, fund)
            if spdr in sect_rank:
                f["sect_rank63"] = sect_rank[spdr].reindex(f.index)
            f = f.join(mkt, how="left").join(labels, how="left")
            f["ticker"] = t; f["close"] = prices[t]["close"]
            frames.append(f.iloc[252:].copy())
            extras[t] = {"sr": sr}
    panel = pd.concat(frames).reset_index(names="date").sort_values(["date", "ticker"]).reset_index(drop=True)
    panel = panel.replace([np.inf, -np.inf], np.nan)
    # relative (cross-sectional) targets: did the stock beat the average stock in the universe?
    for name in config.HORIZONS:
        r = panel[f"y_ret_{name}"]
        panel[f"y_xup_{name}"] = (r > panel.groupby("date")[f"y_ret_{name}"].transform("mean")).astype(float).where(r.notna())
    # cross-sectional ranks (point-in-time: computed within each date)
    for c in ("tech_mom_12_1", "tech_ret_21d", "rel_vs_mkt_63d", "tech_vol_63d", "fund_last_surprise"):
        if c in panel:
            panel[f"xs_{c}"] = panel.groupby("date")[c].rank(pct=True)
    return panel, extras, mkt


def feature_columns(panel: pd.DataFrame) -> list[str]:
    pre = tuple(FAMILY_PREFIX) + ("xs_",)
    return [c for c in panel.columns if c.startswith(pre)]
