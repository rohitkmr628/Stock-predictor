"""Models, walk-forward backtest and feature importance.

Direction  : ensemble of gradient-boosted trees + regularised logistic regression,
             calibrated with isotonic regression on a held-out slice of the training window.
Magnitude  : gradient-boosted quantile regression (10th / 50th / 90th percentile of return).
Big gains  : one gradient-boosted classifier per threshold (e.g. max close > +5% within period).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import config
from features import family_of

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

QUANTILES = (0.1, 0.5, 0.9)


def _hgb_clf(seed=0):
    return HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=400, l2_regularization=2.0, random_state=seed)


def _hgb_q(q, seed=0):
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=150, learning_rate=0.05,
                                         max_leaf_nodes=15, min_samples_leaf=300, l2_regularization=2.0,
                                         random_state=seed)


def _lr():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=0.05, max_iter=2000))


class DirectionModel:
    """Calibrated ensemble for P(up)."""

    def fit(self, X: pd.DataFrame, y: pd.Series):
        n = len(X); cut = int(n * 0.85)
        self.hgb, self.lr = _hgb_clf(), _lr()
        # fit on the first 85%, calibrate on the last 15% (chronological)
        self.hgb.fit(X.iloc[:cut], y.iloc[:cut]); self.lr.fit(X.iloc[:cut], y.iloc[:cut])
        raw = self._raw(X.iloc[cut:])
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=0.02, y_max=0.98).fit(raw, y.iloc[cut:])
        # refit base models on everything
        self.hgb.fit(X, y); self.lr.fit(X, y)
        return self

    def _raw(self, X):
        return 0.5 * self.hgb.predict_proba(X)[:, 1] + 0.5 * self.lr.predict_proba(X)[:, 1]

    def predict_proba(self, X):
        raw = self._raw(X)
        cal = self.iso.predict(raw)
        # shrink toward the raw ensemble a little so isotonic steps don't produce flat plateaus
        return np.clip(0.7 * cal + 0.3 * raw, 0.01, 0.99)

    def contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        """Per-feature log-odds contributions from the logistic part (for explanations)."""
        imp, sc, lr = self.lr.named_steps.values()
        z = sc.transform(imp.transform(X))
        return pd.DataFrame(z * lr.coef_[0], index=X.index, columns=X.columns)


class QuantileModel:
    def fit(self, X, y):
        self.models = {q: _hgb_q(q).fit(X, y) for q in QUANTILES}
        return self

    def predict(self, X):
        p = np.column_stack([self.models[q].predict(X) for q in QUANTILES])
        p.sort(axis=1)    # enforce q10 <= q50 <= q90
        return p


class ThresholdModel:
    def fit(self, X, y):
        self.base = float(y.mean())
        self.model = _hgb_clf().fit(X, y) if y.sum() >= 40 and (1 - y).sum() >= 40 else None
        return self

    def predict_proba(self, X):
        if self.model is None:
            return np.full(len(X), self.base)
        return self.model.predict_proba(X)[:, 1]


# --------------------------------------------------------------------------- training helpers
def _rows(panel, target):
    m = panel[target].notna()
    return panel.loc[m]


def fit_all(panel: pd.DataFrame, feats: list[str]) -> dict:
    """Fit final models for every horizon on all labelled history."""
    models = {}
    for name in config.HORIZONS:
        d = _rows(panel, f"y_up_{name}")
        X = d[feats]
        m = {"dir": DirectionModel().fit(X, d[f"y_up_{name}"]),
             "q": QuantileModel().fit(X, d[f"y_ret_{name}"]),
             "thr": {}}
        for thr in config.GAIN_THRESHOLDS:
            col = f"y_gain{int(thr * 100)}_{name}"
            m["thr"][thr] = ThresholdModel().fit(X, d[col])
        models[name] = m
        print(f"  trained {name}: {len(d):,} rows")
    return models


# --------------------------------------------------------------------------- backtest
def walk_forward(panel: pd.DataFrame, feats: list[str]) -> dict:
    """Expanding-window walk-forward test. Models are retrained every RETRAIN_EVERY days and only
    see rows whose outcome was already known (an embargo equal to the horizon avoids overlap leakage)."""
    dates = np.sort(panel["date"].unique())
    start = int(len(dates) * config.BACKTEST_START_FRACTION)
    results = {}
    for name, h in config.HORIZONS.items():
        preds = []
        for b in range(start, len(dates), config.RETRAIN_EVERY):
            test_dates = dates[b:b + config.RETRAIN_EVERY]
            train_end = dates[max(0, b - h - 1)]
            tr = panel[(panel["date"] <= train_end) & panel[f"y_up_{name}"].notna()]
            te = panel[panel["date"].isin(test_dates) & panel[f"y_up_{name}"].notna()]
            if len(tr) < config.MIN_TRAIN_ROWS or te.empty:
                continue
            dm = DirectionModel().fit(tr[feats], tr[f"y_up_{name}"])
            qm = QuantileModel().fit(tr[feats], tr[f"y_ret_{name}"])
            out = te[["date", "ticker", f"y_up_{name}", f"y_ret_{name}"]].copy()
            out.columns = ["date", "ticker", "y", "ret"]
            out["p"] = dm.predict_proba(te[feats])
            out[["q10", "q50", "q90"]] = qm.predict(te[feats])
            for thr in config.GAIN_THRESHOLDS:
                col = f"y_gain{int(thr * 100)}_{name}"
                tm = ThresholdModel().fit(tr[feats], tr[col])
                out[f"g{int(thr * 100)}_p"] = tm.predict_proba(te[feats])
                out[f"g{int(thr * 100)}_y"] = te[col].to_numpy()
            preds.append(out)
        if not preds:
            continue
        p = pd.concat(preds, ignore_index=True)
        results[name] = {"metrics": _metrics(p, h), "preds": p}
        mt = results[name]["metrics"]
        print(f"  backtest {name}: acc {mt['accuracy']:.3f}  AUC {mt['auc']:.3f}  base-rate {mt['base_rate']:.3f}  n={mt['n']:,}")
    return results


def _metrics(p: pd.DataFrame, h: int) -> dict:
    y, pr = p["y"].to_numpy(), p["p"].to_numpy()
    base = y.mean()
    m = {"n": int(len(p)), "start": str(pd.Timestamp(p["date"].min()).date()), "end": str(pd.Timestamp(p["date"].max()).date()),
         "base_rate": float(base),
         "accuracy": float(accuracy_score(y, pr > 0.5)),
         "naive_accuracy": float(max(base, 1 - base)),
         "balanced_accuracy": float(balanced_accuracy_score(y, pr > 0.5)),
         "auc": float(roc_auc_score(y, pr)) if len(set(y)) > 1 else float("nan"),
         "brier": float(brier_score_loss(y, pr)),
         "brier_base": float(brier_score_loss(y, np.full_like(pr, base))),
         "log_loss": float(log_loss(y, np.clip(pr, 1e-4, 1 - 1e-4)))}
    m["brier_skill"] = 1 - m["brier"] / m["brier_base"] if m["brier_base"] else 0.0
    conf = (pr >= 0.6) | (pr <= 0.4)
    m["high_conf_share"] = float(conf.mean())
    m["high_conf_accuracy"] = float(accuracy_score(y[conf], pr[conf] > 0.5)) if conf.any() else float("nan")
    # calibration curve
    bins = np.linspace(0, 1, 11); idx = np.clip(np.digitize(pr, bins) - 1, 0, 9)
    m["calibration"] = [{"pred": float(pr[idx == i].mean()), "actual": float(y[idx == i].mean()), "n": int((idx == i).sum())}
                        for i in range(10) if (idx == i).sum() >= 30]
    # average forward return by predicted-probability bucket (does ranking work?)
    p = p.copy(); p["bucket"] = pd.qcut(p["p"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    m["quintile_returns"] = [{"q": int(k), "avg_ret": float(g["ret"].mean()), "hit": float(g["y"].mean())}
                             for k, g in p.groupby("bucket", observed=True)]
    # magnitude model
    inside = (p["ret"] >= p["q10"]) & (p["ret"] <= p["q90"])
    m["range_coverage_80"] = float(inside.mean())
    # multiplier on the predicted range that would have given exactly 80% coverage
    lo, mid, hi = p["q10"].to_numpy(), p["q50"].to_numpy(), p["q90"].to_numpy(); r = p["ret"].to_numpy()
    grid = np.arange(0.6, 3.01, 0.05)
    cov = [np.mean((r >= mid - g * (mid - lo)) & (r <= mid + g * (hi - mid))) for g in grid]
    m["range_scale"] = float(grid[int(np.argmin(np.abs(np.array(cov) - 0.8)))])
    m["median_abs_err"] = float((p["ret"] - p["q50"]).abs().median())
    m["median_abs_err_naive"] = float(p["ret"].abs().median())
    # big-gain classifiers
    m["thresholds"] = {}
    for thr in config.GAIN_THRESHOLDS:
        k = int(thr * 100); yy, pp = p[f"g{k}_y"].to_numpy(), p[f"g{k}_p"].to_numpy()
        ok = ~np.isnan(yy)
        if ok.sum() and len(set(yy[ok])) > 1:
            top = pp[ok] >= np.quantile(pp[ok], 0.9)
            m["thresholds"][str(k)] = {"base_rate": float(yy[ok].mean()), "auc": float(roc_auc_score(yy[ok], pp[ok])),
                                       "top_decile_hit": float(yy[ok][top].mean())}
    # simple strategy check using non-overlapping periods: equal-weight the names with p>0.55
    dates = np.sort(p["date"].unique())[::h]
    s = p[p["date"].isin(dates)]
    curve, eq, bh = [], 1.0, 1.0
    for d, g in s.groupby("date"):
        sel = g[g["p"] > 0.55]
        eq *= 1 + (sel["ret"].mean() if len(sel) else 0.0)
        bh *= 1 + g["ret"].mean()
        curve.append({"date": str(pd.Timestamp(d).date()), "model": round(eq, 4), "equal_weight": round(bh, 4)})
    m["equity_curve"] = curve
    return m


# --------------------------------------------------------------------------- importance
def feature_importance(model: DirectionModel, X: pd.DataFrame, y: pd.Series, top: int = 20, seed: int = 0) -> dict:
    """Permutation importance (drop in AUC when a feature is shuffled) on recent data."""
    Xs, ys = X.iloc[-min(len(X), 6000):], y.iloc[-min(len(y), 6000):]
    r = permutation_importance(model.hgb, Xs, ys, scoring="roc_auc", n_repeats=3, random_state=seed, n_jobs=-1)
    imp = pd.Series(r.importances_mean, index=X.columns).clip(lower=0)
    fam = imp.groupby([family_of(c) for c in imp.index]).sum()
    tot = fam.sum() or 1.0
    return {"features": [{"feature": k, "family": family_of(k), "importance": float(v)} for k, v in imp.sort_values(ascending=False).head(top).items()],
            "families": [{"family": k, "share": float(v / tot)} for k, v in fam.sort_values(ascending=False).items()]}
