"""Dynamic ensemble, walk-forward backtest across market cycles, and the saved model state.

Components (each sees one family of evidence):
  technical      gradient-boosted trees on indicators, chart patterns, momentum
  relative       gradient-boosted trees on sector / relative strength / sector rotation
  macro_regime   gradient-boosted trees on index trend, regime, breadth, rates, macro
  earnings       logistic regression on earnings surprises and calendar
  time_series    logistic regression on autocorrelation, drift and EWMA volatility (AR-style)
  all_linear     heavily regularised logistic regression on every feature

Ensemble: each component's weight = its out-of-sample log-loss skill over the previous ~2 years.
Components with no skill get weight 0 (switched off). The blend is then isotonic-calibrated on
earlier out-of-sample results. Magnitude comes from an EWMA volatility forecast whose band width
is calibrated to hold 80% of outcomes; the median move is consistent with the probability.
"""
from __future__ import annotations

import json
import math
import os
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import config
from features import family_of

warnings.filterwarnings("ignore")

# target "rel": predicts whether the stock beats the average stock (stock selection);
# target "abs": predicts the direction of the stock itself, driven by the market (market timing).
COMPONENTS = {
    "technical": {"label": "Technical & chart patterns", "prefixes": ("tech_", "pat_", "xs_tech"), "kind": "hgb", "target": "rel"},
    "relative": {"label": "Sector & relative strength", "prefixes": ("rel_", "sect_", "xs_rel"), "kind": "hgb", "target": "rel"},
    "earnings": {"label": "Earnings results & calendar", "prefixes": ("earn_", "fund_", "xs_fund"), "kind": "lr", "target": "rel"},
    "time_series": {"label": "Time-series (AR / drift / EWMA vol)", "prefixes": ("ts_", "tech_ret_1d", "tech_ret_5d", "tech_vol_"), "kind": "lr", "target": "rel"},
    "all_linear": {"label": "All stock factors (linear)", "prefixes": ("tech_", "pat_", "rel_", "sect_", "earn_", "fund_", "ts_", "xs_"), "kind": "lr", "target": "rel"},
    "macro_regime": {"label": "Market timing: regime, breadth & macro", "prefixes": ("mkt_", "x_", "macro_", "regime_", "breadth_"), "kind": "hgb", "target": "abs"},
}
# Setups are defined by where a stock's probability ranks within the universe on that day,
# because the ensemble's skill is mostly in ordering stocks against each other.
RANK_BUCKETS = [(0.0, 0.10, "Bottom 10% (strong bearish)"), (0.10, 0.25, "Bottom 25% (bearish)"),
                (0.25, 0.75, "Middle (no edge)"), (0.75, 0.90, "Top 25% (bullish)"), (0.90, 1.01, "Top 10% (strong bullish)")]


def _hgb():
    return HistGradientBoostingClassifier(max_iter=120, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=500,
                                          l2_regularization=3.0, max_features=0.6, random_state=0)


def _lr(C=0.05):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=C, max_iter=600))


def component_features(feats: list[str]) -> dict[str, list[str]]:
    out = {}
    for k, c in COMPONENTS.items():
        cols = feats if c["prefixes"] is None else [f for f in feats if f.startswith(c["prefixes"])]
        if cols:
            out[k] = cols
    return out


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def sigm(x):
    return 1 / (1 + np.exp(-x))


def _ll(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def sample_rows(df: pd.DataFrame, every: int) -> pd.DataFrame:
    if every <= 1:
        return df
    codes = pd.factorize(df["date"], sort=True)[0]
    return df[codes % every == 0]


# --------------------------------------------------------------------------- component fitting
def fit_components(tr: pd.DataFrame, comp_cols: dict, ycol: str) -> dict:
    """ycol is the absolute target (y_up_h); relative components use y_xup_h instead."""
    xcol = ycol.replace("y_up_", "y_xup_")
    models = {}
    for k, cols in comp_cols.items():
        y = tr[xcol if COMPONENTS[k]["target"] == "rel" else ycol].to_numpy()
        ok = ~np.isnan(y)
        if COMPONENTS[k]["target"] == "abs":
            # market-level features repeat for every stock on a date: fit on one row per date
            d = tr.loc[ok].groupby("date").head(1)
            X, yy = d[cols], d[ycol].to_numpy()
            mdl = HistGradientBoostingClassifier(max_iter=80, learning_rate=0.05, max_leaf_nodes=7, min_samples_leaf=60,
                                                 l2_regularization=3.0, random_state=0)
        else:
            X, yy = tr.loc[ok, cols], y[ok]
            mdl = _hgb() if COMPONENTS[k]["kind"] == "hgb" else _lr(0.02 if k == "all_linear" else 0.1)
        mdl.fit(X, yy)
        models[k] = mdl
    return models


def predict_components(models: dict, df: pd.DataFrame, comp_cols: dict) -> pd.DataFrame:
    return pd.DataFrame({k: m.predict_proba(df[comp_cols[k]])[:, 1] for k, m in models.items()}, index=df.index)


def ranking_auc(df: pd.DataFrame, col: str, ycol: str = "y") -> float:
    """Average within-date AUC: how well the signal ranks stocks against each other on the same day."""
    vals = []
    for _, g in df.groupby("date"):
        yy = g[ycol].to_numpy()
        if 0 < yy.sum() < len(yy) and len(yy) >= 8:
            vals.append(roc_auc_score(yy, g[col].to_numpy()))
    return float(np.mean(vals)) if vals else 0.5


def market_auc(df: pd.DataFrame, col: str) -> float:
    d = df.groupby("date").agg(p=(col, "first"), y=("mret", "first"))
    y = (d["y"] > 0).astype(int)
    return float(roc_auc_score(y, d["p"])) if y.nunique() > 1 else 0.5


MIN_EDGE_AUC = 0.505   # a component must beat this out of sample to receive any weight


def _thin(df, max_rows=60000):
    if len(df) <= max_rows:
        return df
    step = int(np.ceil(len(df) / max_rows))
    return df[df["date"].isin(np.sort(df["date"].unique())[::step])]


def component_weights(recent: pd.DataFrame, comps: list[str], history: pd.DataFrame | None = None) -> tuple[dict, dict]:
    """Stock-selection components are weighted by out-of-sample ranking AUC above MIN_EDGE_AUC; the
    market-timing component by its AUC on market direction (with a much higher bar, since there is only
    one market path to learn from). The score used is the WORSE of the recent (~2y) and full-history AUC,
    so a signal must work consistently to keep its weight; below the bar it is switched off."""
    perf, w = {}, {}
    rs = _thin(recent); hs = _thin(history) if history is not None and len(history) > len(recent) else None
    for k in comps:
        f = market_auc if COMPONENTS[k]["target"] == "abs" else (lambda d, c: ranking_auc(d, c, "yx"))
        a_recent = f(rs, k); a_all = f(hs, k) if hs is not None else a_recent
        auc = min(a_recent, a_all)
        perf[k] = {"auc": a_recent, "auc_all": a_all, "skill": auc - 0.5}
        if COMPONENTS[k]["target"] == "abs":
            w[k] = float(np.clip((auc - 0.53) / 0.07, 0, 1) * 0.5)
        else:
            w[k] = max(auc - MIN_EDGE_AUC, 0.0)
    stock = [k for k in comps if COMPONENTS[k]["target"] == "rel"]
    tot = sum(w[k] for k in stock)
    out = {k: (w[k] / tot if tot > 0 else 0.0) for k in stock}
    for k in comps:
        if COMPONENTS[k]["target"] == "abs":
            out[k] = w[k]                            # market component is additive, not normalised
    return out, perf


def blend(comp_preds: pd.DataFrame, weights: dict, base: float, mkt_base: float | None = None) -> np.ndarray:
    """log-odds(base) + weighted stock-selection deviations (vs 0.5) + market-timing deviation (vs its base)."""
    lb = logit(base)
    dev = np.zeros(len(comp_preds))
    for k, w in weights.items():
        if w <= 0 or k not in comp_preds:
            continue
        p = comp_preds[k].to_numpy()
        if COMPONENTS[k]["target"] == "rel":
            dev += w * (logit(p) - 0.0)
        else:
            dev += w * (logit(p) - logit(mkt_base if mkt_base is not None else base))
    return sigm(lb + dev)


def fit_calibrator(raw: np.ndarray, y: np.ndarray):
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.03, y_max=0.97).fit(raw, y)
    return iso


def band_multiplier(ret, mu_unit, sigma):
    """c such that |ret - c*sigma*mu_unit| <= 1.2816*c*sigma holds BAND_COVERAGE of the time (grid search)."""
    best, err = 1.0, 9
    for c in np.arange(0.5, 3.01, 0.05):
        cov = np.mean(np.abs(ret - c * sigma * mu_unit) <= norm.ppf(0.5 + config.BAND_COVERAGE / 2) * c * sigma)
        if abs(cov - config.BAND_COVERAGE) < err:
            best, err = c, abs(cov - config.BAND_COVERAGE)
    return float(best)


def horizon_sigma(df: pd.DataFrame, h: int) -> np.ndarray:
    v = df["ts_ewma_vol"].fillna(df["tech_vol_63d"]).fillna(0.3).to_numpy()
    return np.clip(v, 0.05, 3) * math.sqrt(h / 252)


def move_from_prob(p, sigma, c):
    return c * sigma * norm.ppf(np.clip(p, 0.01, 0.99))


def prob_max_above(mu, s, thr):
    """P(max over the horizon >= +thr) for Brownian motion with drift mu and vol s (log terms)."""
    a = math.log(1 + thr)
    s = np.maximum(s, 1e-6)
    t1 = norm.cdf((mu - a) / s)
    t2 = np.exp(np.clip(2 * mu * a / s ** 2, -50, 50)) * norm.cdf((-a - mu) / s)
    return np.clip(t1 + t2, 0, 1)


def rank_bucket(rank: float) -> str:
    for lo, hi, name in RANK_BUCKETS:
        if lo <= rank < hi:
            return name
    return "Middle (no edge)"


def direction(bucket: str) -> int:
    return 1 if "bullish" in bucket else -1 if "bearish" in bucket else 0


def setup_table(df: pd.DataFrame) -> dict:
    """Historical accuracy of similar predictions, keyed by regime|bucket and by bucket alone."""
    if df.empty:
        return {}
    d = df.assign(bucket=[rank_bucket(r) for r in df["rank"]])
    out = {}
    for keys, g in list(d.groupby(["regime", "bucket"])) + [(("All", b), g) for b, g in d.groupby("bucket")]:
        reg, b = keys
        bull = direction(b) > 0
        bear = direction(b) < 0
        if bull:
            hit = g["y"].mean(); side_base = g["base"].mean()
        elif bear:
            hit = 1 - g["y"].mean(); side_base = 1 - g["base"].mean()
        else:
            hit = g["y"].mean(); side_base = g["base"].mean()
        out[f"{reg}|{b}"] = {"n": int(len(g)), "hit": float(hit), "side_base": float(side_base),
                             "edge": float(hit - side_base), "avg_ret": float(g["ret"].mean())}
    return out


def lookup_setup(table: dict, regime: str, bucket: str) -> dict | None:
    r = table.get(f"{regime}|{bucket}")
    if r and r["n"] >= config.CONFIDENCE["medium"]["min_n"]:
        return {**r, "scope": regime}
    r = table.get(f"All|{bucket}")
    return {**r, "scope": "All regimes"} if r else None


def confidence(edge: float, bucket: str, setup: dict | None) -> str:
    """High/Medium only when (1) the stock sits in a top/bottom bucket, (2) its probability is on the
    same side of the base rate, and (3) similar past calls beat their base rate by enough, often enough."""
    d = direction(bucket)
    if setup is None or d == 0 or np.sign(edge) != d:
        return "Low"
    for lvl in ("high", "medium"):
        c = config.CONFIDENCE[lvl]
        strong_ok = ("10%" in bucket) or lvl == "medium"
        if strong_ok and abs(edge) >= c["min_edge"] and setup["edge"] >= c["setup_edge"] and setup["n"] >= c["min_n"]:
            return lvl.capitalize()
    return "Low"


# --------------------------------------------------------------------------- walk-forward backtest
def walk_forward(panel: pd.DataFrame, feats: list[str], log=print) -> dict:
    comp_cols = component_features(feats)
    dates = np.sort(panel["date"].unique())
    date_pos = {d: i for i, d in enumerate(dates)}
    panel = panel.assign(_pos=panel["date"].map(date_pos))
    start = int(252 * config.BACKTEST_MIN_TRAIN_YEARS)
    results = {}
    for name, h in config.HORIZONS.items():
        ycol, rcol = f"y_up_{name}", f"y_ret_{name}"
        lab = panel[panel[ycol].notna()]
        blocks = []
        for b0 in range(start, len(dates), config.RETRAIN_EVERY):
            b1 = min(b0 + config.RETRAIN_EVERY, len(dates))
            tr = sample_rows(lab[lab["_pos"] <= b0 - h - 1], config.TRAIN_SAMPLE_EVERY)
            te = lab[(lab["_pos"] >= b0) & (lab["_pos"] < b1)]
            if len(tr) < 3000 or te.empty:
                continue
            models = fit_components(tr, comp_cols, ycol)
            cp = predict_components(models, te, comp_cols)
            cp["y"] = te[ycol].to_numpy(); cp["ret"] = te[rcol].to_numpy(); cp["maxret"] = te[f"y_maxret_{name}"].to_numpy()
            cp["yx"] = te[f"y_xup_{name}"].to_numpy()
            cp["mret"] = te.groupby("date")[rcol].transform("mean").to_numpy()
            cp["base_train"] = float(tr[ycol].mean())
            cp["mkt_base"] = float((tr.groupby("date")[rcol].mean() > 0).mean())
            for c in ("date", "ticker", "_pos", "regime", "vol_regime", "downturn", "earn_season"):
                cp[c] = te[c].to_numpy()
            cp["sigma"] = horizon_sigma(te, h)
            cp["block"] = len(blocks)
            blocks.append(cp)
        if not blocks:
            continue
        oos = pd.concat(blocks, ignore_index=True)
        # point-in-time ensemble: weights, calibration, band and setup tables use only outcomes known before each block
        weights_hist, perf_hist = [], []
        conf = np.empty(len(oos), dtype=object); band_c = np.empty(len(oos))
        for bi in sorted(oos["block"].unique()):
            cur = oos["block"] == bi
            b_start = oos.loc[cur, "_pos"].min()
            prior = oos[(oos["block"] < bi) & (oos["_pos"] <= b_start - h - 1)]
            prior = prior[prior["block"] >= bi - config.WEIGHT_LOOKBACK_BLOCKS]
            base = float(oos.loc[cur, "base_train"].iloc[0])
            mkt_base = float(oos.loc[cur, "mkt_base"].iloc[0])
            if len(prior) >= 2000:
                hist = oos[(oos["block"] < bi) & (oos["_pos"] <= b_start - h - 1)]
                w, perf = component_weights(prior, list(comp_cols), hist)
            else:   # no track record yet: small equal weights on stock selection, no market timing
                stock = [k for k in comp_cols if COMPONENTS[k]["target"] == "rel"]
                w, perf = {k: (0.5 / len(stock) if k in stock else 0.0) for k in comp_cols}, {}
            weights_hist.append({"block": int(bi), "start": str(pd.Timestamp(oos.loc[cur, "date"].min()).date()), **w})
            perf_hist.append(perf)
            raw_cur = blend(oos.loc[cur, list(comp_cols)], w, base, mkt_base)
            all_prior = oos[(oos["block"] < bi) & (oos["_pos"] <= b_start - h - 1)]
            if sum(w.values()) <= 0:
                p, c, table = np.full(cur.sum(), base), 1.0, {}
                if len(all_prior) >= 4000 and "p" in oos:
                    c = band_multiplier(all_prior["ret"].to_numpy(), norm.ppf(np.clip(oos.loc[all_prior.index, "p"].to_numpy(), .01, .99)), all_prior["sigma"].to_numpy())
            elif len(all_prior) >= 4000 and "raw" in oos:
                iso = fit_calibrator(oos.loc[all_prior.index, "raw"].to_numpy(), all_prior["y"].to_numpy())
                p = np.clip(base + iso.predict(raw_cur) - iso.predict(np.array([base]))[0], 0.02, 0.98)
                c = band_multiplier(all_prior["ret"].to_numpy(), norm.ppf(np.clip(oos.loc[all_prior.index, "p"].to_numpy(), .01, .99)), all_prior["sigma"].to_numpy())
                table = setup_table(oos.loc[all_prior.index].assign(base=all_prior["base_train"]))
            else:
                p = base + (raw_cur - base) * 0.3
                c, table = 1.0, {}
            oos.loc[cur, "raw"] = raw_cur
            oos.loc[cur, "p"] = p
            oos.loc[cur, "rank"] = oos.loc[cur].groupby("date")["p"].rank(pct=True, method="average").to_numpy()
            band_c[cur.to_numpy()] = c
            edges = p - base
            regs = oos.loc[cur, "regime"].to_numpy(); rks = oos.loc[cur, "rank"].to_numpy()
            conf[cur.to_numpy()] = [confidence(e, rank_bucket(k), lookup_setup(table, r, rank_bucket(k))) for e, r, k in zip(edges, regs, rks)]
        oos["conf"] = conf; oos["band_c"] = band_c; oos["base"] = oos["base_train"]
        results[name] = {"oos": oos, "weights_hist": weights_hist, "h": h, "comp_cols": comp_cols}
        m = horizon_metrics(oos)
        log(f"  backtest {name}: AUC {m['auc']:.3f}  rank-AUC {m['ranking_auc']:.3f}  acc {m['accuracy']:.3f} (naive {m['naive_accuracy']:.3f})  "
            f"published {m['published_share']:.0%} @ {m['published_accuracy'] if m['published_accuracy'] == m['published_accuracy'] else 0:.3f}")
    return results


# --------------------------------------------------------------------------- metrics
def _cls_metrics(g: pd.DataFrame) -> dict:
    y, p, base = g["y"].to_numpy(), g["p"].to_numpy(), g["base"].to_numpy()
    call_up = p > base
    n = len(g)
    if n == 0:
        return {"n": 0}
    acc = float(np.mean(call_up == (y == 1)))
    tp = np.sum(call_up & (y == 1)); fp = np.sum(call_up & (y == 0)); fn = np.sum(~call_up & (y == 1))
    br = float(np.mean((p - y) ** 2)); br0 = float(np.mean((y.mean() - y) ** 2))
    pub = g["conf"].isin(["High", "Medium"]).to_numpy()
    pub_acc = float(np.mean(call_up[pub] == (y[pub] == 1))) if pub.any() else float("nan")
    rank_auc = ranking_auc(g, "p") if g["date"].nunique() <= 4000 else float("nan")
    return {"n": int(n), "base_rate": float(y.mean()), "accuracy": acc, "ranking_auc": rank_auc, "naive_accuracy": float(max(y.mean(), 1 - y.mean())),
            "precision": float(tp / (tp + fp)) if tp + fp else float("nan"), "recall": float(tp / (tp + fn)) if tp + fn else float("nan"),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else float("nan"),
            "brier_skill": float(1 - br / br0) if br0 else 0.0,
            "published_share": float(pub.mean()), "published_accuracy": pub_acc}


def strategy_metrics(oos: pd.DataFrame, h: int) -> dict:
    """Long-only: equal-weight the published bullish calls, rebalanced every h days (no costs).
    Benchmark: equal-weight the whole universe. Also a market-neutral top-minus-bottom quintile spread."""
    reb = np.sort(oos["_pos"].unique())[::max(h, 1)]
    s = oos[oos["_pos"].isin(reb)]
    rows = []
    for d, g in s.groupby("date"):
        pick = g[(g["p"] > g["base"]) & g["conf"].isin(["High", "Medium"])]
        q = g["p"].rank(pct=True)
        rows.append({"date": d, "strat": pick["ret"].mean() if len(pick) else 0.0, "bench": g["ret"].mean(),
                     "n_pos": len(pick), "hit": (pick["ret"] > 0).mean() if len(pick) else np.nan,
                     "ls": g.loc[q >= 0.8, "ret"].mean() - g.loc[q <= 0.2, "ret"].mean()})
    r = pd.DataFrame(rows).set_index("date")
    ppy = 252 / max(h, 1)

    def stats(x):
        x = x.fillna(0)
        eq = (1 + x).cumprod()
        ann = eq.iloc[-1] ** (ppy / max(len(x), 1)) - 1 if len(x) else 0
        vol = x.std() * math.sqrt(ppy)
        return {"ann_return": float(ann), "ann_vol": float(vol), "sharpe": float(ann / vol) if vol > 0 else 0.0,
                "max_drawdown": float((eq / eq.cummax() - 1).min()), "win_rate": float((x > 0).mean())}

    out = {"strategy": stats(r["strat"]), "benchmark": stats(r["bench"]), "long_short": stats(r["ls"]),
           "avg_positions": float(r["n_pos"].mean()), "position_hit_rate": float(r["hit"].mean()),
           "invested_share": float((r["n_pos"] > 0).mean())}
    eq_s, eq_b = (1 + r["strat"].fillna(0)).cumprod(), (1 + r["bench"].fillna(0)).cumprod()
    step = max(1, len(r) // 300)
    out["curve"] = [{"date": str(pd.Timestamp(d).date()), "strategy": round(float(a), 4), "benchmark": round(float(b), 4),
                     "dd": round(float(a / eq_s.loc[:d].max() - 1), 4)} for d, a, b in zip(r.index[::step], eq_s.iloc[::step], eq_b.iloc[::step])]
    return out


def horizon_metrics(oos: pd.DataFrame) -> dict:
    return _cls_metrics(oos)


def segment_metrics(oos: pd.DataFrame) -> list[dict]:
    segs = []
    for col, label_map in (("regime", None), ("vol_regime", None),
                           ("earn_season", {True: "Earnings season (≤10 days after report)", False: "Outside earnings season"}),
                           ("downturn", {True: "Economic downturn / deep drawdown", False: "No downturn"})):
        for val, g in oos.groupby(col):
            if len(g) < 500:
                continue
            name = label_map.get(val, str(val)) if label_map else str(val)
            segs.append({"segment": name, "group": col, **_cls_metrics(g)})
    return segs


def gain_calibration(oos: pd.DataFrame) -> list[dict]:
    out = []
    mu = move_from_prob(oos["p"].to_numpy(), oos["sigma"].to_numpy(), oos["band_c"].to_numpy())
    s = oos["band_c"].to_numpy() * oos["sigma"].to_numpy()
    for thr in (0.05, 0.10, 0.20):
        pred = prob_max_above(mu, s, thr)
        act = (oos["maxret"].to_numpy() > thr)
        pr, ac = float(np.nanmean(pred)), float(np.nanmean(act))
        out.append({"threshold": int(thr * 100), "predicted": pr, "actual": ac, "scale": (ac / pr) if pr > 1e-4 else 1.0})
    return out


def calibration_curve(oos: pd.DataFrame) -> list[dict]:
    bins = np.linspace(0, 1, 21); idx = np.clip(np.digitize(oos["p"], bins) - 1, 0, 19)
    return [{"pred": float(oos["p"][idx == i].mean()), "actual": float(oos["y"][idx == i].mean()), "n": int((idx == i).sum())}
            for i in range(20) if (idx == i).sum() >= 100]


# --------------------------------------------------------------------------- state
def build_state(bt: dict, panel: pd.DataFrame, feats: list[str], log=print) -> dict:
    """Everything the daily run needs from the backtest, plus the numbers the dashboard shows."""
    state = {"generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "horizons": {}}
    for name, r in bt.items():
        oos, h = r["oos"], r["h"]
        comps = list(r["comp_cols"])
        last_blocks = oos[oos["block"] >= oos["block"].max() - config.WEIGHT_LOOKBACK_BLOCKS + 1]
        w, perf = component_weights(last_blocks, comps, oos)
        full_auc = {k: perf[k]["auc_all"] for k in comps}
        iso = fit_calibrator(oos["raw"].to_numpy(), oos["y"].to_numpy())
        c = band_multiplier(oos["ret"].to_numpy(), norm.ppf(np.clip(oos["p"].to_numpy(), .01, .99)), oos["sigma"].to_numpy())
        cover = float(np.mean(np.abs(oos["ret"] - move_from_prob(oos["p"], oos["sigma"], oos["band_c"])) <=
                              norm.ppf(0.5 + config.BAND_COVERAGE / 2) * oos["band_c"] * oos["sigma"]))
        state["horizons"][name] = {
            "h": h, "base_rate": float(oos["y"].mean()), "mkt_base": float(oos.groupby("date")["mret"].first().gt(0).mean()),
            "weights": w, "iso_x": iso.X_thresholds_.tolist(), "iso_y": iso.y_thresholds_.tolist(), "band_c": c,
            "setup_table": setup_table(oos),
            "metrics": {**horizon_metrics(oos), "band_coverage": cover,
                        "start": str(pd.Timestamp(oos["date"].min()).date()), "end": str(pd.Timestamp(oos["date"].max()).date())},
            "segments": segment_metrics(oos), "strategy": strategy_metrics(oos, h),
            "calibration": calibration_curve(oos), "gain_calibration": gain_calibration(oos),
            "components": [{"key": k, "label": COMPONENTS[k]["label"], "weight": w[k], "recent_skill": perf[k]["skill"],
                            "recent_auc": perf[k]["auc"], "full_auc": full_auc[k],
                            "status": "Active" if w[k] >= 0.15 else ("Reduced" if w[k] > 0 else "Switched off")} for k in comps],
            "weights_history": r["weights_hist"],
        }
        log(f"  state {name}: weights " + ", ".join(f"{k}={v:.2f}" for k, v in w.items()))
    return state


def save_state(state: dict):
    os.makedirs(config.STATE_DIR, exist_ok=True)
    with open(os.path.join(config.STATE_DIR, "backtest_state.json"), "w") as fh:
        json.dump(state, fh, default=lambda o: None if (isinstance(o, float) and o != o) else (float(o) if isinstance(o, np.floating) else str(o)))


def load_state() -> dict | None:
    p = os.path.join(config.STATE_DIR, "backtest_state.json")
    return json.load(open(p)) if os.path.exists(p) else None


# --------------------------------------------------------------------------- final models
class LiveModel:
    """Final components trained on all labelled history + the saved weights / calibration."""

    def __init__(self, panel, feats, state, log=print):
        self.comp_cols = component_features(feats)
        self.state = state
        self.models = {}
        for name in config.HORIZONS:
            ycol = f"y_up_{name}"
            tr = sample_rows(panel[panel[ycol].notna()], config.TRAIN_SAMPLE_EVERY)
            self.models[name] = fit_components(tr, self.comp_cols, ycol)
            log(f"  trained {name}: {len(tr):,} rows")

    def predict(self, name: str, X: pd.DataFrame) -> dict:
        hs = self.state["horizons"][name]
        cp = predict_components(self.models[name], X, self.comp_cols)
        base = hs["base_rate"]
        if sum(hs["weights"].values()) <= 0:
            return {"p": np.full(len(X), base), "raw": np.full(len(X), base), "components": cp}
        raw = blend(cp, hs["weights"], base, hs.get("mkt_base"))
        p = np.clip(base + np.interp(raw, hs["iso_x"], hs["iso_y"]) - np.interp(base, hs["iso_x"], hs["iso_y"]), 0.02, 0.98)
        return {"p": p, "raw": raw, "components": cp}


def feature_importance(panel: pd.DataFrame, feats: list[str], horizon: str = "1m", top: int = 25) -> dict:
    ycol = f"y_up_{horizon}"
    d = sample_rows(panel[panel[ycol].notna()], 5)
    d = d.iloc[-min(len(d), 40000):]
    cut = int(len(d) * 0.75)
    m = _hgb().fit(d[feats].iloc[:cut], d[ycol].iloc[:cut])
    te = d.iloc[cut:]
    te = te.sample(min(len(te), 6000), random_state=0)
    r = permutation_importance(m, te[feats], te[ycol], scoring="roc_auc", n_repeats=3, random_state=0, n_jobs=-1)
    imp = pd.Series(r.importances_mean, index=feats).clip(lower=0)
    fam = imp.groupby([family_of(c) for c in imp.index]).sum()
    tot = fam.sum() or 1.0
    return {"features": [{"feature": k, "family": family_of(k), "importance": float(v)} for k, v in imp.sort_values(ascending=False).head(top).items()],
            "families": [{"family": k, "share": float(v / tot)} for k, v in fam.sort_values(ascending=False).items()]}
