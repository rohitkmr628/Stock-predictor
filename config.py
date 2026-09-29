"""All settings for Odds Board v2. Edit here; nothing else needs changing for normal use."""

# --------------------------------------------------------------------------- universe
# Your own names are always included (and tagged "Watchlist") even if they fail the quality screen.
WATCHLIST = [
    "MU", "NVDA", "MSFT", "META", "GOOGL", "INTC", "PLTR", "TSM", "RKLB", "FLY",
    "PHOS", "MDA.TO", "AMZN", "ONDS", "TSLA", "EOSE", "AMD", "FLT.V", "SNDK",
    "NFLX", "NOW", "SHOP", "MRVL",
]
# Alternative Yahoo symbols tried when a ticker returns no data (fixes the missing Canadian listings).
ALT_SYMBOLS = {"FLT.V": ["FLT.TO", "VLTTF"], "MDA.TO": ["MDALF"], "PHOS": ["PHOS.CN", "FRSPF"], "FLY": []}

# Index constituents are read from Wikipedia at run time; this built-in list is the fallback
# and also guarantees coverage of the largest names.
FALLBACK_UNIVERSE = sorted(set("""
AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA BRK-B LLY JPM V UNH XOM MA JNJ PG HD COST ABBV MRK ORCL CVX
WMT KO PEP BAC ADBE CRM NFLX AMD TMO LIN ACN MCD CSCO ABT WFC DHR TXN INTU QCOM PM DIS VZ AMGN IBM
CAT NOW GE ISRG SPGI UBER AMAT CMCSA NEE UNP RTX HON LOW GS BKNG PFE T AXP BLK SYK ELV PGR COP
TJX LMT VRTX BSX MS ETN ADP SCHW MDT C REGN PLD CB MMC ADI LRCX DE PANW MU KLAC SBUX BMY GILD
FI CI SO TMUS MDLZ ANET BX ICE DUK SHW ZTS CME MO SNPS CDNS EQIX CL APH PH MCO TT WM ITW KKR ORLY
CTAS MSI HCA ROP NOC GD MAR CMG PYPL ABNB CRWD FTNT MRVL ADSK WDAY DDOG TEAM ZS MELI PDD ASML
CEG FICO AZO ODFL CPRT PAYX FAST ROST IDXX MNST KDP CSX NXPI MCHP ON TTD CSGP VRSK EA
MMM TRV MCK HUM AON AJG ECL APD EMR AFL MET PSX VLO MPC OXY KMB GIS HSY KR TGT DG ANSS KEYS
IT TDG HWM URI PWR GWW AME DOV XYL ROK DHI LEN NVR PHM TSCO ULTA DECK LULU NKE EL YUM DPZ
INTC PLTR SHOP NOW SNOW NET
TSM NVO SAP TM SONY AZN SHEL UL NVS BHP RIO HSBC TTE BP DEO BTI SNY GSK RY TD MUFG INFY HDB
""".split()))
USE_WIKIPEDIA_CONSTITUENTS = True       # S&P 500, Nasdaq-100, Dow 30
GLOBAL_BLUE_CHIPS = ["TSM", "ASML", "NVO", "SAP", "TM", "SONY", "AZN", "SHEL", "UL", "NVS", "BHP", "RIO",
                     "HSBC", "TTE", "DEO", "SNY", "GSK", "RY", "TD", "MUFG", "INFY", "HDB", "MELI"]

# Quality screen (applied to index names; watchlist names bypass it)
MIN_MARKET_CAP = 30e9            # USD
MAX_UNIVERSE = 40                # top 40 by quality score + your watchlist
SCREEN = {
    "min_profit_margin": 0.0,     # consistently profitable
    "min_fcf": 0.0,               # positive free cash flow
    "max_debt_to_equity": 250.0,  # Yahoo reports D/E in % (250 = 2.5x); skipped for banks/insurers
}

# --------------------------------------------------------------------------- sector mapping
SECTOR_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV", "Energy": "XLE",
    "Industrials": "XLI", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Utilities": "XLU",
    "Basic Materials": "XLB", "Real Estate": "XLRE", "Communication Services": "XLC",
}
# Finer industry ETFs for watchlist themes (override the sector ETF when present)
INDUSTRY_ETF_OVERRIDE = {
    "MU": "SMH", "NVDA": "SMH", "INTC": "SMH", "TSM": "SMH", "AMD": "SMH", "MRVL": "SMH", "SNDK": "SMH",
    "AVGO": "SMH", "QCOM": "SMH", "TXN": "SMH", "AMAT": "SMH", "LRCX": "SMH", "KLAC": "SMH", "ADI": "SMH",
    "RKLB": "UFO", "FLY": "UFO", "MDA.TO": "UFO", "ONDS": "ITA", "FLT.V": "ITA", "EOSE": "ICLN", "PHOS": "LIT",
    "NOW": "IGV", "PLTR": "IGV", "SHOP": "IGV", "CRM": "IGV", "ADBE": "IGV", "WDAY": "IGV",
}
DEFAULT_SECTOR = "SPY"

MARKET = {"spx": "SPY", "ndx": "QQQ", "dow": "DIA", "rut": "IWM"}
MACRO_MARKET = {"vix": "^VIX", "tnx": "^TNX", "irx": "^IRX", "oil": "CL=F", "gold": "GC=F",
                "dxy": "DX-Y.NYB", "hyg": "HYG", "tlt": "TLT"}
FRED_SERIES = {"cpi": "CPIAUCSL", "unrate": "UNRATE", "fedfunds": "FEDFUNDS", "umcsent": "UMCSENT",
               "gdp": "GDPC1", "indpro": "INDPRO"}

# --------------------------------------------------------------------------- model
HISTORY_YEARS = 12                         # covers 2015-16 slowdown, 2018 Q4, 2020 crash, 2022 bear, 2025 sell-off
HORIZONS = {"1d": 1, "1w": 5, "1m": 21, "3m": 63}
PRIMARY_HORIZON = "1m"                     # used for position size, opportunities list
TRAIN_SAMPLE_EVERY = 3                     # train on every Nth day (overlapping labels add little; big speed-up)
BACKTEST_MIN_TRAIN_YEARS = 3
RETRAIN_EVERY = 126                        # trading days between walk-forward retrains (~6 months)
WEIGHT_LOOKBACK_BLOCKS = 4                 # component weights use the last ~2 years of out-of-sample results
N_JOBS = -1

# Confidence gating: a forecast is "published" only at Medium or High confidence
# A stock must rank in the top/bottom of the universe (High needs the top/bottom 10%), sit on the same
# side of the base rate by at least min_edge, and similar past calls must have beaten their base rate
# by setup_edge on at least min_n cases.
CONFIDENCE = {
    "high": {"min_edge": 0.02, "setup_edge": 0.03, "min_n": 300},
    "medium": {"min_edge": 0.01, "setup_edge": 0.015, "min_n": 150},
}
BAND_COVERAGE = 0.80                       # uncertainty band target coverage (calibrated in the backtest)

# Illustrative position sizing (NOT advice): risk this share of the portfolio on the band's downside
POSITION = {"risk_per_idea": 0.01, "max_weight": 0.08, "conf_mult": {"High": 1.0, "Medium": 0.5, "Low": 0.0}}

# Live overlays (not backtestable) — capped log-odds nudges, and only fetched for the top names
OVERLAY_WEIGHTS = {"news_sentiment": 0.15, "analyst": 0.12, "options": 0.12, "institutional": 0.08}
LIVE_SIGNAL_LIMIT = 60

STATE_DIR = "model_state"                  # saved backtest results, weights, calibration, fundamentals cache
