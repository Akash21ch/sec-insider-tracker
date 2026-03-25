"""
build_site.py
Reads data/trades_with_returns.csv and regenerates index.html.
Run this after collecting new company data:
    python build_site.py
"""

import csv
import json
import os

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, "data", "trades_with_returns.csv")
OUT_FILE  = os.path.join(ROOT, "index.html")

# ── Load & clean data ─────────────────────────────────────────────────────────
rows = list(csv.DictReader(open(DATA_FILE)))

trades = []
for r in rows:
    trades.append({
        "ticker":  r["ticker"],
        "company": r["company_name"],
        "insider": r["insider_name"].title(),
        "role":    r["role_type"],
        "date":    r["transaction_date"],
        "type":    r["transaction_type"],
        "shares":  float(r["shares"]) if r["shares"] else 0,
        "price":   round(float(r["price_on_trade_date"]), 2) if r["price_on_trade_date"] else 0,
        "r30":     float(r["return_30d"])  if r["return_30d"]  else 0,
        "r60":     float(r["return_60d"])  if r["return_60d"]  else 0,
        "r90":     float(r["return_90d"])  if r["return_90d"]  else 0,
        "sector":  r["sector"],
        "cap":     r["cap_size"],
    })

# ── Compute stats ─────────────────────────────────────────────────────────────
def avg(lst, key):
    vals = [t[key] for t in lst]
    return round(sum(vals) / len(vals), 2) if vals else 0

total      = len(trades)
buys       = [t for t in trades if t["type"] == "A"]
sells      = [t for t in trades if t["type"] == "D"]
companies  = len(set(t["ticker"] for t in trades))

buy30      = avg(buys, "r30")
buy90      = avg(buys, "r90")
win_count  = sum(1 for t in buys if t["r30"] > 0)
win_pct    = round(win_count / len(buys) * 100) if buys else 0

date_range_start = min(t["date"] for t in trades)
date_range_end   = max(t["date"] for t in trades)
year_start       = date_range_start[:4]
year_end         = date_range_end[:4]

data_json = json.dumps(trades, separators=(",", ":"))

# ── HTML template ─────────────────────────────────────────────────────────────
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEC Insider Trading Tracker</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2236;
    --border: #1f2d47;
    --text: #e2e8f0;
    --muted: #64748b;
    --buy: #22c55e;
    --sell: #ef4444;
    --accent: #3b82f6;
    --accent2: #8b5cf6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14px; min-height: 100vh; }}

  /* Nav */
  nav {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 56px; position: sticky; top: 0; z-index: 100; }}
  .nav-brand {{ font-size: 16px; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 8px; }}
  .nav-links {{ display: flex; gap: 24px; }}
  .nav-links a {{ color: var(--muted); text-decoration: none; font-size: 13px; transition: color .2s; }}
  .nav-links a:hover {{ color: var(--text); }}

  /* Hero */
  .hero {{ background: linear-gradient(135deg, #0a0e1a 0%, #0f172a 50%, #0a0e1a 100%); border-bottom: 1px solid var(--border); padding: 60px 24px 48px; text-align: center; }}
  .hero h1 {{ font-size: 36px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 12px; }}
  .hero h1 span {{ background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .hero p {{ color: var(--muted); font-size: 16px; max-width: 560px; margin: 0 auto 36px; line-height: 1.6; }}
  .hero-badge {{ display: inline-flex; align-items: center; gap: 6px; background: rgba(59,130,246,.12); border: 1px solid rgba(59,130,246,.3); color: var(--accent); padding: 4px 12px; border-radius: 100px; font-size: 12px; font-weight: 600; margin-bottom: 20px; }}

  /* Stats bar */
  .stats-bar {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--border); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }}
  .stat {{ background: var(--surface); padding: 20px 24px; text-align: center; }}
  .stat-value {{ font-size: 28px; font-weight: 800; }}
  .stat-label {{ color: var(--muted); font-size: 12px; margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }}

  /* Main layout */
  .container {{ max-width: 1280px; margin: 0 auto; padding: 32px 24px; }}
  .section-title {{ font-size: 18px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
  .section-title::before {{ content: ""; width: 3px; height: 18px; background: var(--accent); border-radius: 2px; }}

  /* Charts row */
  .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px; }}
  .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
  .chart-card h3 {{ font-size: 14px; font-weight: 600; color: var(--muted); margin-bottom: 16px; text-transform: uppercase; letter-spacing: .5px; }}
  .chart-wrap {{ position: relative; height: 260px; }}

  /* Insight cards */
  .insight-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }}
  .insight-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
  .insight-card .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .6px; color: var(--muted); margin-bottom: 8px; }}
  .insight-card .big {{ font-size: 32px; font-weight: 800; }}
  .insight-card .sub {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}

  /* Table */
  .table-controls {{ display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
  .search-box {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 8px; font-size: 13px; width: 220px; outline: none; transition: border-color .2s; }}
  .search-box:focus {{ border-color: var(--accent); }}
  select.filter {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 8px; font-size: 13px; outline: none; cursor: pointer; }}
  select.filter:focus {{ border-color: var(--accent); }}
  .table-wrap {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead {{ background: var(--surface2); }}
  th {{ padding: 12px 16px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .6px; color: var(--muted); font-weight: 600; white-space: nowrap; cursor: pointer; user-select: none; }}
  th:hover {{ color: var(--text); }}
  th.sorted {{ color: var(--accent); }}
  td {{ padding: 11px 16px; border-top: 1px solid var(--border); white-space: nowrap; }}
  tr:hover td {{ background: rgba(59,130,246,.04); }}
  .badge {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 100px; font-size: 11px; font-weight: 600; }}
  .badge-buy {{ background: rgba(34,197,94,.15); color: var(--buy); }}
  .badge-sell {{ background: rgba(239,68,68,.15); color: var(--sell); }}
  .badge-ceo {{ background: rgba(139,92,246,.15); color: #a78bfa; }}
  .badge-cfo {{ background: rgba(59,130,246,.15); color: #60a5fa; }}
  .pos {{ color: var(--buy); }}
  .neg {{ color: var(--sell); }}
  .neu {{ color: var(--muted); }}
  .pagination {{ display: flex; align-items: center; gap: 8px; padding: 14px 16px; border-top: 1px solid var(--border); justify-content: space-between; }}
  .page-info {{ color: var(--muted); font-size: 13px; }}
  .page-btns {{ display: flex; gap: 4px; }}
  .page-btn {{ background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all .2s; }}
  .page-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .page-btn:disabled {{ opacity: .4; cursor: not-allowed; }}

  /* Footer */
  footer {{ border-top: 1px solid var(--border); padding: 32px 24px; text-align: center; color: var(--muted); font-size: 13px; }}
  footer a {{ color: var(--accent); text-decoration: none; }}

  @media (max-width: 900px) {{
    .charts-row {{ grid-template-columns: 1fr; }}
    .insight-grid {{ grid-template-columns: 1fr 1fr; }}
    .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  @media (max-width: 600px) {{
    .insight-grid {{ grid-template-columns: 1fr; }}
    .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
    .hero h1 {{ font-size: 26px; }}
    .nav-links {{ display: none; }}
  }}
</style>
</head>
<body>

<nav>
  <div class="nav-brand">SEC Insider Tracker</div>
  <div class="nav-links">
    <a href="#insights">Insights</a>
    <a href="#charts">Charts</a>
    <a href="#trades">All Trades</a>
  </div>
</nav>

<div class="hero">
  <div class="hero-badge">Real SEC EDGAR Data</div>
  <h1>CEO &amp; CFO <span>Insider Trading</span> Analysis</h1>
  <p>Tracking executive buy and sell signals across {companies} S&amp;P 500 companies from {year_start} to {year_end} &mdash; do insiders know something the market doesn&#39;t?</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-value">{total:,}</div><div class="stat-label">Total Trades</div></div>
  <div class="stat"><div class="stat-value" style="color:var(--buy)">{len(buys):,}</div><div class="stat-label">Buy Transactions</div></div>
  <div class="stat"><div class="stat-value" style="color:var(--sell)">{len(sells):,}</div><div class="stat-label">Sell Transactions</div></div>
  <div class="stat"><div class="stat-value">{companies}</div><div class="stat-label">Companies Tracked</div></div>
</div>

<div class="container">

  <!-- Key Insights -->
  <div id="insights">
    <div class="section-title">Key Findings</div>
    <div class="insight-grid">
      <div class="insight-card">
        <div class="label">Avg Return After Buy (30 days)</div>
        <div class="big pos">{f"+{buy30}%" if buy30 >= 0 else f"{buy30}%"}</div>
        <div class="sub">Based on {len(buys):,} buy transactions</div>
      </div>
      <div class="insight-card">
        <div class="label">Avg Return After Buy (90 days)</div>
        <div class="big pos">{f"+{buy90}%" if buy90 >= 0 else f"{buy90}%"}</div>
        <div class="sub">Strongest signal at 3-month horizon</div>
      </div>
      <div class="insight-card">
        <div class="label">Buys with Positive 30-Day Return</div>
        <div class="big pos">{win_pct}%</div>
        <div class="sub">{win_count:,} out of {len(buys):,} buy trades gained</div>
      </div>
    </div>
  </div>

  <!-- Charts -->
  <div id="charts">
    <div class="section-title">Return Analysis</div>
    <div class="charts-row">
      <div class="chart-card">
        <h3>Avg Returns: Buys vs Sells</h3>
        <div class="chart-wrap"><canvas id="chart-buysell"></canvas></div>
      </div>
      <div class="chart-card">
        <h3>Avg 30-Day Return by Sector</h3>
        <div class="chart-wrap"><canvas id="chart-sector"></canvas></div>
      </div>
    </div>
    <div class="charts-row">
      <div class="chart-card">
        <h3>Trades by Company</h3>
        <div class="chart-wrap"><canvas id="chart-company"></canvas></div>
      </div>
      <div class="chart-card">
        <h3>CEO vs CFO: Avg Returns</h3>
        <div class="chart-wrap"><canvas id="chart-role"></canvas></div>
      </div>
    </div>
  </div>

  <!-- Trade Table -->
  <div id="trades">
    <div class="section-title">All Insider Trades</div>
    <div class="table-controls">
      <input class="search-box" id="search" type="text" placeholder="Search company, insider, ticker...">
      <select class="filter" id="f-type">
        <option value="">All Types</option>
        <option value="A">Buy (A)</option>
        <option value="D">Sell (D)</option>
      </select>
      <select class="filter" id="f-role">
        <option value="">All Roles</option>
        <option value="CEO">CEO</option>
        <option value="CFO">CFO</option>
      </select>
      <select class="filter" id="f-sector">
        <option value="">All Sectors</option>
      </select>
      <select class="filter" id="f-ticker">
        <option value="">All Companies</option>
      </select>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th onclick="sortBy('ticker')">Ticker <span id="sort-ticker"></span></th>
            <th onclick="sortBy('company')">Company <span id="sort-company"></span></th>
            <th onclick="sortBy('insider')">Insider <span id="sort-insider"></span></th>
            <th onclick="sortBy('role')">Role <span id="sort-role"></span></th>
            <th onclick="sortBy('date')">Date <span id="sort-date"></span></th>
            <th onclick="sortBy('type')">Type <span id="sort-type"></span></th>
            <th onclick="sortBy('shares')" style="text-align:right">Shares <span id="sort-shares"></span></th>
            <th onclick="sortBy('price')" style="text-align:right">Price <span id="sort-price"></span></th>
            <th onclick="sortBy('r30')" style="text-align:right">30d Ret <span id="sort-r30"></span></th>
            <th onclick="sortBy('r60')" style="text-align:right">60d Ret <span id="sort-r60"></span></th>
            <th onclick="sortBy('r90')" style="text-align:right">90d Ret <span id="sort-r90"></span></th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
      <div class="pagination">
        <div class="page-info" id="page-info"></div>
        <div class="page-btns">
          <button class="page-btn" id="btn-prev" onclick="changePage(-1)">Prev</button>
          <button class="page-btn" id="btn-next" onclick="changePage(1)">Next</button>
        </div>
      </div>
    </div>
  </div>

</div>

<footer>
  <p>Built by <strong>Akash Chaudhary</strong> &nbsp;|&nbsp; Data from <a href="https://www.sec.gov/cgi-bin/browse-edgar" target="_blank">SEC EDGAR</a> &nbsp;|&nbsp;
  <a href="https://github.com/Akash21ch" target="_blank">GitHub</a> &nbsp;|&nbsp;
  <a href="https://public.tableau.com/app/profile/akash.chaudhary4621" target="_blank">Tableau Public</a></p>
  <p style="margin-top:8px;font-size:12px;color:#334155">Data covers {year_start}&ndash;{year_end} &bull; {companies} S&amp;P 500 companies &bull; CEO &amp; CFO transactions only &bull; Returns calculated using Yahoo Finance price data</p>
</footer>

<script>
const TRADES = {data_json};

const sectors = [...new Set(TRADES.map(t => t.sector))].sort();
const tickers = [...new Set(TRADES.map(t => t.ticker))].sort();
const fSector = document.getElementById('f-sector');
const fTicker = document.getElementById('f-ticker');
sectors.forEach(s => {{ const o = document.createElement('option'); o.value = s; o.textContent = s; fSector.appendChild(o); }});
tickers.forEach(t => {{ const o = document.createElement('option'); o.value = t; o.textContent = t; fTicker.appendChild(o); }});

let filtered = [...TRADES];
let page = 1;
const PER_PAGE = 20;
let sortKey = 'date';
let sortDir = -1;

function fmt(n) {{ return n >= 0 ? `+${{n.toFixed(2)}}%` : `${{n.toFixed(2)}}%`; }}
function fmtN(n) {{ if (n >= 1e6) return (n/1e6).toFixed(1)+'M'; if (n >= 1e3) return (n/1e3).toFixed(1)+'K'; return n.toLocaleString(); }}
function cls(n) {{ return n > 0 ? 'pos' : n < 0 ? 'neg' : 'neu'; }}

function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase();
  const type = document.getElementById('f-type').value;
  const role = document.getElementById('f-role').value;
  const sector = document.getElementById('f-sector').value;
  const ticker = document.getElementById('f-ticker').value;
  filtered = TRADES.filter(t =>
    (!q || t.ticker.toLowerCase().includes(q) || t.company.toLowerCase().includes(q) || t.insider.toLowerCase().includes(q)) &&
    (!type || t.type === type) &&
    (!role || t.role === role) &&
    (!sector || t.sector === sector) &&
    (!ticker || t.ticker === ticker)
  );
  filtered.sort((a, b) => {{
    let av = a[sortKey], bv = b[sortKey];
    if (typeof av === 'string') return av.localeCompare(bv) * sortDir;
    return (av - bv) * sortDir;
  }});
  page = 1;
  renderTable();
}}

function sortBy(key) {{
  if (sortKey === key) sortDir *= -1; else {{ sortKey = key; sortDir = -1; }}
  document.querySelectorAll('th span').forEach(s => s.textContent = '');
  const el = document.getElementById('sort-'+key);
  if (el) el.textContent = sortDir === -1 ? ' \u25bc' : ' \u25b2';
  applyFilters();
}}

function renderTable() {{
  const start = (page - 1) * PER_PAGE;
  const rows = filtered.slice(start, start + PER_PAGE);
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = rows.map(t => `
    <tr>
      <td><strong>${{t.ticker}}</strong></td>
      <td>${{t.company}}</td>
      <td style="color:var(--muted)">${{t.insider}}</td>
      <td><span class="badge badge-${{t.role.toLowerCase()}}">${{t.role}}</span></td>
      <td style="color:var(--muted)">${{t.date}}</td>
      <td><span class="badge ${{t.type==='A'?'badge-buy':'badge-sell'}}">${{t.type==='A'?'BUY':'SELL'}}</span></td>
      <td style="text-align:right">${{fmtN(t.shares)}}</td>
      <td style="text-align:right">$${{t.price.toFixed(2)}}</td>
      <td style="text-align:right" class="${{cls(t.r30)}}">${{fmt(t.r30)}}</td>
      <td style="text-align:right" class="${{cls(t.r60)}}">${{fmt(t.r60)}}</td>
      <td style="text-align:right" class="${{cls(t.r90)}}">${{fmt(t.r90)}}</td>
    </tr>
  `).join('');
  const total = filtered.length;
  const totalPages = Math.ceil(total / PER_PAGE);
  document.getElementById('page-info').textContent = `Showing ${{start+1}}\u2013${{Math.min(start+PER_PAGE, total)}} of ${{total}} trades`;
  document.getElementById('btn-prev').disabled = page <= 1;
  document.getElementById('btn-next').disabled = page >= totalPages;
}}

function changePage(d) {{ page += d; renderTable(); }}

['search','f-type','f-role','f-sector','f-ticker'].forEach(id => {{
  document.getElementById(id).addEventListener('input', applyFilters);
}});

applyFilters();

// ── Charts ────────────────────────────────────────────────────────────────────
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = '#1f2d47';

const buys  = TRADES.filter(t => t.type === 'A');
const sells = TRADES.filter(t => t.type === 'D');
const avg   = (arr, k) => arr.length ? arr.reduce((s,t) => s + t[k], 0) / arr.length : 0;

new Chart(document.getElementById('chart-buysell'), {{
  type: 'bar',
  data: {{
    labels: ['30-Day Return', '60-Day Return', '90-Day Return'],
    datasets: [
      {{ label: 'Buys',  data: [avg(buys,'r30'), avg(buys,'r60'), avg(buys,'r90')].map(v => +v.toFixed(2)), backgroundColor: 'rgba(34,197,94,.7)',  borderRadius: 6 }},
      {{ label: 'Sells', data: [avg(sells,'r30'),avg(sells,'r60'),avg(sells,'r90')].map(v => +v.toFixed(2)), backgroundColor: 'rgba(239,68,68,.7)', borderRadius: 6 }}
    ]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ x: {{ grid: {{ color: '#1f2d47' }} }}, y: {{ grid: {{ color: '#1f2d47' }}, ticks: {{ callback: v => v+'%' }} }} }} }}
}});

const sectorMap = {{}};
TRADES.forEach(t => {{ if (!sectorMap[t.sector]) sectorMap[t.sector] = []; sectorMap[t.sector].push(t.r30); }});
const sectorAvgs = Object.entries(sectorMap).map(([k,v]) => [k, v.reduce((s,x)=>s+x,0)/v.length]).sort((a,b) => b[1]-a[1]);

new Chart(document.getElementById('chart-sector'), {{
  type: 'bar',
  data: {{
    labels: sectorAvgs.map(s => s[0]),
    datasets: [{{ label: 'Avg 30d Return %', data: sectorAvgs.map(s => +s[1].toFixed(2)), backgroundColor: sectorAvgs.map(s => s[1] >= 0 ? 'rgba(59,130,246,.7)' : 'rgba(239,68,68,.7)'), borderRadius: 4 }}]
  }},
  options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#1f2d47' }}, ticks: {{ callback: v => v+'%' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }} }} }}
}});

const companyCount = {{}};
TRADES.forEach(t => {{ companyCount[t.ticker] = (companyCount[t.ticker]||0)+1; }});
const compSorted = Object.entries(companyCount).sort((a,b)=>b[1]-a[1]);

new Chart(document.getElementById('chart-company'), {{
  type: 'bar',
  data: {{
    labels: compSorted.map(c=>c[0]),
    datasets: [{{ label: 'Trades', data: compSorted.map(c=>c[1]), backgroundColor: 'rgba(139,92,246,.7)', borderRadius: 4 }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ display: false }} }}, y: {{ grid: {{ color: '#1f2d47' }} }} }} }}
}});

const ceos = TRADES.filter(t => t.role === 'CEO');
const cfos = TRADES.filter(t => t.role === 'CFO');

new Chart(document.getElementById('chart-role'), {{
  type: 'bar',
  data: {{
    labels: ['30-Day Return', '60-Day Return', '90-Day Return'],
    datasets: [
      {{ label: 'CEO', data: [avg(ceos,'r30'), avg(ceos,'r60'), avg(ceos,'r90')].map(v=>+v.toFixed(2)), backgroundColor: 'rgba(139,92,246,.7)', borderRadius: 6 }},
      {{ label: 'CFO', data: [avg(cfos,'r30'), avg(cfos,'r60'), avg(cfos,'r90')].map(v=>+v.toFixed(2)), backgroundColor: 'rgba(59,130,246,.7)', borderRadius: 6 }}
    ]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ x: {{ grid: {{ color: '#1f2d47' }} }}, y: {{ grid: {{ color: '#1f2d47' }}, ticks: {{ callback: v => v+'%' }} }} }} }}
}});
</script>
</body>
</html>'''

# ── Write output ──────────────────────────────────────────────────────────────
with open(OUT_FILE, "w") as f:
    f.write(html)

print(f"Done — index.html updated ({total:,} trades, {companies} companies)")
