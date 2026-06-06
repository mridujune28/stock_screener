"""
Fetches the NASDAQ 100 and Nifty 100 stock universes and financial data via yfinance.
Falls back to hardcoded lists when Wikipedia scraping fails.
"""

import logging
import time
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

NASDAQ_100_FALLBACK = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST",
    "NFLX", "AMD", "ADBE", "QCOM", "TMUS", "AMAT", "INTU", "TXN", "AMGN", "BKNG",
    "ISRG", "MU", "LRCX", "VRTX", "REGN", "PANW", "KLAC", "SNPS", "CDNS", "CRWD",
    "MELI", "ABNB", "FTNT", "DXCM", "MAR", "PYPL", "NXPI", "ORLY", "CTAS", "PCAR",
    "MRNA", "WDAY", "ASML", "ADP", "SMCI", "MCHP", "MNST", "PAYX", "ODFL", "ROST",
    "FAST", "TEAM", "KDP", "EA", "BIIB", "ILMN", "CTSH", "EXC", "EBAY", "GEHC",
    "DLTR", "XEL", "IDXX", "DDOG", "ON", "VRSK", "KHC", "FANG", "BKR", "ALGN",
    "GFS", "WBD", "CSGP", "ANSS", "RVTY", "SIRI", "CDW", "NTAP", "CPRT", "GILD",
    "CCEP", "SBUX", "TTWO", "TROW", "ZS", "OKTA", "WBA", "ZM", "LCID", "RIVN",
    "PDD", "BIDU", "JD", "NTES", "LULU", "DOCU", "SPLK", "VEEV", "MTCH", "CHTR",
]

NIFTY_100_FALLBACK = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFOSYS.NS", "SBIN.NS", "HINDUNILVR.NS", "ITC.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS",
    "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "NTPC.NS", "AXISBANK.NS",
    "NESTLEIND.NS", "WIPRO.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "POWERGRID.NS",
    "M&M.NS", "BAJAJFINSV.NS", "TATASTEEL.NS", "JSWSTEEL.NS", "ADANIPORTS.NS",
    "COALINDIA.NS", "BRITANNIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "GRASIM.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "INDUSINDBK.NS", "CIPLA.NS",
    "APOLLOHOSP.NS", "BPCL.NS", "TECHM.NS", "TATACONSUM.NS", "BAJAJ-AUTO.NS",
    "TATAMOTORS.NS", "VEDL.NS", "SBILIFE.NS", "HDFCLIFE.NS", "ICICIPRULI.NS",
    "CHOLAFIN.NS", "SHRIRAMFIN.NS", "ZOMATO.NS", "NYKAA.NS", "PAYTM.NS",
    "IRCTC.NS", "HAL.NS", "BEL.NS", "RECLTD.NS", "PFC.NS",
    "SIEMENS.NS", "ABB.NS", "PIDILITIND.NS", "DABUR.NS", "MARICO.NS",
    "GODREJCP.NS", "COLPAL.NS", "BERGEPAINT.NS", "ICICIGI.NS", "MUTHOOTFIN.NS",
    "TORNTPHARM.NS", "ALKEM.NS", "LUPIN.NS", "BIOCON.NS", "AUROPHARMA.NS",
    "INDIGO.NS", "AMBUJACEM.NS", "ACC.NS", "SHREECEM.NS", "DMART.NS",
    "TRENT.NS", "JUBLFOOD.NS", "HAVELLS.NS", "VOLTAS.NS", "WHIRLPOOL.NS",
    "POLYCAB.NS", "CUMMINSIND.NS", "THERMAX.NS", "GMRAIRPORT.NS", "ADANIGREEN.NS",
    "ADANITRANS.NS", "ADANIPOWER.NS", "TATAPOWER.NS", "TORNTPOWER.NS", "NHPC.NS",
    "SJVN.NS", "GAIL.NS", "IOC.NS", "HPCL.NS", "MRPL.NS",
    "OBEROIRLTY.NS", "DLF.NS", "GODREJPROP.NS", "PRESTIGE.NS",
]


def _fetch_nasdaq100_wikipedia() -> list[str]:
    try:
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        tables = pd.read_html(url)
        for tbl in tables:
            cols = [str(c).lower() for c in tbl.columns]
            if "ticker" in cols or "symbol" in cols:
                col = "Ticker" if "Ticker" in tbl.columns else "Symbol"
                tickers = tbl[col].dropna().tolist()
                tickers = [str(t).strip().upper() for t in tickers if str(t).strip()]
                if len(tickers) >= 90:
                    logger.info("Fetched %d NASDAQ 100 tickers from Wikipedia", len(tickers))
                    return tickers
    except Exception as e:
        logger.warning("Wikipedia NASDAQ 100 fetch failed: %s", e)
    return []


def _fetch_nifty100_wikipedia() -> list[str]:
    try:
        url = "https://en.wikipedia.org/wiki/NIFTY_100"
        tables = pd.read_html(url)
        for tbl in tables:
            cols_lower = [str(c).lower() for c in tbl.columns]
            for candidate in ("symbol", "ticker"):
                if candidate in cols_lower:
                    col_idx = cols_lower.index(candidate)
                    col = tbl.columns[col_idx]
                    tickers = tbl[col].dropna().tolist()
                    tickers = [str(t).strip().upper() + ".NS" for t in tickers if str(t).strip()]
                    if len(tickers) >= 80:
                        logger.info("Fetched %d Nifty 100 tickers from Wikipedia", len(tickers))
                        return tickers
    except Exception as e:
        logger.warning("Wikipedia Nifty 100 fetch failed: %s", e)
    return []


def fetch_universe() -> dict[str, list[str]]:
    """Return {'nasdaq100': [...], 'nifty100': [...]} ticker lists."""
    nasdaq = _fetch_nasdaq100_wikipedia() or NASDAQ_100_FALLBACK
    nifty = _fetch_nifty100_wikipedia() or NIFTY_100_FALLBACK
    return {"nasdaq100": nasdaq[:100], "nifty100": nifty[:100]}


def fetch_stock_data(ticker: str) -> Optional[dict]:
    """
    Fetch all required financial data for a single ticker.
    Returns a dict with keys: info, quarterly_revenue, quarterly_op_income,
    quarterly_gross_profit, or None on total failure.
    """
    try:
        tk = yf.Ticker(ticker)

        # Basic info
        try:
            info = tk.info or {}
        except Exception:
            info = {}

        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            # May still be valid for some metrics; don't skip entirely
            pass

        # Quarterly financials
        quarterly_revenue: list = []
        quarterly_op_income: list = []
        quarterly_gross_profit: list = []

        try:
            fins = tk.quarterly_financials
            if fins is not None and not fins.empty:
                fins_t = fins.T.sort_index()  # oldest → newest
                # Revenue row labels vary; try common names
                for rev_label in ("Total Revenue", "Revenue", "Net Revenue"):
                    if rev_label in fins.index:
                        quarterly_revenue = fins.loc[rev_label].dropna().tolist()[-10:]
                        quarterly_revenue = [float(v) for v in quarterly_revenue]
                        break
                for oi_label in ("Operating Income", "Operating Income Loss", "Ebit"):
                    if oi_label in fins.index:
                        quarterly_op_income = fins.loc[oi_label].dropna().tolist()[-10:]
                        quarterly_op_income = [float(v) for v in quarterly_op_income]
                        break
                for gp_label in ("Gross Profit", "GrossProfit"):
                    if gp_label in fins.index:
                        quarterly_gross_profit = fins.loc[gp_label].dropna().tolist()[-10:]
                        quarterly_gross_profit = [float(v) for v in quarterly_gross_profit]
                        break

                # Try income_stmt if quarterly_financials is empty
                if not quarterly_revenue:
                    stmt = tk.quarterly_income_stmt
                    if stmt is not None and not stmt.empty:
                        for rev_label in ("Total Revenue", "Revenue"):
                            if rev_label in stmt.index:
                                vals = stmt.loc[rev_label].dropna()
                                vals = vals.sort_index()
                                quarterly_revenue = [float(v) for v in vals.tolist()][-10:]
                                break
                        for oi_label in ("Operating Income", "Ebit"):
                            if oi_label in stmt.index:
                                vals = stmt.loc[oi_label].dropna()
                                vals = vals.sort_index()
                                quarterly_op_income = [float(v) for v in vals.tolist()][-10:]
                                break
                        for gp_label in ("Gross Profit",):
                            if gp_label in stmt.index:
                                vals = stmt.loc[gp_label].dropna()
                                vals = vals.sort_index()
                                quarterly_gross_profit = [float(v) for v in vals.tolist()][-10:]
                                break
        except Exception as e:
            logger.warning("%s: Failed to fetch quarterly financials: %s", ticker, e)

        # Quarterly revenue date labels for charting
        quarterly_revenue_dates: list = []
        try:
            fins = tk.quarterly_financials
            if fins is not None and not fins.empty:
                for rev_label in ("Total Revenue", "Revenue", "Net Revenue"):
                    if rev_label in fins.index:
                        series = fins.loc[rev_label].dropna()
                        quarterly_revenue_dates = [str(d)[:10] for d in series.index.tolist()][-10:]
                        break
        except Exception:
            pass

        result = {
            "ticker": ticker,
            "info": info,
            "quarterly_revenue": quarterly_revenue,
            "quarterly_revenue_dates": quarterly_revenue_dates,
            "quarterly_op_income": quarterly_op_income,
            "quarterly_gross_profit": quarterly_gross_profit,
        }
        return result

    except Exception as e:
        logger.error("%s: Unhandled error in fetch_stock_data: %s", ticker, e)
        return None


def fetch_all_stocks(universe: dict[str, list[str]], delay: float = 0.3) -> list[dict]:
    """
    Fetch data for all tickers across all universes.
    Returns list of stock data dicts with 'universe' key added.
    """
    results = []
    seen = set()

    for universe_name, tickers in universe.items():
        logger.info("Fetching %s (%d tickers)...", universe_name, len(tickers))
        for i, ticker in enumerate(tickers):
            if ticker in seen:
                continue
            seen.add(ticker)

            logger.info("  [%d/%d] %s", i + 1, len(tickers), ticker)
            data = fetch_stock_data(ticker)
            if data is None:
                logger.warning("Skipping %s — no data returned", ticker)
                continue
            data["universe"] = universe_name
            results.append(data)
            time.sleep(delay)

    logger.info("Fetched data for %d stocks total", len(results))
    return results
