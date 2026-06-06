# Stock Screener — NASDAQ 100 & Nifty 100

A Python-based stock screening agent that scores ~200 stocks across 4 dimensions, generates AI-powered moat commentary via Claude, and publishes a live HTML dashboard to GitHub Pages.

---

## Architecture

```
workflow_dispatch
     │
     ▼
src/main.py  ──►  fetcher.py   (yfinance: NASDAQ 100 + Nifty 100)
                  scorer.py    (Q1 Revenue, Q2 Profitability, Q3 Valuation, Q4 Moat numeric)
                  moat.py      (Claude API → ≤10-sentence moat commentary)
                  gdrive.py    (upload scored_stocks.json + dated snapshot)
                  dashboard.py (generate docs/index.html → GitHub Pages)
```

---

## One-time setup

### 1. Fork or clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/stock_screener.git
cd stock_screener
```

### 2. Enable GitHub Pages

1. Go to your repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` | Folder: `/docs`
4. Save — your dashboard will be live at `https://YOUR_USERNAME.github.io/stock_screener/`

### 3. Create a Google Cloud service account

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **IAM & Admin → Service Accounts**
2. Create a new service account (e.g. `stock-screener-bot`)
3. Grant it no project roles (Drive access is folder-level)
4. Create a JSON key and download it

### 4. Enable Google Drive API & share your folder

1. In Google Cloud Console → **APIs & Services → Enable APIs** → enable **Google Drive API**
2. Create (or choose) a folder in Google Drive
3. Share that folder with the service account email (e.g. `stock-screener-bot@project.iam.gserviceaccount.com`) with **Editor** access
4. Copy the folder ID from the Drive URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

### 5. Add GitHub Actions secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com) |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | The **entire contents** of the service account JSON key file |
| `GDRIVE_FOLDER_ID` | The Google Drive folder ID (from the Drive URL) |

---

## Triggering a run

### Option A — GitHub UI

1. Go to your repo → **Actions**
2. Click **"Run stock screener"** in the left sidebar
3. Click **"Run workflow"** → **Run workflow**
4. The workflow fetches ~200 stocks, scores them, calls Claude for moat commentary, uploads to Drive, and commits the updated dashboard.

### Option B — Claude Code / GitHub MCP

In Claude chat with GitHub MCP configured:

```
Trigger the run-stock-screener workflow in my stock_screener repo
```

---

## Scoring dimensions

| Question | Max | What it measures |
|---|---|---|
| Q1 Revenue Growth | 25 | 10Q revenue CAGR, YoY consistency, acceleration/deceleration |
| Q2 Profitability | 25 | Operating income trend, margin expansion, positive OI consistency |
| Q3 Valuation | 25 | Forward PE vs sector median (Overpriced / Fairly priced / Below average) |
| Q4 Moat | 25 | Gross margin vs sector thresholds, ROIC vs 8% WACC + Claude commentary |

**Total: 100 points**

Dashboard colour coding: ≥80% of max → green | 40–79% → amber | <40% → red

---

## Extending the agent

### Add a new scoring dimension

Edit `src/scorer.py`. Add a new function `score_YOUR_DIMENSION(...)` following the same pattern as `score_revenue_growth`. Return a dict with at least `{"score": int, "label": str}`. Call it from `score_stock()` and add it to the returned dict. Update `src/dashboard.py` to display it.

### Change the moat prompt

Edit `moat_prompt.txt` directly — no code change needed. The file is read at runtime. Available template variables: `{ticker}`, `{company_name}`, `{gross_margin}`, `{roic}`, `{revenue_growth}`, `{sector}`, `{competitors}`.

### Add a new stock universe

Edit `src/fetcher.py` → `fetch_universe()`. Add a new key to the returned dict with a list of tickers. For Indian stocks, append `.NS`; for US stocks use bare tickers. The rest of the pipeline handles it automatically.

### Change the Claude model

Edit `src/moat.py` → `generate_moat_commentary()`, update the `model=` argument.

---

## Local development

```bash
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export GDRIVE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
export GDRIVE_FOLDER_ID=your_folder_id

# Run the full pipeline
python src/main.py

# Open the dashboard locally
open docs/index.html
```

---

## Output files

| File | Description |
|---|---|
| `scored_stocks.json` | Full scored output, committed to repo each run |
| `docs/index.html` | Live HTML dashboard, committed to repo each run |
| Google Drive: `scored_stocks.json` | Always-current version in your Drive folder |
| Google Drive: `history/YYYY-MM-DD_scored_stocks.json` | Dated snapshot per run |

---

## Required GitHub Actions secrets checklist

Before your first run, ensure all 3 secrets are set:

- [ ] `ANTHROPIC_API_KEY` — Anthropic API key for Claude moat commentary
- [ ] `GDRIVE_SERVICE_ACCOUNT_JSON` — Google Cloud service account JSON key (full file contents)
- [ ] `GDRIVE_FOLDER_ID` — Google Drive folder ID where outputs are saved
