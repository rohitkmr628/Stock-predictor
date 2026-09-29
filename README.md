# Odds Board v2

A research dashboard that estimates, for the **top 40 quality large caps plus your watchlist**:

- the probability of rising or falling over **1 day, 1 week, 1 month and 3 months**
- the expected change and an 80% uncertainty band for each horizon
- a **confidence level**, earned from the model's own track record on similar past calls
- a risk rating (1–10), an illustrative position size and a risk/reward ratio

It then builds five top-20 lists (drawn from the ~60 stocks covered): **low-risk growth**, **highest probability**, **momentum**, **long-term compounders** and **next-30-day opportunities**. The backtest, feature importance and component weights are all shown.

> **Illustrative research, not investment advice.** Short-term returns are mostly noise. The model is built to be *reliable* rather than to promise accuracy. It publishes a forecast only when its backtested record in similar setups supports one, and it shows every miss in the Backtest tab.

## What changed from v1

| Area | v1 | v2 |
|---|---|---|
| Universe | 23-stock watchlist | S&P 500 + Nasdaq-100 + Dow 30 + global blue chips, quality-screened (market cap ≥ $30B, profitable, positive FCF, moderate debt), top 40 by quality, plus your watchlist |
| Horizons | 1d / 1w / 1m | + 3 months |
| Model | one boosted-tree + logistic blend | 6-component ensemble: 5 stock-selection components (technical, relative strength, earnings, time-series, linear all-factor) predict *beating the average stock*; 1 market-timing component (regime, breadth, macro) |
| Weighting | fixed | each component earns weight from its out-of-sample record (the worse of recent and full-history AUC); failing components are switched off automatically |
| New evidence | – | market regime (bull/bear/sideways, volatility), breadth, sector rotation, EPS surprises and beat streaks, recession signals, 12-1 momentum, cross-sectional ranks |
| Backtest | 2 years | ~8 years walk-forward (2018 Q4, 2020 crash, 2022 bear, 2025 sell-off) with results by condition: bull, bear, sideways, high volatility, earnings season, downturn |
| Metrics | accuracy, AUC | + precision, recall, ranking AUC, Brier skill, published-call accuracy, band coverage, Sharpe, max drawdown, win rate, long-short spread |
| Confidence | simple | High/Medium only when the stock ranks in the top/bottom of the universe *and* past calls from that bucket beat their base rate. Low forecasts are not published |
| Fundamentals | – | growth, profitability, cash flow, balance sheet, stability and valuation scores (0–100) |
| Coverage fix | FLT.V / MDA.TO missing | alternative Yahoo symbols tried automatically |
| Schedule | once a day | pre-open + post-close (fast), plus a weekly full rebuild |

## How the runs work

- **Full run** (Saturdays, or manually): refreshes the universe and fundamentals, runs the multi-cycle backtest, and saves the model's track record, weights and calibration to `model_state/`. It takes about 30–60 minutes on GitHub.
- **Daily run** (8:15 AM and 4:30 PM New York time on weekdays): downloads fresh prices and earnings, retrains the final models, reuses the saved track record and publishes the dashboard. It takes about 5–15 minutes.
- **The first run** is automatically a full run, because there's no saved state yet.

## Upgrading your GitHub repo from v1

1. In your repo, delete the old files: `features.py`, `model.py`, `report.py`, `run.py`, `dashboard.py`, `config.py`, `data.py`, `overlays.py`, `streamlit_app.py`, `requirements.txt`, `README.md`. For each one, open it, click the ⋯ menu, then **Delete file**.
2. **Add file → Upload files**, and drag in every `.py` file plus `requirements.txt` and `README.md` from this folder.
3. Open `.github/workflows/daily.yml`, click the pencil, **replace its whole contents** with the new `daily.yml`, and commit.
4. Go to **Actions → Odds Board → Run workflow**, choose **full**, then **Run workflow**. Wait for the green tick (about 30–60 minutes).
5. Open your site as before: `https://<username>.github.io/<repo>/`

## Settings (`config.py`)

| Setting | What it does |
|---|---|
| `WATCHLIST` | Your names, always included |
| `MIN_MARKET_CAP`, `SCREEN`, `MAX_UNIVERSE` | The quality screen and universe size (currently 40; larger = broader lists but slower runs) |
| `HORIZONS`, `PRIMARY_HORIZON` | Forecast horizons; the primary one drives sizing and the 30-day list |
| `CONFIDENCE` | Thresholds for High/Medium; raise them to publish fewer, stronger calls |
| `POSITION` | Illustrative sizing rule: risk per idea, max weight, confidence multipliers |
| `OVERLAY_WEIGHTS`, `LIVE_SIGNAL_LIMIT` | How much news, analyst, options and insider data may nudge a probability, and for how many stocks it's fetched |
| `HISTORY_YEARS`, `RETRAIN_EVERY`, `TRAIN_SAMPLE_EVERY` | Backtest depth and speed |

## Honest limits

- **Stock-selection skill is small.** A ranking AUC of 0.52–0.55 is already a good result. Accuracy vs "always up" often looks poor, because markets rise most of the time; judge the model on published-call accuracy and ranking AUC.
- **Fundamentals are today's snapshot.** They're used for the screen, the quality scores and the lists, but not inside the backtested model, because that would leak future information. EPS surprises *are* point-in-time and are backtested.
- **News, analyst, options and insider signals** can't be backtested with free data. Their effect is small and capped.
- **The universe has survivorship bias.** Today's index members survived. Treat backtest returns as optimistic.
- **Costs are not modelled.** Transaction costs, taxes and slippage aren't included.

## Run locally

```bash
pip install -r requirements.txt
python run.py --mode full     # first time
python run.py --mode daily    # afterwards
python run.py --demo          # synthetic data, no internet
```

Open `site/index.html` in your browser.
