"""
Scoring engine: 4 questions, each 0–25, total 0–100.
All functions accept the raw stock data dict from fetcher.py.
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# Sector median forward PEs — used when per-stock sector comparison is unavailable.
# Values are approximate consensus medians; update annually.
SECTOR_PE_MEDIANS = {
    "Technology": 28.0,
    "Communication Services": 22.0,
    "Consumer Cyclical": 20.0,
    "Consumer Defensive": 22.0,
    "Healthcare": 20.0,
    "Financials": 14.0,
    "Financial Services": 14.0,
    "Industrials": 20.0,
    "Basic Materials": 15.0,
    "Energy": 12.0,
    "Utilities": 16.0,
    "Real Estate": 30.0,
    "Unknown": 20.0,
}


# ---------------------------------------------------------------------------
# Q1: Revenue Growth (0–25)
# ---------------------------------------------------------------------------

def score_revenue_growth(quarterly_revenue: list[float]) -> dict:
    """
    Score revenue growth based on:
    - YoY consistency: # quarters with positive YoY growth (up to 6, as we need 4 prior)
    - 10Q CAGR (annualised)
    - Whether growth is accelerating or decelerating
    """
    if not quarterly_revenue or len(quarterly_revenue) < 2:
        return {"score": 0, "label": "Data unavailable", "cagr": None, "trend": "unknown"}

    rev = quarterly_revenue  # oldest → newest, up to 10 values
    n = len(rev)

    # YoY consistency (compare Q_i vs Q_{i-4})
    yoy_positive = 0
    yoy_total = 0
    yoy_growth_rates = []
    for i in range(4, n):
        prior = rev[i - 4]
        current = rev[i]
        if prior and prior != 0:
            rate = (current - prior) / abs(prior)
            yoy_growth_rates.append(rate)
            yoy_total += 1
            if current > prior:
                yoy_positive += 1

    consistency_score = (yoy_positive / yoy_total * 10) if yoy_total > 0 else 0

    # Overall CAGR over available quarters
    if rev[0] and rev[0] > 0 and rev[-1] and rev[-1] > 0:
        periods_years = (n - 1) / 4.0
        cagr = (rev[-1] / rev[0]) ** (1 / periods_years) - 1 if periods_years > 0 else 0
    else:
        cagr = None

    cagr_score = 0
    if cagr is not None:
        if cagr >= 0.25:
            cagr_score = 10
        elif cagr >= 0.15:
            cagr_score = 8
        elif cagr >= 0.08:
            cagr_score = 6
        elif cagr >= 0.03:
            cagr_score = 4
        elif cagr >= 0:
            cagr_score = 2
        else:
            cagr_score = 0

    # Acceleration/deceleration (last 2 YoY vs first 2 YoY)
    accel_score = 0
    trend = "stable"
    if len(yoy_growth_rates) >= 4:
        early_avg = sum(yoy_growth_rates[:2]) / 2
        recent_avg = sum(yoy_growth_rates[-2:]) / 2
        if recent_avg > early_avg + 0.03:
            accel_score = 5
            trend = "accelerating"
        elif recent_avg > early_avg - 0.03:
            accel_score = 3
            trend = "stable"
        else:
            accel_score = 0
            trend = "decelerating"
    elif len(yoy_growth_rates) >= 1:
        accel_score = 2
        trend = "stable"

    score = min(25, round(consistency_score + cagr_score + accel_score))

    label = (
        "Strong growth" if score >= 20
        else "Moderate growth" if score >= 12
        else "Weak growth" if score >= 5
        else "No growth / declining"
    )

    return {
        "score": score,
        "label": label,
        "cagr": round(cagr * 100, 1) if cagr is not None else None,
        "trend": trend,
        "yoy_consistency": f"{yoy_positive}/{yoy_total}",
    }


# ---------------------------------------------------------------------------
# Q2: Profitability — Operating Income Growth (0–25)
# ---------------------------------------------------------------------------

def score_profitability(quarterly_op_income: list[float], quarterly_revenue: list[float]) -> dict:
    """
    Score profitability based on:
    - Trend direction of operating income
    - Operating margin expansion/contraction
    - Consistency of positive operating income
    """
    if not quarterly_op_income or len(quarterly_op_income) < 2:
        return {"score": 0, "label": "Data unavailable", "margin_trend": "unknown"}

    oi = quarterly_op_income
    n = len(oi)

    # Consistency of positive operating income
    positive_count = sum(1 for v in oi if v is not None and v > 0)
    consistency_score = round(positive_count / n * 10)

    # Trend direction (linear regression slope sign)
    if n >= 3:
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(oi) / n
        num = sum((xs[i] - mean_x) * (oi[i] - mean_y) for i in range(n))
        den = sum((xs[i] - mean_x) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0
        trend_score = 8 if slope > 0 else 3 if abs(slope) < 0.05 * abs(mean_y or 1) else 0
        trend = "improving" if slope > 0 else "stable" if trend_score == 3 else "declining"
    else:
        slope = oi[-1] - oi[0]
        trend_score = 6 if slope > 0 else 2
        trend = "improving" if slope > 0 else "declining"

    # Operating margin expansion
    margin_trend_score = 0
    margin_trend = "unknown"
    if quarterly_revenue and len(quarterly_revenue) >= 2 and len(oi) >= 2:
        rev = quarterly_revenue
        # Pair up revenue and OI (use shortest length)
        pairs = list(zip(rev[-len(oi):], oi))
        margins = [
            (o / r * 100) if r and r != 0 else None
            for r, o in pairs
        ]
        margins = [m for m in margins if m is not None]
        if len(margins) >= 2:
            early_margin = sum(margins[:2]) / 2
            late_margin = sum(margins[-2:]) / 2
            if late_margin > early_margin + 1:
                margin_trend_score = 7
                margin_trend = "expanding"
            elif late_margin > early_margin - 1:
                margin_trend_score = 4
                margin_trend = "stable"
            else:
                margin_trend_score = 0
                margin_trend = "contracting"

    score = min(25, consistency_score + trend_score + margin_trend_score)
    label = (
        "High profitability" if score >= 20
        else "Moderate profitability" if score >= 12
        else "Low profitability" if score >= 5
        else "Unprofitable / declining"
    )

    return {
        "score": score,
        "label": label,
        "operating_income_trend": trend,
        "margin_trend": margin_trend,
    }


# ---------------------------------------------------------------------------
# Q3: Valuation — Forward PE (0–25)
# ---------------------------------------------------------------------------

def score_valuation(info: dict) -> dict:
    """
    Score valuation using forward PE vs sector median.
    Labels: Overpriced | Fairly priced | Below average
    """
    forward_pe = info.get("forwardPE") or info.get("trailingPE")
    sector = info.get("sector", "Unknown") or "Unknown"
    sector_median = SECTOR_PE_MEDIANS.get(sector, SECTOR_PE_MEDIANS["Unknown"])

    if forward_pe is None or not isinstance(forward_pe, (int, float)) or forward_pe <= 0:
        return {
            "score": 0,
            "label": "Data unavailable",
            "valuation_label": "Unknown",
            "forward_pe": None,
            "sector_median_pe": sector_median,
            "sector": sector,
        }

    # Negative PE (losses) treated as overpriced
    if forward_pe < 0:
        return {
            "score": 2,
            "label": "Negative PE (losses)",
            "valuation_label": "Overpriced",
            "forward_pe": round(forward_pe, 1),
            "sector_median_pe": sector_median,
            "sector": sector,
        }

    ratio = forward_pe / sector_median

    if ratio > 1.20:
        valuation_label = "Overpriced"
        score = max(0, round(25 - (ratio - 1.0) * 20))
    elif ratio < 0.80:
        valuation_label = "Below average"
        score = min(25, round(20 + (1.0 - ratio) * 20))
    else:
        valuation_label = "Fairly priced"
        # Closer to median = higher score within 15–20 range
        deviation = abs(ratio - 1.0) / 0.20
        score = round(20 - deviation * 5)

    score = max(0, min(25, score))

    return {
        "score": score,
        "label": f"Forward PE: {round(forward_pe, 1)} vs sector median {sector_median}",
        "valuation_label": valuation_label,
        "forward_pe": round(forward_pe, 1),
        "sector_median_pe": sector_median,
        "sector": sector,
    }


# ---------------------------------------------------------------------------
# Q4: Moat — numeric component (0–25); commentary added by moat.py
# ---------------------------------------------------------------------------

def score_moat_numeric(info: dict, quarterly_revenue: list[float], quarterly_gross_profit: list[float]) -> dict:
    """
    Score the moat numerically based on:
    - Gross margin percentile within sector (approximated via absolute thresholds)
    - ROIC vs 8% WACC proxy
    """
    sector = info.get("sector", "Unknown") or "Unknown"
    gross_margin = info.get("grossMargins")
    roe = info.get("returnOnEquity")

    # --- Gross margin score (0–12) ---
    # Sector-specific gross margin thresholds for "strong moat"
    SECTOR_GM_THRESHOLDS = {
        "Technology": (0.50, 0.70),
        "Communication Services": (0.45, 0.65),
        "Healthcare": (0.45, 0.65),
        "Consumer Defensive": (0.30, 0.50),
        "Consumer Cyclical": (0.25, 0.45),
        "Financials": (0.50, 0.70),
        "Financial Services": (0.50, 0.70),
        "Industrials": (0.25, 0.45),
        "Energy": (0.15, 0.35),
        "Utilities": (0.20, 0.40),
        "Basic Materials": (0.20, 0.40),
        "Real Estate": (0.35, 0.55),
        "Unknown": (0.35, 0.55),
    }

    gm_score = 0
    gm_pct = None
    if gross_margin is not None and isinstance(gross_margin, (int, float)):
        gm_pct = round(gross_margin * 100, 1)
        low_threshold, high_threshold = SECTOR_GM_THRESHOLDS.get(sector, (0.35, 0.55))
        if gross_margin >= high_threshold:
            gm_score = 12
        elif gross_margin >= low_threshold:
            gm_score = 8
        elif gross_margin >= low_threshold * 0.6:
            gm_score = 4
        else:
            gm_score = 1
    elif quarterly_revenue and quarterly_gross_profit and len(quarterly_revenue) >= 1 and len(quarterly_gross_profit) >= 1:
        # Approximate gross margin from quarterly data
        rev = quarterly_revenue[-1]
        gp = quarterly_gross_profit[-1]
        if rev and rev != 0:
            gm = gp / rev
            gm_pct = round(gm * 100, 1)
            low_threshold, high_threshold = SECTOR_GM_THRESHOLDS.get(sector, (0.35, 0.55))
            if gm >= high_threshold:
                gm_score = 12
            elif gm >= low_threshold:
                gm_score = 8
            else:
                gm_score = 3

    # --- ROIC proxy score (0–13) ---
    # Use returnOnEquity as ROIC proxy (yfinance rarely exposes ROIC directly)
    WACC = 0.08
    roic_score = 0
    roic_pct = None
    if roe is not None and isinstance(roe, (int, float)):
        roic_pct = round(roe * 100, 1)
        spread = roe - WACC
        if spread >= 0.20:
            roic_score = 13
        elif spread >= 0.10:
            roic_score = 10
        elif spread >= 0.05:
            roic_score = 7
        elif spread >= 0:
            roic_score = 4
        else:
            roic_score = 0

    score = min(25, gm_score + roic_score)

    # Revenue growth for moat prompt
    rev_growth = None
    if quarterly_revenue and len(quarterly_revenue) >= 5:
        old = quarterly_revenue[-5]
        new = quarterly_revenue[-1]
        if old and old != 0:
            rev_growth = round((new - old) / abs(old) * 100, 1)

    return {
        "score": score,
        "gross_margin": gm_pct,
        "roic": roic_pct,
        "revenue_growth_pct": rev_growth,
        "sector": sector,
        "commentary": None,  # filled by moat.py
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def score_stock(stock_data: dict) -> dict:
    """
    Run all 4 scoring dimensions on a single stock data dict.
    Returns a scored stock dict ready for output.
    """
    info = stock_data.get("info", {}) or {}
    quarterly_revenue = stock_data.get("quarterly_revenue", []) or []
    quarterly_op_income = stock_data.get("quarterly_op_income", []) or []
    quarterly_gross_profit = stock_data.get("quarterly_gross_profit", []) or []

    q1 = score_revenue_growth(quarterly_revenue)
    q2 = score_profitability(quarterly_op_income, quarterly_revenue)
    q3 = score_valuation(info)
    q4 = score_moat_numeric(info, quarterly_revenue, quarterly_gross_profit)

    total = q1["score"] + q2["score"] + q3["score"] + q4["score"]

    return {
        "ticker": stock_data["ticker"],
        "universe": stock_data.get("universe", "unknown"),
        "company_name": info.get("shortName") or info.get("longName") or stock_data["ticker"],
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "market_cap": info.get("marketCap"),
        "q1_revenue_growth": q1,
        "q2_profitability": q2,
        "q3_valuation": q3,
        "q4_moat": q4,
        "total_score": total,
        "quarterly_revenue": quarterly_revenue,
        "quarterly_revenue_dates": stock_data.get("quarterly_revenue_dates", []),
        "quarterly_op_income": quarterly_op_income,
    }
