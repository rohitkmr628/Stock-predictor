"""Settings for the stock prediction model. Edit this file to change tickers, horizons or weights."""

# Stocks to analyse. Yahoo Finance symbols (Canadian listings use .TO / .V / .CN suffixes).
WATCHLIST = [
    "MU", "NVDA", "MSFT", "META", "GOOGL", "INTC", "PLTR", "TSM", "RKLB", "FLY",
    "PHOS", "MDA.TO", "AMZN", "ONDS", "TSLA", "EOSE", "AMD", "FLT.V", "SNDK",
    "NFLX", "NOW", "SHOP", "MRVL",
]

# Sector / industry ETF used for each stock's relative-strength features.
SECTOR_MAP = {
    "MU": "SMH", "NVDA": "SMH", "INTC": "SMH", "TSM": "SMH", "AMD": "SMH", "MRVL": "SMH", "SNDK": "SMH",
    "MSFT": "IGV", "NOW": "IGV", "PLTR": "IGV", "SHOP": "IGV",
    "META": "XLC", "GOOGL": "XLC", "NFLX": "XLC",
    "AMZN": "XLY", "TSLA": "XLY",
    "RKLB": "UFO", "FLY": "UFO", "MDA.TO": "UFO", "ONDS": "ITA", "FLT.V": "ITA",
    "EOSE": "ICLN", "PHOS": "LIT",
}
DEFAULT_SECTOR = "SPY"

# Broad market and cross-asset series (Yahoo symbols).
MARKET = {"spx": "SPY", "ndx": "QQQ", "dow": "DIA", "rut": "IWM"}
MACRO_MARKET = {
    "vix": "^VIX",        # volatility index
    "tnx": "^TNX",        # 10-yr Treasury yield (x10 on Yahoo for older data; handled as level)
    "irx": "^IRX",        # 13-week T-bill yield
    "oil": "CL=F",        # WTI crude
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",    # US dollar index
    "hyg": "HYG",         # high-yield credit (risk appetite)
}

# FRED macro series (monthly/quarterly). Lagged by one release to avoid look-ahead.
FRED_SERIES = {
    "cpi": "CPIAUCSL",       # CPI index -> YoY inflation
    "unrate": "UNRATE",      # unemployment rate
    "fedfunds": "FEDFUNDS",  # effective fed funds rate
    "umcsent": "UMCSENT",    # UMich consumer sentiment
    "gdp": "GDPC1",          # real GDP (quarterly) -> YoY growth
}

HISTORY_YEARS = 6            # price history to download
HORIZONS = {"1d": 1, "1w": 5, "1m": 21}   # trading days
GAIN_THRESHOLDS = [0.05, 0.10, 0.20]      # "gain more than X% within the period" (max close in window)

# Walk-forward backtest
BACKTEST_START_FRACTION = 0.5   # first half of history is the initial training window
RETRAIN_EVERY = 63              # trading days between retrains (~quarterly)
MIN_TRAIN_ROWS = 2000

# Live overlays: how far each current-only signal may shift the model's probability,
# expressed as a maximum change in log-odds. These signals have no usable history to
# backtest, so they are kept small on purpose. Set to 0 to switch one off.
OVERLAY_WEIGHTS = {
    "news_sentiment": 0.20,
    "analyst": 0.15,
    "options": 0.15,
    "institutional": 0.10,
    "earnings_event": 0.0,   # earnings widens the range (handled in risk), not the direction
}
