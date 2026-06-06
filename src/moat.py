"""
Generates moat commentary for each stock using the Anthropic Claude API.
Reads the prompt template from moat_prompt.txt.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "moat_prompt.txt"

# Closest competitors by sector (for context injection)
SECTOR_COMPETITORS = {
    "Technology": "Microsoft, Apple, Alphabet, Samsung, ASML, TSMC",
    "Communication Services": "Alphabet, Meta, Comcast, AT&T, Disney",
    "Consumer Cyclical": "Amazon, Tesla, Home Depot, Nike, Booking Holdings",
    "Consumer Defensive": "Procter & Gamble, Nestlé, Unilever, Coca-Cola, PepsiCo",
    "Healthcare": "Johnson & Johnson, UnitedHealth, Pfizer, Roche, Novartis",
    "Financials": "JPMorgan, Bank of America, Visa, Mastercard, HDFC Bank",
    "Financial Services": "JPMorgan, Goldman Sachs, Visa, Mastercard, PayPal",
    "Industrials": "Caterpillar, Honeywell, Siemens, GE, 3M",
    "Energy": "ExxonMobil, Chevron, Shell, BP, TotalEnergies",
    "Utilities": "NextEra Energy, Duke Energy, Southern Company, Dominion, Exelon",
    "Basic Materials": "Rio Tinto, BHP, Linde, Air Products, Nucor",
    "Real Estate": "American Tower, Prologis, Crown Castle, Simon Property, Equity Residential",
    "Unknown": "sector peers",
}


def _load_prompt_template() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Could not load moat_prompt.txt (%s), using inline fallback", e)
        return (
            "You are a fundamental equity analyst. Assess the competitive moat of {ticker} "
            "({company_name}) in no more than 10 sentences. "
            "Gross margin: {gross_margin}%, ROIC: {roic}%, Revenue growth: {revenue_growth}%. "
            "Sector: {sector}. Competitors: {competitors}. "
            "No headings, no bullet points, plain paragraph only."
        )


def generate_moat_commentary(scored_stock: dict, api_key: str) -> str:
    """
    Call Claude to generate a moat commentary for a single stock.
    Returns the commentary string, or a fallback message on error.
    """
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return "Moat commentary unavailable."

    q4 = scored_stock.get("q4_moat", {})
    ticker = scored_stock.get("ticker", "?")
    company_name = scored_stock.get("company_name", ticker)
    sector = scored_stock.get("sector", "Unknown")
    gross_margin = q4.get("gross_margin") or "N/A"
    roic = q4.get("roic") or "N/A"
    revenue_growth = q4.get("revenue_growth_pct") or "N/A"
    competitors = SECTOR_COMPETITORS.get(sector, SECTOR_COMPETITORS["Unknown"])

    template = _load_prompt_template()
    prompt = template.format(
        ticker=ticker,
        company_name=company_name,
        gross_margin=gross_margin,
        roic=roic,
        revenue_growth=revenue_growth,
        sector=sector,
        competitors=competitors,
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        commentary = message.content[0].text.strip()
        # Enforce ≤10 sentences as a safety net
        sentences = commentary.split(". ")
        if len(sentences) > 10:
            commentary = ". ".join(sentences[:10]) + "."
        logger.info("%s: Moat commentary generated (%d chars)", ticker, len(commentary))
        return commentary
    except Exception as e:
        logger.error("%s: Claude API call failed: %s", ticker, e)
        return "Moat commentary unavailable."


def enrich_moat_commentary(scored_stocks: list[dict], api_key: str) -> list[dict]:
    """
    Mutates each stock dict in-place to add commentary to q4_moat['commentary'].
    """
    total = len(scored_stocks)
    for i, stock in enumerate(scored_stocks):
        ticker = stock.get("ticker", "?")
        logger.info("[%d/%d] Generating moat commentary for %s", i + 1, total, ticker)
        commentary = generate_moat_commentary(stock, api_key)
        stock["q4_moat"]["commentary"] = commentary
    return scored_stocks
