"""
Generates docs/index.html — a fully self-contained HTML dashboard.
All JS and CSS are inlined; stock data is embedded as a JS variable.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent / "docs"

BRAND = {
    "purple": "#59058F",
    "teal": "#00A8A8",
    "blue": "#0388BC",
    "navy": "#180D5B",
}


def _fmt_score(score, max_score=25):
    if score is None:
        return 0
    return max(0, min(max_score, int(score)))


def _color_class(score, max_score=25):
    pct = score / max_score if max_score else 0
    if pct >= 0.8:
        return "score-green"
    elif pct >= 0.4:
        return "score-amber"
    else:
        return "score-red"


def _safe_val(val, fmt=None):
    if val is None:
        return "N/A"
    if fmt == "pct":
        return f"{val:.1f}%"
    if fmt == "pe":
        return f"{val:.1f}x"
    return str(val)


def generate_html(scored_stocks: list[dict], run_timestamp: str | None = None) -> str:
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Prepare slim data for embedding
    table_rows = []
    for s in scored_stocks:
        q1 = s.get("q1_revenue_growth", {})
        q2 = s.get("q2_profitability", {})
        q3 = s.get("q3_valuation", {})
        q4 = s.get("q4_moat", {})
        row = {
            "ticker": s.get("ticker", ""),
            "company": s.get("company_name", s.get("ticker", "")),
            "sector": s.get("sector", "Unknown"),
            "universe": s.get("universe", ""),
            "q1": _fmt_score(q1.get("score")),
            "q2": _fmt_score(q2.get("score")),
            "q3": _fmt_score(q3.get("score")),
            "q4": _fmt_score(q4.get("score")),
            "total": _fmt_score(s.get("total_score", 0), 100),
            "valuation_label": q3.get("valuation_label", "Unknown"),
            "forward_pe": q3.get("forward_pe"),
            "sector_median_pe": q3.get("sector_median_pe"),
            "cagr": q1.get("cagr"),
            "rev_trend": q1.get("trend", ""),
            "margin_trend": q2.get("margin_trend", ""),
            "gross_margin": q4.get("gross_margin"),
            "roic": q4.get("roic"),
            "commentary": q4.get("commentary") or "Moat commentary unavailable.",
            "quarterly_revenue": s.get("quarterly_revenue", []),
            "quarterly_revenue_dates": s.get("quarterly_revenue_dates", []),
            "quarterly_op_income": s.get("quarterly_op_income", []),
            "q1_label": q1.get("label", ""),
            "q2_label": q2.get("label", ""),
            "yoy_consistency": q1.get("yoy_consistency", ""),
        }
        table_rows.append(row)

    data_json = json.dumps(table_rows, indent=None, default=str)
    total_stocks = len(scored_stocks)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Stock Screener — NASDAQ 100 &amp; Nifty 100</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f1a;color:#e8e8f0;font-size:14px}}
a{{color:{BRAND['teal']};text-decoration:none}}
header{{background:linear-gradient(135deg,{BRAND['navy']} 0%,{BRAND['purple']} 100%);padding:24px 32px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
header h1{{font-size:1.5rem;font-weight:700;color:#fff;letter-spacing:-0.3px}}
.meta{{font-size:0.8rem;color:#b8b8d0;display:flex;gap:20px;flex-wrap:wrap}}
.meta span{{display:flex;align-items:center;gap:4px}}
.container{{max-width:1400px;margin:0 auto;padding:20px 16px}}
.filters{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.filter-btn{{padding:6px 16px;border-radius:20px;border:1px solid #333;background:#1a1a2e;color:#b8b8d0;cursor:pointer;font-size:0.8rem;transition:all .2s}}
.filter-btn:hover,.filter-btn.active{{background:{BRAND['teal']};border-color:{BRAND['teal']};color:#fff}}
.table-wrap{{overflow-x:auto;border-radius:10px;border:1px solid #222}}
table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
thead{{background:#1a1a2e;position:sticky;top:0;z-index:5}}
th{{padding:10px 12px;text-align:left;color:#8888aa;font-weight:600;cursor:pointer;white-space:nowrap;user-select:none;border-bottom:1px solid #2a2a40}}
th:hover{{color:{BRAND['teal']}}}
th .sort-icon{{margin-left:4px;opacity:0.5;font-size:0.7rem}}
th.sorted .sort-icon{{opacity:1;color:{BRAND['teal']}}}
tbody tr{{border-bottom:1px solid #1e1e30;transition:background .15s;cursor:pointer}}
tbody tr:hover{{background:#1e1e32}}
tbody tr.expanded{{background:#1e1e40}}
td{{padding:9px 12px;vertical-align:middle}}
.ticker{{font-weight:700;color:{BRAND['teal']};font-family:monospace;font-size:0.9rem}}
.universe-badge{{font-size:0.65rem;padding:2px 6px;border-radius:10px;font-weight:600;margin-left:6px}}
.badge-nasdaq{{background:#1a3050;color:{BRAND['blue']}}}
.badge-nifty{{background:#1a2e1a;color:#4caf50}}
.score-cell{{font-weight:700;border-radius:4px;padding:4px 8px;text-align:center;min-width:44px}}
.score-green{{background:#0d3321;color:#4caf50}}
.score-amber{{background:#2e2000;color:#f59e0b}}
.score-red{{background:#2e0d0d;color:#ef4444}}
.total-score{{font-weight:800;font-size:1rem}}
.val-label{{font-size:0.7rem;padding:2px 8px;border-radius:10px;font-weight:600;white-space:nowrap}}
.val-Overpriced{{background:#3d0d0d;color:#ef4444}}
.val-Fairly.priced,.val-Fairly_priced{{background:#0d2a0d;color:#4caf50}}
.val-Below.average,.val-Below_average{{background:#0d1e3d;color:{BRAND['blue']}}}
.val-Unknown{{background:#1e1e2e;color:#666}}
.detail-row td{{padding:0;background:#12121e!important}}
.detail-row td>div{{padding:20px 24px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;border-top:2px solid {BRAND['purple']}}}
@media(max-width:900px){{.detail-row td>div{{grid-template-columns:1fr 1fr}}}}
@media(max-width:600px){{.detail-row td>div{{grid-template-columns:1fr}}}}
.detail-card{{background:#1a1a2e;border-radius:8px;padding:16px}}
.detail-card h4{{font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;color:{BRAND['teal']};margin-bottom:12px}}
.moat-card{{grid-column:1/-1}}
.moat-text{{line-height:1.7;color:#c8c8e0;font-size:0.88rem}}
svg.chart{{width:100%;overflow:visible}}
.bar{{transition:opacity .2s}}
.bar:hover{{opacity:0.8}}
.chart-label{{font-size:9px;fill:#666}}
.axis-line{{stroke:#333;stroke-width:1}}
.stat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.stat-item{{background:#12121e;border-radius:6px;padding:10px}}
.stat-label{{font-size:0.7rem;color:#6666aa;margin-bottom:2px}}
.stat-value{{font-weight:700;color:#e8e8f0}}
.pe-bar-wrap{{margin-top:8px}}
.pe-label{{font-size:0.7rem;color:#888;margin-bottom:4px}}
.pe-track{{height:12px;background:#1e1e30;border-radius:6px;overflow:visible;position:relative;margin-bottom:8px}}
.pe-fill{{height:100%;border-radius:6px;position:absolute;top:0;left:0}}
.pe-median-line{{position:absolute;top:-4px;bottom:-4px;width:2px;background:#fff;border-radius:2px}}
.no-data{{color:#444;font-style:italic;font-size:0.8rem}}
</style>
</head>
<body>
<header>
  <h1>Stock Screener — NASDAQ 100 &amp; Nifty 100</h1>
  <div class="meta">
    <span>Last run: <strong id="run-ts">{run_timestamp}</strong></span>
    <span>Stocks screened: <strong>{total_stocks}</strong></span>
  </div>
</header>
<div class="container">
  <div class="filters" id="filters">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="nasdaq100">NASDAQ 100</button>
    <button class="filter-btn" data-filter="nifty100">Nifty 100</button>
    <button class="filter-btn" data-filter="70">Score &ge; 70</button>
    <button class="filter-btn" data-filter="85">Score &ge; 85</button>
  </div>
  <div class="table-wrap">
    <table id="mainTable">
      <thead>
        <tr>
          <th data-col="ticker">Ticker <span class="sort-icon">&#8597;</span></th>
          <th data-col="company">Company <span class="sort-icon">&#8597;</span></th>
          <th data-col="sector">Sector <span class="sort-icon">&#8597;</span></th>
          <th data-col="q1">Q1 Growth /25 <span class="sort-icon">&#8597;</span></th>
          <th data-col="q2">Q2 Profit /25 <span class="sort-icon">&#8597;</span></th>
          <th data-col="q3">Q3 Value /25 <span class="sort-icon">&#8597;</span></th>
          <th data-col="q4">Q4 Moat /25 <span class="sort-icon">&#8597;</span></th>
          <th data-col="total">Total /100 <span class="sort-icon">&#8597;</span></th>
          <th data-col="valuation_label">Valuation <span class="sort-icon">&#8597;</span></th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
</div>
<script>
const STOCKS = {data_json};
let currentFilter = 'all';
let sortCol = 'total';
let sortDir = -1;
let expandedTicker = null;

function scoreClass(score, max) {{
  const p = score / max;
  if (p >= 0.8) return 'score-green';
  if (p >= 0.4) return 'score-amber';
  return 'score-red';
}}

function valLabelClass(label) {{
  return 'val-label val-' + (label || 'Unknown').replace(/ /g, '_');
}}

function filteredStocks() {{
  return STOCKS.filter(s => {{
    if (currentFilter === 'nasdaq100') return s.universe === 'nasdaq100';
    if (currentFilter === 'nifty100') return s.universe === 'nifty100';
    if (currentFilter === '70') return s.total >= 70;
    if (currentFilter === '85') return s.total >= 85;
    return true;
  }});
}}

function sorted(arr) {{
  return [...arr].sort((a, b) => {{
    const va = a[sortCol], vb = b[sortCol];
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sortDir;
    return String(va || '').localeCompare(String(vb || '')) * sortDir;
  }});
}}

function svgBarChart(values, dates, color) {{
  if (!values || values.length === 0) return '<div class="no-data">No data available</div>';
  const W = 300, H = 100, pad = 20;
  const max = Math.max(...values.map(Math.abs), 1);
  const n = values.length;
  const bw = Math.floor((W - pad * 2) / n) - 2;
  let bars = '', labels = '';
  values.forEach((v, i) => {{
    const bh = Math.max(2, Math.abs(v) / max * (H - pad - 10));
    const x = pad + i * ((W - pad * 2) / n);
    const y = v >= 0 ? H - pad - bh : H - pad;
    const fill = v >= 0 ? color : '#ef4444';
    bars += `<rect class="bar" x="${{x}}" y="${{y}}" width="${{bw}}" height="${{bh}}" fill="${{fill}}" rx="2"/>`;
    if (dates && dates[i]) {{
      const lbl = dates[i].substring(2, 7);
      labels += `<text class="chart-label" x="${{x + bw/2}}" y="${{H - 2}}" text-anchor="middle">${{lbl}}</text>`;
    }}
  }});
  return `<svg class="chart" viewBox="0 0 ${{W}} ${{H}}">
    <line class="axis-line" x1="${{pad}}" y1="${{H-pad}}" x2="${{W-pad}}" y2="${{H-pad}}"/>
    ${{bars}}${{labels}}
  </svg>`;
}}

function svgLineChart(values, color) {{
  if (!values || values.length < 2) return '<div class="no-data">No data available</div>';
  const W = 300, H = 100, pad = 20;
  const min = Math.min(...values), max = Math.max(...values, min + 1);
  const n = values.length;
  const xs = values.map((_, i) => pad + i * (W - pad * 2) / (n - 1));
  const ys = values.map(v => H - pad - (v - min) / (max - min) * (H - pad * 2));
  const pts = xs.map((x, i) => `${{x}},${{ys[i]}}`).join(' ');
  const area = `${{xs[0]}},${{H - pad}} ` + pts + ` ${{xs[xs.length-1]}},${{H-pad}}`;
  return `<svg class="chart" viewBox="0 0 ${{W}} ${{H}}">
    <line class="axis-line" x1="${{pad}}" y1="${{H-pad}}" x2="${{W-pad}}" y2="${{H-pad}}"/>
    <polygon points="${{area}}" fill="${{color}}" opacity="0.15"/>
    <polyline points="${{pts}}" fill="none" stroke="${{color}}" stroke-width="2" stroke-linejoin="round"/>
  </svg>`;
}}

function peBarHtml(fpe, median) {{
  if (!fpe || !median) return '<div class="no-data">No data available</div>';
  const maxPE = Math.max(fpe, median) * 1.5;
  const stockPct = Math.min(98, (fpe / maxPE) * 100);
  const medPct = Math.min(98, (median / maxPE) * 100);
  const stockColor = fpe > median * 1.2 ? '#ef4444' : fpe < median * 0.8 ? '#0388BC' : '#4caf50';
  return `
    <div class="pe-bar-wrap">
      <div class="pe-label">Stock PE: <strong>${{fpe.toFixed(1)}}x</strong></div>
      <div class="pe-track">
        <div class="pe-fill" style="width:${{stockPct}}%;background:${{stockColor}};height:100%"></div>
        <div class="pe-median-line" style="left:${{medPct}}%"></div>
      </div>
      <div class="pe-label">Sector median: <strong>${{median.toFixed(1)}}x</strong></div>
      <div class="pe-track">
        <div class="pe-fill" style="width:${{medPct}}%;background:#888;height:100%"></div>
      </div>
    </div>`;
}}

function detailHtml(s) {{
  const revenueChart = svgBarChart(s.quarterly_revenue, s.quarterly_revenue_dates, '#00A8A8');
  const oiChart = svgLineChart(s.quarterly_op_income, '#59058F');
  const peHtml = peBarHtml(s.forward_pe, s.sector_median_pe);
  return `<div>
    <div class="detail-card">
      <h4>Q1 — Revenue (last 10 quarters)</h4>
      ${{revenueChart}}
      <div class="stat-grid" style="margin-top:10px">
        <div class="stat-item"><div class="stat-label">CAGR</div><div class="stat-value">${{s.cagr != null ? s.cagr + '%' : 'N/A'}}</div></div>
        <div class="stat-item"><div class="stat-label">Trend</div><div class="stat-value">${{s.rev_trend || 'N/A'}}</div></div>
        <div class="stat-item"><div class="stat-label">YoY Positive</div><div class="stat-value">${{s.yoy_consistency || 'N/A'}}</div></div>
        <div class="stat-item"><div class="stat-label">Label</div><div class="stat-value" style="font-size:.75rem">${{s.q1_label || 'N/A'}}</div></div>
      </div>
    </div>
    <div class="detail-card">
      <h4>Q2 — Operating Income Trend</h4>
      ${{oiChart}}
      <div class="stat-grid" style="margin-top:10px">
        <div class="stat-item"><div class="stat-label">Margin Trend</div><div class="stat-value">${{s.margin_trend || 'N/A'}}</div></div>
        <div class="stat-item"><div class="stat-label">Label</div><div class="stat-value" style="font-size:.75rem">${{s.q2_label || 'N/A'}}</div></div>
      </div>
    </div>
    <div class="detail-card">
      <h4>Q3 — Valuation vs Sector Median</h4>
      ${{peHtml}}
      <div class="stat-grid" style="margin-top:10px">
        <div class="stat-item"><div class="stat-label">Gross Margin</div><div class="stat-value">${{s.gross_margin != null ? s.gross_margin + '%' : 'N/A'}}</div></div>
        <div class="stat-item"><div class="stat-label">ROIC (proxy)</div><div class="stat-value">${{s.roic != null ? s.roic + '%' : 'N/A'}}</div></div>
      </div>
    </div>
    <div class="detail-card moat-card">
      <h4>Q4 — Competitive Moat Commentary</h4>
      <p class="moat-text">${{s.commentary}}</p>
    </div>
  </div>`;
}}

function renderTable() {{
  const tbody = document.getElementById('tableBody');
  const data = sorted(filteredStocks());
  let html = '';
  data.forEach(s => {{
    const isExpanded = s.ticker === expandedTicker;
    html += `<tr class="${{isExpanded ? 'expanded' : ''}}" onclick="toggleDetail('${{s.ticker}}')">
      <td class="ticker">${{s.ticker}}<span class="universe-badge badge-${{s.universe}}">${{s.universe === 'nasdaq100' ? 'NDQ' : 'NSE'}}</span></td>
      <td>${{s.company}}</td>
      <td style="color:#888">${{s.sector}}</td>
      <td><span class="score-cell ${{scoreClass(s.q1, 25)}}">${{s.q1}}</span></td>
      <td><span class="score-cell ${{scoreClass(s.q2, 25)}}">${{s.q2}}</span></td>
      <td><span class="score-cell ${{scoreClass(s.q3, 25)}}">${{s.q3}}</span></td>
      <td><span class="score-cell ${{scoreClass(s.q4, 25)}}">${{s.q4}}</span></td>
      <td><span class="score-cell total-score ${{scoreClass(s.total, 100)}}">${{s.total}}</span></td>
      <td><span class="${{valLabelClass(s.valuation_label)}}">${{s.valuation_label}}</span></td>
    </tr>`;
    if (isExpanded) {{
      html += `<tr class="detail-row"><td colspan="9"><div>${{detailHtml(s)}}</div></td></tr>`;
    }}
  }});
  tbody.innerHTML = html;
}}

function toggleDetail(ticker) {{
  expandedTicker = expandedTicker === ticker ? null : ticker;
  renderTable();
}}

// Sorting
document.querySelectorAll('th[data-col]').forEach(th => {{
  th.addEventListener('click', () => {{
    const col = th.dataset.col;
    if (sortCol === col) {{ sortDir *= -1; }} else {{ sortCol = col; sortDir = -1; }}
    document.querySelectorAll('th').forEach(t => t.classList.remove('sorted'));
    th.classList.add('sorted');
    th.querySelector('.sort-icon').textContent = sortDir === 1 ? '\\u2191' : '\\u2193';
    renderTable();
  }});
}});

// Filters
document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    currentFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderTable();
  }});
}});

renderTable();
</script>
</body>
</html>"""
    return html


def write_dashboard(scored_stocks: list[dict], run_timestamp: str | None = None):
    """Write the HTML dashboard to docs/index.html."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    html = generate_html(scored_stocks, run_timestamp)
    out_path = DOCS_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("Dashboard written to %s (%d bytes)", out_path, len(html))
    return str(out_path)
