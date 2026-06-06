"""
Orchestrator: runs the full stock screening pipeline.

Pipeline:
  1. Fetch stock universe (NASDAQ 100 + Nifty 100)
  2. Fetch financial data for each ticker
  3. Score each stock (Q1–Q4 numeric)
  4. Enrich Q4 with Claude moat commentary
  5. Write scored_stocks.json locally
  6. Upload to Google Drive
  7. Generate docs/index.html dashboard
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent


def main():
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("=== Stock Screener Run started at %s ===", run_ts)

    # --- Step 1: Fetch universe ---
    from fetcher import fetch_universe, fetch_all_stocks

    universe = fetch_universe()
    logger.info(
        "Universe: %d NASDAQ 100 + %d Nifty 100 tickers",
        len(universe["nasdaq100"]),
        len(universe["nifty100"]),
    )

    # --- Step 2: Fetch financial data ---
    raw_stocks = fetch_all_stocks(universe)
    if not raw_stocks:
        logger.error("No stock data fetched — aborting")
        sys.exit(1)
    logger.info("Fetched data for %d stocks", len(raw_stocks))

    # --- Step 3: Score each stock ---
    from scorer import score_stock

    scored = []
    for raw in raw_stocks:
        try:
            s = score_stock(raw)
            scored.append(s)
        except Exception as e:
            logger.error("Scoring failed for %s: %s", raw.get("ticker", "?"), e)

    logger.info("Scored %d stocks", len(scored))
    scored.sort(key=lambda s: s["total_score"], reverse=True)

    # --- Step 4: Moat commentary ---
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        from moat import enrich_moat_commentary
        scored = enrich_moat_commentary(scored, api_key)
    else:
        logger.warning("ANTHROPIC_API_KEY not set — skipping moat commentary")
        for s in scored:
            s["q4_moat"]["commentary"] = "Moat commentary unavailable (API key not configured)."

    # --- Step 5: Write JSON locally ---
    out_path = ROOT / "scored_stocks.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2, default=str)
    logger.info("Wrote %s (%d stocks)", out_path, len(scored))

    # --- Step 6: Upload to Google Drive ---
    try:
        from gdrive import upload_to_drive
        success = upload_to_drive(scored)
        if not success:
            logger.warning("Google Drive upload skipped or failed — continuing")
    except Exception as e:
        logger.error("Google Drive step raised an exception: %s — continuing", e)

    # --- Step 7: Generate dashboard ---
    try:
        from dashboard import write_dashboard
        write_dashboard(scored, run_timestamp=run_ts)
    except Exception as e:
        logger.error("Dashboard generation failed: %s", e)
        sys.exit(1)

    logger.info("=== Run complete. %d stocks processed ===", len(scored))


if __name__ == "__main__":
    main()
