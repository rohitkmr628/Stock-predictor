"""Human-readable names and value formatting for features."""
from __future__ import annotations

import math

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
PCT_FEATS = ("_ret", "dist_", "rel_", "_vol", "atr_pct", "52w", "slope", "gap", "mom_", "max_dd", "spx_dd", "small_vs", "growth_vs", "risk_on")


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
             "earn_days_since": "Days since earnings", "earn_in_5d": "Earnings within a week",
             "tech_mom_12_1": "12-1 month momentum", "tech_mom_6_1": "6-1 month momentum", "tech_sharpe_126": "6-month Sharpe",
             "tech_max_dd_126": "Drawdown from 6-month high", "rel_downside_beta": "Downside beta",
             "rel_vs_sector_126d": "6-month return vs sector", "rel_vs_mkt_126d": "6-month return vs S&P 500",
             "regime_bull": "Bull-market regime", "regime_bear": "Bear-market regime", "regime_spx_dd": "S&P 500 drawdown",
             "regime_vol_pct": "Market volatility percentile", "regime_highvol": "High-volatility regime",
             "breadth_above50": "Stocks above 50-day MA", "breadth_above200": "Stocks above 200-day MA",
             "breadth_up21": "Stocks up over 1 month", "breadth_new_high_share": "Stocks at 52-week highs",
             "breadth_vix_term": "VIX vs its 3-month average", "sect_rank63": "Sector strength rank (3m)",
             "sect_risk_on": "Cyclicals vs defensives", "fund_last_surprise": "Last EPS surprise",
             "fund_surprise_avg4": "Avg EPS surprise (4 qtrs)", "fund_beat_streak": "EPS beat streak",
             "macro_sahm": "Sahm recession indicator", "macro_cpi_3m_ann": "CPI 3-month annualised",
             "macro_indpro_yoy": "Industrial production YoY", "mkt_small_vs_large21": "Small vs large caps (1m)",
             "mkt_growth_vs_blend21": "Nasdaq vs S&P 500 (1m)", "xs_tech_mom_12_1": "Momentum rank in universe",
             "xs_tech_ret_21d": "1-month return rank", "xs_rel_vs_mkt_63d": "Relative strength rank",
             "xs_tech_vol_63d": "Volatility rank", "xs_fund_last_surprise": "Earnings surprise rank"}
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
    if f.startswith(("xs_", "sect_rank", "breadth_above", "breadth_up", "breadth_new", "regime_vol_pct")):
        return f"rank {v * 100:.0f}/100" if f.startswith(("xs_", "sect_rank", "regime_vol")) else f"{v * 100:.0f}%"
    if f.startswith("fund_last") or f.startswith("fund_surprise"):
        return f"{v:+.1f}%"
    if f in ("regime_bull", "regime_bear", "regime_highvol"):
        return "yes" if v >= 1 else "no"
    if f.startswith(("x_vix", "tech_vol_z", "tech_obv", "tech_cmf", "tech_updown", "rel_beta", "rel_corr", "ts_ar1", "ts_drift")) or f.endswith("_r2"):
        return f"{v:.2f}"
    if any(k in f for k in PCT_FEATS) or "dist" in f or "_ret" in f or f.startswith("mkt_") or "vol" in f:
        return f"{v * 100:+.1f}%"
    return f"{v:.2f}"


