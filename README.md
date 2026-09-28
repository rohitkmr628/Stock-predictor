# Odds Board: a stock move probability model

For each stock, Odds Board estimates:

- the chance of a higher or lower close in 1 day, 1 week and 1 month
- the expected (median) move and an 80% range
- the chance of gaining more than +5%, +10% or +20% within the period

It then writes a dashboard with charts, factor explanations, risk flags, a big-move scanner and full backtest results.

> **Read this first.** Short-term stock moves are mostly noise. Good models usually reach 51–56% directional accuracy. This model shows its own out-of-sample record, and it shrinks every probability toward the historical base rate unless the backtest proves skill. It is not financial advice.

## What goes into it

| Factor | How it's used | Backtested? |
|---|---|---|
| Price & volume history (OHLCV) | 118 features: returns, volatility, RSI, MACD, Bollinger Bands, moving averages, stochastics, ATR, ADX, CCI, OBV, money flow | Yes |
| Chart patterns | Rule-based detection: double tops/bottoms, head & shoulders (and inverse), cup & handle, flags, triangles, breakouts, support/resistance, trend lines | Yes |
| Sector & market | Relative strength vs sector ETF and S&P 500, beta, index trends (S&P, Nasdaq, Dow, Russell) | Yes |
| Rates, volatility & commodities | VIX, 10-yr and 3-month yields, yield curve, oil, gold, dollar, high-yield credit | Yes |
| Macroeconomic | CPI inflation, unemployment, fed funds, consumer sentiment, GDP (FRED, lagged to release dates) | Yes |
| Earnings calendar | Days to and since earnings; the range widens when earnings fall inside the window | Yes |
| News sentiment | Recent headlines scored with VADER | No (live overlay) |
| Analyst ratings | Target price vs current price, net up/downgrades in 30 days, consensus rating | No (live overlay) |
| Options market | Put/call ratios, implied vs realised volatility, unusual activity | No (live overlay) |
| Institutional & insider | Institutional ownership, net insider buying/selling in 6 months | No (live overlay) |

**Models:** gradient-boosted trees plus logistic regression for direction (isotonic-calibrated), gradient-boosted quantile regression for the move range, and one classifier per gain threshold. All data is pooled across your tickers.

**Backtest:** an expanding-window walk-forward test. The model retrains quarterly and uses an embargo equal to the horizon, so it never sees an outcome it's predicting. Reported metrics: accuracy vs naive, AUC, Brier skill, calibration curve, quintile returns, 80%-range coverage, big-gain AUC and a simple signal equity curve. Feature importance is permutation-based.

**Live overlays** can't be backtested with free data, so each can shift the probability only by a small, capped amount. You can change these weights in `config.py`.

## Option A: run it on your computer

```bash
pip install -r requirements.txt
python run.py                      # full run on your watchlist (≈10–20 min with backtest)
python run.py --no-backtest        # faster (≈3–5 min)
python run.py --tickers NVDA AMD MU
python run.py --demo               # synthetic data, no internet needed
```

Then open `site/index.html` in your browser.

## Option B: automatic daily web page (GitHub Actions + Pages, free)

1. Create a free account at github.com, then create a **new repository** (e.g. `stock-predictor`). It can be private if you have GitHub Pro; otherwise Pages needs a public repo.
2. Upload every file in this folder, including the hidden `.github/workflows/daily.yml` file. Use **Add file → Upload files** and drag the whole folder in.
3. Go to **Settings → Pages** and under *Source* choose **GitHub Actions**.
4. Go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**.
5. Go to the **Actions** tab, open **Daily predictions** and press **Run workflow**.

The first run takes about 15–20 minutes. Your dashboard will then be at `https://<your-username>.github.io/<repo-name>/`. After that it refreshes automatically at 8:15 AM New York time on weekdays. To change the time, edit the `cron` line.

## Option C: interactive web app (Streamlit Community Cloud, free)

1. Complete step 1–2 of option B (the code must be in a GitHub repo).
2. Go to share.streamlit.io, sign in with GitHub and choose **Create app**.
3. Pick your repo, set the main file to `streamlit_app.py` and deploy.

You get a URL where you can type any tickers and press **Run**. If the GitHub workflow is also set up, the app shows the latest daily run until you start a new one.

## Customising

- **Watchlist, sector ETFs, horizons, thresholds, overlay weights:** edit `config.py`.
- **Canadian listings** use Yahoo suffixes: `MDA.TO`, `FLT.V`. `PHOS` is the Nasdaq ADR.
- **A new feature:** add a column in `features.py` with one of the family prefixes (`tech_`, `pat_`, `rel_`, `mkt_`, `x_`, `macro_`, `earn_`, `ts_`). It's picked up automatically.

## Files

| File | Purpose |
|---|---|
| `config.py` | All settings |
| `data.py` | Yahoo Finance and FRED downloads, plus the synthetic demo data |
| `features.py` | Indicators, chart patterns, relative strength, market and macro features, targets |
| `model.py` | Models, walk-forward backtest, feature importance |
| `overlays.py` | News, analyst, options and institutional signals |
| `report.py` | Predictions, explanations, risk, outlooks, rankings |
| `dashboard.py` | Self-contained HTML dashboard (no external chart libraries) |
| `run.py` | Command-line entry point |
| `streamlit_app.py` | Web app |
