#!/usr/bin/env python3
"""
Flask Web Application for Car Arbitrage Scraper
Provides REST API and web interface for car deals
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import os
import json
from datetime import datetime
import threading
from pathlib import Path

from car_scraper import CarArbitrageFinder, create_sample_data, OUTPUT_DIR, TARGET_CARS

app = Flask(__name__)
CORS(app)


@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Global state
scraper_status = {
    'running': False,
    'last_run': None,
    'error': None,
    'progress': 0,
    'current_action': '',
    'action_log': []
}

latest_deals = []


def log_action(message):
    import re
    scraper_status['current_action'] = message
    scraper_status['action_log'].append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': message
    })
    progress_match = re.search(r'(\d+)%\s+complete', message)
    if progress_match:
        scraper_status['progress'] = int(progress_match.group(1))
    if len(scraper_status['action_log']) > 30:
        scraper_status['action_log'] = scraper_status['action_log'][-30:]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def deal_to_dict(d):
    return {
        'model_type': d.model_type,
        'title': d.title,
        'price': d.price,
        'avg_uk_price': d.avg_uk_price,
        'uk_saving': d.uk_saving,
        'expected_ni_price': d.expected_ni_price,
        'avg_ni_price': d.avg_ni_price,
        'net_profit': d.net_profit,
        'profit_margin': d.profit_margin,
        'location': d.location,
        'distance': round(d.distance, 1),
        'year': d.year,
        'mileage': d.mileage,
        'source': d.source,
        'url': d.url,
        'image': getattr(d, 'image', '')
    }


def run_scraper_background(use_demo=False):
    global scraper_status, latest_deals

    try:
        scraper_status['running'] = True
        scraper_status['error'] = None
        scraper_status['progress'] = 0
        scraper_status['current_action'] = 'Initializing...'
        scraper_status['action_log'] = []
        latest_deals = []

        log_action("Starting Car Arbitrage Scraper...")

        finder = CarArbitrageFinder(progress_callback=log_action)

        if use_demo:
            log_action("Running in DEMO mode with sample data")
            finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
            latest_deals = [deal_to_dict(d) for d in sorted(finder.profitable_deals, key=lambda x: x.net_profit, reverse=True)]
            scraper_status['progress'] = 100
            log_action("Demo complete - {} deals loaded".format(len(latest_deals)))
        else:
            def monitor():
                while scraper_status['running']:
                    if finder.profitable_deals:
                        try:
                            latest_deals[:] = [deal_to_dict(d) for d in sorted(finder.profitable_deals, key=lambda x: x.net_profit, reverse=True)]
                        except Exception:
                            pass
                    threading.Event().wait(2)

            t = threading.Thread(target=monitor, daemon=True)
            t.start()

            finder.search_all()

            latest_deals[:] = [deal_to_dict(d) for d in sorted(finder.profitable_deals, key=lambda x: x.net_profit, reverse=True)]
            scraper_status['progress'] = 100
            log_action("Scraping complete - {} deals found".format(len(latest_deals)))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if finder.profitable_deals:
            finder.export_csv(f"{OUTPUT_DIR}/deals_{timestamp}.csv")
            finder.export_html(f"{OUTPUT_DIR}/deals_{timestamp}.html")

        scraper_status['last_run'] = datetime.now().isoformat()

    except Exception as e:
        scraper_status['error'] = str(e)
        log_action("ERROR: " + str(e))
        print(f"Scraper error: {e}")
    finally:
        scraper_status['running'] = False


@app.route('/')
def index():
    return DASHBOARD_HTML


@app.route('/api/deals')
def get_deals():
    return jsonify(latest_deals)


@app.route('/api/status')
def get_status():
    return jsonify(scraper_status)


@app.route('/api/scrape', methods=['POST'])
def run_scrape():
    if scraper_status['running']:
        return jsonify({'status': 'already_running'}), 409

    use_demo = request.args.get('demo', 'false').lower() == 'true'

    thread = threading.Thread(target=run_scraper_background, args=(use_demo,))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'demo': use_demo})


@app.route('/api/models')
def get_models():
    return jsonify({
        model: {
            'search_terms': config['search_terms'],
            'max_price': config['max_price'],
            'ni_markup': config['ni_markup'],
            'min_profit': config['min_profit']
        }
        for model, config in TARGET_CARS.items()
    })


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/image-proxy')
def image_proxy():
    """Proxy external images to bypass referrer/hotlink restrictions"""
    import requests as req
    url = request.args.get('url', '')
    if not url or not url.startswith('http'):
        return '', 404

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': url.split('/')[0] + '//' + url.split('/')[2] + '/',
        }
        resp = req.get(url, headers=headers, timeout=10, stream=True)
        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            response = make_response(resp.content)
            response.headers['Content-Type'] = content_type
            response.headers['Cache-Control'] = 'public, max-age=86400'
            return response
    except Exception:
        pass

    return '', 404


@app.route('/api/version')
def version():
    return jsonify({'version': 'v3-2026-02-15', 'started': app.config.get('START_TIME', 'unknown')})


@app.route('/search-links')
def search_links():
    from urllib.parse import urlencode

    car_models = []
    for model_key, config in TARGET_CARS.items():
        search_term = config['search_terms'][0]
        max_price = config['max_price']

        autotrader_url = "https://www.autotrader.co.uk/car-search?" + urlencode({
            'postcode': 'L1', 'radius': '200',
            'price-to': str(max_price), 'sort': 'price-asc'
        }) + "&search=" + search_term.replace(' ', '+')

        gumtree_url = "https://www.gumtree.com/search?" + urlencode({
            'search_category': 'cars', 'q': search_term,
            'search_location': 'Liverpool', 'distance': '200',
            'max_price': str(max_price), 'sort': 'price_asc'
        })

        pistonheads_url = "https://www.pistonheads.com/classifieds/used-cars?" + urlencode({
            'keywords': search_term, 'price_to': str(max_price)
        })

        car_models.append({
            'name': model_key.replace('_', ' ').title(),
            'search_term': search_term,
            'max_price': max_price,
            'autotrader': autotrader_url,
            'gumtree': gumtree_url,
            'pistonheads': pistonheads_url
        })

    sections = ''
    for car in car_models:
        sections += '''
        <div class="car-section">
            <div class="car-header">
                <div class="car-name">{name}</div>
                <div class="car-info">Search: "{search}" | Max: &pound;{price:,}</div>
            </div>
            <div class="links-grid">
                <a href="{at}" target="_blank" class="site-link">
                    <div class="site-name">AutoTrader UK</div>
                    <span class="open-btn">Open Search</span>
                </a>
                <a href="{gt}" target="_blank" class="site-link">
                    <div class="site-name">Gumtree</div>
                    <span class="open-btn">Open Search</span>
                </a>
                <a href="{ph}" target="_blank" class="site-link">
                    <div class="site-name">PistonHeads</div>
                    <span class="open-btn">Open Search</span>
                </a>
            </div>
        </div>
        '''.format(
            name=car['name'], search=car['search_term'],
            price=car['max_price'], at=car['autotrader'],
            gt=car['gumtree'], ph=car['pistonheads']
        )

    return SEARCH_LINKS_HTML.replace('{{CAR_SECTIONS}}', sections)


# ============================================================
# HTML Templates (separated from Python logic for clarity)
# ============================================================

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>No-Mo Cars | UK to NI Deals</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg-primary:#0c0f1a;--bg-secondary:#141829;--bg-card:#1a1f35;--bg-card-hover:#222842;--accent:#22c55e;--accent-glow:rgba(34,197,94,.15);--accent-dim:#16a34a;--blue:#3b82f6;--blue-dim:#2563eb;--amber:#f59e0b;--red:#ef4444;--text-primary:#f1f5f9;--text-secondary:#94a3b8;--text-muted:#64748b;--border:rgba(148,163,184,.08);--border-accent:rgba(34,197,94,.2);--radius:12px;--radius-lg:16px;--shadow:0 4px 6px -1px rgba(0,0,0,.3),0 2px 4px -2px rgba(0,0,0,.2);--shadow-lg:0 10px 25px -5px rgba(0,0,0,.4)}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg-primary);color:var(--text-primary);min-height:100vh}
.container{max-width:1500px;margin:0 auto;padding:20px}

/* Top nav bar */
.navbar{display:flex;align-items:center;justify-content:space-between;padding:16px 28px;background:var(--bg-secondary);border-bottom:1px solid var(--border);margin-bottom:28px;border-radius:var(--radius-lg)}
.brand{display:flex;align-items:center;gap:12px}
.brand-icon{width:42px;height:42px;background:linear-gradient(135deg,var(--accent),#10b981);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:#fff;font-family:'Space Grotesk',sans-serif;letter-spacing:-1px}
.brand-text{font-family:'Space Grotesk',sans-serif;font-size:1.6em;font-weight:700;color:var(--text-primary);letter-spacing:-.5px}
.brand-text span{color:var(--accent)}
.brand-tag{font-size:.7em;color:var(--text-muted);font-weight:400;letter-spacing:1px;text-transform:uppercase;margin-left:2px}
.nav-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.btn{border:none;padding:10px 20px;border-radius:8px;font-size:.85em;font-weight:600;cursor:pointer;transition:all .2s;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-family:'Inter',sans-serif}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:var(--accent-dim);box-shadow:0 0 20px var(--accent-glow)}
.btn-outline{background:transparent;color:var(--text-secondary);border:1px solid var(--border)}
.btn-outline:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-glow)}
.btn-amber{background:var(--amber);color:#fff}
.btn-amber:hover{background:#d97706}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none!important}

/* Toast / message */
#msg{display:none;text-align:center;padding:12px 16px;margin:0 0 20px 0;border-radius:var(--radius);font-size:.9em;font-weight:500}

/* Progress panel */
.progress-box{background:var(--bg-card);border-radius:var(--radius-lg);padding:24px;margin:0 0 24px 0;border:1px solid rgba(59,130,246,.15);display:none}
.progress-header{display:flex;align-items:center;gap:8px;margin-bottom:14px;font-weight:600;color:var(--blue)}
.progress-bar{background:var(--bg-primary);height:24px;border-radius:12px;overflow:hidden}
.progress-fill{background:linear-gradient(90deg,var(--accent),#10b981);height:100%;width:0%;transition:width .4s;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:.75em;min-width:36px;border-radius:12px}
.progress-fill.error{background:linear-gradient(90deg,var(--red),#dc2626)}
.action-text{color:var(--accent);font-size:.9em;padding:10px 12px;background:var(--bg-primary);border-radius:8px;border-left:3px solid var(--accent);margin:14px 0 0 0;font-family:'Space Grotesk',monospace;font-weight:500}
.action-text.error{color:var(--red);border-left-color:var(--red)}
.log-box{max-height:160px;overflow-y:auto;background:var(--bg-primary);border-radius:8px;padding:10px;margin-top:12px}
.log-item{padding:4px 8px;font-size:.8em;color:var(--text-muted);border-left:2px solid var(--border);margin:3px 0;font-family:'Space Grotesk',monospace}
.log-item .t{color:var(--blue);margin-right:8px}

/* Stat cards */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:0 0 24px 0;display:none}
@media(max-width:900px){.stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:500px){.stats{grid-template-columns:1fr}}
.stat-card{background:var(--bg-card);padding:22px;border-radius:var(--radius);border:1px solid var(--border);position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent);opacity:.6}
.stat-card:nth-child(2)::before{background:var(--blue)}
.stat-card:nth-child(3)::before{background:var(--amber)}
.stat-card:nth-child(4)::before{background:#a855f7}
.stat-val{font-family:'Space Grotesk',sans-serif;font-size:2em;font-weight:700;color:var(--text-primary);line-height:1.1}
.stat-lbl{color:var(--text-muted);text-transform:uppercase;font-size:.7em;letter-spacing:1.5px;margin-top:6px;font-weight:600}

/* Deals section */
.section-panel{background:var(--bg-secondary);border-radius:var(--radius-lg);padding:28px;margin:0 0 24px 0;border:1px solid var(--border)}
.section-title{font-family:'Space Grotesk',sans-serif;font-size:1.3em;font-weight:700;color:var(--text-primary);margin-bottom:20px;display:flex;align-items:center;gap:10px}
.section-title .icon{width:32px;height:32px;background:var(--accent-glow);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px}

/* Filters */
.filters{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px}
.filter-group{flex:1;min-width:200px}
.filter-label{color:var(--text-muted);font-size:.7em;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;font-weight:600}
.filters select{width:100%;background:var(--bg-primary);color:var(--text-primary);border:1px solid var(--border);padding:10px 14px;border-radius:8px;font-size:.9em;cursor:pointer;font-family:'Inter',sans-serif;appearance:auto;transition:border-color .2s}
.filters select:hover,.filters select:focus{border-color:var(--accent);outline:none}
.filter-count{color:var(--text-muted);font-size:.85em;margin-bottom:16px}
.filter-count span{color:var(--accent);font-weight:600}

/* Deal cards */
.deal-card{background:var(--bg-card);margin:0 0 12px 0;border-radius:var(--radius);border:1px solid var(--border);transition:all .2s;overflow:hidden;display:flex}
.deal-card:hover{border-color:var(--border-accent);background:var(--bg-card-hover);box-shadow:var(--shadow)}
.deal-img{width:200px;min-height:140px;flex-shrink:0;background-color:var(--bg-primary);position:relative;overflow:hidden}
.deal-img .no-img{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:.75em;text-transform:uppercase;letter-spacing:1px}
.deal-body{flex:1;padding:20px;min-width:0}
@media(max-width:700px){.deal-card{flex-direction:column}.deal-img{width:100%;height:180px}}
.deal-header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:14px}
.deal-title{font-size:1.05em;color:var(--text-primary);font-weight:600;line-height:1.3}
.deal-profit-badge{background:var(--accent-glow);color:var(--accent);font-weight:700;padding:6px 14px;border-radius:20px;font-size:.95em;white-space:nowrap;font-family:'Space Grotesk',sans-serif}
.deal-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px}
.deal-lbl{color:var(--text-muted);font-size:.7em;text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:2px}
.deal-val{color:var(--text-primary);font-size:.95em;font-weight:600}
.deal-val.profit{color:var(--accent)}
.deal-footer{display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}
.deal-meta{display:flex;gap:16px;font-size:.8em;color:var(--text-muted)}
.deal-link{padding:8px 18px;background:var(--blue);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:.85em;transition:all .2s}
.deal-link:hover{background:var(--blue-dim);box-shadow:0 4px 12px rgba(59,130,246,.3)}

.loading{text-align:center;padding:40px;color:var(--text-muted);font-size:1em}
.spinner{border:3px solid var(--bg-card);border-top:3px solid var(--accent);border-radius:50%;width:32px;height:32px;animation:spin .8s linear infinite;margin:12px auto}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
    <nav class="navbar">
        <div class="brand">
            <div class="brand-icon">NM</div>
            <div>
                <div class="brand-text">No-Mo <span>Cars</span></div>
                <div class="brand-tag">UK &rarr; Northern Ireland</div>
            </div>
        </div>
        <div class="nav-actions">
            <a href="/search-links" class="btn btn-outline">Manual Search</a>
            <button onclick="loadDeals()" class="btn btn-outline">Refresh</button>
            <button onclick="doScrape(false)" id="scrape-btn" class="btn btn-primary">Scrape Live Data</button>
        </div>
    </nav>

    <div id="msg"></div>

    <div id="progress-box" class="progress-box">
        <div class="progress-header">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/></svg>
            Scraping in Progress
        </div>
        <div class="progress-bar"><div id="pbar" class="progress-fill">0%</div></div>
        <div id="action-text" class="action-text">Waiting...</div>
        <details>
            <summary style="color:var(--text-muted);cursor:pointer;margin-top:12px;font-size:.85em;font-weight:500">Activity Log</summary>
            <div id="log-box" class="log-box"></div>
        </details>
    </div>

    <div class="stats" id="stats">
        <div class="stat-card"><div class="stat-val" id="s-deals">0</div><div class="stat-lbl">Deals Found</div></div>
        <div class="stat-card"><div class="stat-val" id="s-profit">&pound;0</div><div class="stat-lbl">Total Profit</div></div>
        <div class="stat-card"><div class="stat-val" id="s-avg">&pound;0</div><div class="stat-lbl">Avg Profit</div></div>
        <div class="stat-card"><div class="stat-val" id="s-margin">0%</div><div class="stat-lbl">Best Margin</div></div>
    </div>

    <div class="section-panel">
        <div class="section-title"><div class="icon">&#9733;</div> Profitable Deals</div>
        <div class="filters">
            <div class="filter-group">
                <div class="filter-label">Model</div>
                <select id="modelFilter" onchange="filterDeals()"><option value="all">All Models</option></select>
            </div>
            <div class="filter-group">
                <div class="filter-label">Source</div>
                <select id="sourceFilter" onchange="filterDeals()"><option value="all">All Sources</option></select>
            </div>
        </div>
        <div class="filter-count" id="filterCount"></div>
        <div id="deals"></div>
    </div>
</div>

<script>
var polling = null;
var statusPoll = null;
var allDeals = [];

var modelLabels = {
    'peugeot_306_dturbo': 'Peugeot 306 D-Turbo',
    'lexus_is200_sport': 'Lexus IS200 Sport',
    'lexus_is250_sport': 'Lexus IS250 Sport',
    'bmw_e46_330ci': 'BMW E46 330ci',
    'bmw_e46_m3': 'BMW E46 M3',
    'honda_civic_ep3_type_r': 'Honda Civic EP3 Type R',
    'bmw_e60_530d': 'BMW E60 530d',
    'bmw_e60_535d': 'BMW E60 535d',
    'bmw_f30_330d': 'BMW F30 330d',
    'bmw_f30_335d': 'BMW F30 335d'
};

var fallbackImages = {
    'peugeot_306_dturbo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Peugeot_306_front_20080822.jpg/640px-Peugeot_306_front_20080822.jpg',
    'lexus_is200_sport': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/1999-2005_Lexus_IS_200_%28GXE10R%29_sedan_01.jpg/640px-1999-2005_Lexus_IS_200_%28GXE10R%29_sedan_01.jpg',
    'lexus_is250_sport': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/1999-2005_Lexus_IS_200_%28GXE10R%29_sedan_01.jpg/640px-1999-2005_Lexus_IS_200_%28GXE10R%29_sedan_01.jpg',
    'bmw_e46_330ci': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/BMW_E46_Coup%C3%A9_front_20080111.jpg/640px-BMW_E46_Coup%C3%A9_front_20080111.jpg',
    'bmw_e46_m3': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/BMW_M3_E46_%282%29.jpg/640px-BMW_M3_E46_%282%29.jpg',
    'honda_civic_ep3_type_r': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Honda_Civic_Type_R_%28EP3%29.jpg/640px-Honda_Civic_Type_R_%28EP3%29.jpg',
    'bmw_e60_530d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/BMW_E60_front_20080417.jpg/640px-BMW_E60_front_20080417.jpg',
    'bmw_e60_535d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/BMW_E60_front_20080417.jpg/640px-BMW_E60_front_20080417.jpg',
    'bmw_f30_330d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/BMW_F30_320d_Sportline_Mineralgrau.jpg/640px-BMW_F30_320d_Sportline_Mineralgrau.jpg',
    'bmw_f30_335d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/BMW_F30_320d_Sportline_Mineralgrau.jpg/640px-BMW_F30_320d_Sportline_Mineralgrau.jpg'
};

function doScrape(demo) {
    try {
        console.log('doScrape called, demo=' + demo);

        var btn = document.getElementById('scrape-btn');
        if (!btn) { alert('ERROR: scrape-btn not found'); return; }
        btn.disabled = true;

        // Show progress box
        var pb = document.getElementById('progress-box');
        if (!pb) { alert('ERROR: progress-box not found'); return; }
        pb.style.display = 'block';
        pb.style.visibility = 'visible';

        var pbar = document.getElementById('pbar');
        pbar.style.width = '0%';
        pbar.textContent = '0%';
        pbar.className = 'progress-fill';

        document.getElementById('action-text').textContent = 'Starting scraper...';
        document.getElementById('action-text').className = 'action-text';
        document.getElementById('log-box').innerHTML = '';

        // Clear deals
        document.getElementById('deals').innerHTML = '<div class="loading"><div class="spinner"></div>Starting scraper...</div>';
        document.getElementById('stats').style.display = 'none';

        showMsg('Scraper starting...', '#ffaa00');

        var url = demo ? '/api/scrape?demo=true' : '/api/scrape';
        console.log('Posting to: ' + url);

        var xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.onload = function() {
            console.log('Response: ' + xhr.status + ' ' + xhr.responseText);
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                if (data.status === 'started') {
                    showMsg('Scraper running...', '#ffaa00');
                    statusPoll = setInterval(pollStatus, 1000);
                    polling = setInterval(loadDeals, 3000);
                }
            } else if (xhr.status === 409) {
                showMsg('Scraper already running...', '#ffaa00');
                btn.disabled = false;
            } else {
                showMsg('Error: ' + xhr.status + ' ' + xhr.statusText, '#ff4444');
                btn.disabled = false;
                showProgressError('Failed to start scraper: HTTP ' + xhr.status);
            }
        };
        xhr.onerror = function() {
            console.log('XHR error');
            showMsg('Network error - is the server running?', '#ff4444');
            btn.disabled = false;
            showProgressError('Network error - cannot reach server');
        };
        xhr.send();

    } catch(e) {
        alert('doScrape error: ' + e.message);
        console.error('doScrape error:', e);
    }
}

function pollStatus() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/status');
    xhr.onload = function() {
        if (xhr.status !== 200) return;
        var data = JSON.parse(xhr.responseText);

        // Update progress bar
        var pbar = document.getElementById('pbar');
        if (data.progress !== undefined) {
            pbar.style.width = data.progress + '%';
            pbar.textContent = data.progress + '%';
        }

        // Update current action
        if (data.current_action) {
            var at = document.getElementById('action-text');
            at.textContent = data.current_action;
            at.className = 'action-text';
        }

        // Update action log
        if (data.action_log && data.action_log.length > 0) {
            var logHtml = '';
            for (var i = data.action_log.length - 1; i >= 0; i--) {
                var log = data.action_log[i];
                logHtml += '<div class="log-item"><span class="t">' + log.time + '</span>' + escHtml(log.message) + '</div>';
            }
            document.getElementById('log-box').innerHTML = logHtml;
        }

        // Check if done
        if (!data.running && data.last_run) {
            clearInterval(statusPoll);
            clearInterval(polling);
            document.getElementById('scrape-btn').disabled = false;

            if (data.error) {
                showMsg('Scraper error: ' + data.error, '#ff4444');
                showProgressError(data.error);
            } else {
                showMsg('Scraper completed!', '#00ff88');
                loadDeals();
                // Hide progress after delay
                setTimeout(function() {
                    document.getElementById('progress-box').style.display = 'none';
                }, 8000);
            }
        }
    };
    xhr.onerror = function() {};
    xhr.send();
}

function showProgressError(msg) {
    var pbar = document.getElementById('pbar');
    pbar.className = 'progress-fill error';
    pbar.style.width = '100%';
    pbar.textContent = 'ERROR';

    var at = document.getElementById('action-text');
    at.textContent = 'Error: ' + msg;
    at.className = 'action-text error';
}

function loadDeals() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/deals');
    xhr.onload = function() {
        if (xhr.status !== 200) return;
        allDeals = JSON.parse(xhr.responseText);

        if (allDeals.length === 0) {
            document.getElementById('deals').innerHTML = '<div class="loading">No deals found yet. Click "Scrape Live Data" to find deals.</div>';
            document.getElementById('stats').style.display = 'none';
            document.getElementById('filterCount').textContent = '';
            return;
        }

        // Populate filter dropdowns
        var models = {};
        var sources = {};
        for (var i = 0; i < allDeals.length; i++) {
            models[allDeals[i].model_type] = true;
            sources[allDeals[i].source] = true;
        }

        var modelSel = document.getElementById('modelFilter');
        var curModel = modelSel.value;
        modelSel.innerHTML = '<option value="all">All Models</option>';
        Object.keys(models).sort().forEach(function(m) {
            var opt = document.createElement('option');
            opt.value = m;
            opt.textContent = modelLabels[m] || m;
            modelSel.appendChild(opt);
        });
        modelSel.value = curModel;

        var sourceSel = document.getElementById('sourceFilter');
        var curSource = sourceSel.value;
        sourceSel.innerHTML = '<option value="all">All Sources</option>';
        Object.keys(sources).sort().forEach(function(s) {
            var opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            sourceSel.appendChild(opt);
        });
        sourceSel.value = curSource;

        filterDeals();
    };
    xhr.onerror = function() {};
    xhr.send();
}

function filterDeals() {
    var modelVal = document.getElementById('modelFilter').value;
    var sourceVal = document.getElementById('sourceFilter').value;

    var filtered = allDeals.filter(function(d) {
        var matchModel = (modelVal === 'all' || d.model_type === modelVal);
        var matchSource = (sourceVal === 'all' || d.source === sourceVal);
        return matchModel && matchSource;
    });

    // Update stats with filtered data
    var totalProfit = 0;
    var bestMargin = 0;
    for (var i = 0; i < filtered.length; i++) {
        totalProfit += filtered[i].net_profit;
        if (filtered[i].profit_margin > bestMargin) bestMargin = filtered[i].profit_margin;
    }
    var avgProfit = filtered.length > 0 ? Math.round(totalProfit / filtered.length) : 0;

    document.getElementById('s-deals').textContent = filtered.length;
    document.getElementById('s-profit').innerHTML = '&pound;' + totalProfit.toLocaleString();
    document.getElementById('s-avg').innerHTML = '&pound;' + avgProfit.toLocaleString();
    document.getElementById('s-margin').textContent = bestMargin.toFixed(1) + '%';
    document.getElementById('stats').style.display = 'grid';

    // Show filter count
    document.getElementById('filterCount').innerHTML = 'Showing <span>' + filtered.length + '</span> of <span>' + allDeals.length + '</span> deals';

    // Render deal cards
    var container = document.getElementById('deals');
    if (filtered.length === 0) {
        container.innerHTML = '<div class="loading">No deals match the selected filters.</div>';
        return;
    }

    var html = '';
    for (var i = 0; i < filtered.length; i++) {
        var d = filtered[i];
        var rawImgUrl = d.image || '';
        var fallbackUrl = fallbackImages[d.model_type] || '';
        // Use image proxy for external images (bypasses hotlink/referrer blocks)
        var imgUrl = rawImgUrl ? '/api/image-proxy?url=' + encodeURIComponent(rawImgUrl) : fallbackUrl;
        var fallbackSrc = fallbackUrl ? fallbackUrl : '';
        html += '<div class="deal-card">';
        html += '<div class="deal-img">';
        if (imgUrl) {
            html += '<img src="' + escAttr(imgUrl) + '" alt="' + escAttr(d.title) + '" data-fallback="' + escAttr(fallbackSrc) + '" loading="lazy" style="width:100%;height:100%;object-fit:cover;" onerror="imgError(this)">';
        } else {
            html += '<div class="no-img">No Image</div>';
        }
        html += '</div>';
        html += '<div class="deal-body">';
        html += '<div class="deal-header"><div class="deal-title">' + escHtml(d.title) + '</div>';
        html += '<div class="deal-profit-badge">&pound;' + d.net_profit.toLocaleString() + '</div></div>';
        html += '<div class="deal-grid">';
        html += '<div><div class="deal-lbl">Buy Price</div><div class="deal-val">&pound;' + d.price.toLocaleString() + '</div></div>';
        html += '<div><div class="deal-lbl">Sell Price (NI)</div><div class="deal-val">&pound;' + d.expected_ni_price.toLocaleString() + '</div></div>';
        html += '<div><div class="deal-lbl">Net Profit</div><div class="deal-val profit">&pound;' + d.net_profit.toLocaleString() + '</div></div>';
        html += '<div><div class="deal-lbl">Margin</div><div class="deal-val">' + d.profit_margin.toFixed(1) + '%</div></div>';
        html += '</div>';
        html += '<div class="deal-footer">';
        html += '<div class="deal-meta"><span>' + escHtml(d.source) + '</span><span>' + escHtml(d.location) + ' (' + d.distance + ' mi)</span></div>';
        if (d.url) {
            html += '<a href="' + escAttr(d.url) + '" target="_blank" class="deal-link">View Listing &rarr;</a>';
        }
        html += '</div></div></div>';
    }
    container.innerHTML = html;
}

function showMsg(text, color) {
    var el = document.getElementById('msg');
    el.textContent = text;
    el.style.display = 'block';
    el.style.textAlign = 'center';
    el.style.padding = '12px 16px';
    el.style.margin = '0 0 20px 0';
    el.style.borderRadius = '12px';
    el.style.fontSize = '.9em';
    el.style.fontWeight = '500';
    el.style.color = color;
    var bgMap = {'#ff4444':'rgba(239,68,68,.1)','#ef4444':'rgba(239,68,68,.1)','#00ff88':'rgba(34,197,94,.1)','#22c55e':'rgba(34,197,94,.1)','#ffaa00':'rgba(245,158,11,.1)','#f59e0b':'rgba(245,158,11,.1)'};
    el.style.background = bgMap[color] || 'rgba(148,163,184,.1)';
    el.style.border = '1px solid ' + color;

    if (color === '#00ff88' || color === '#22c55e') {
        setTimeout(function() { el.style.display = 'none'; }, 5000);
    }
}

function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}

function imgError(el) {
    el.onerror = null;
    if (el.src.indexOf('image-proxy') > -1) {
        var fb = el.getAttribute('data-fallback');
        if (fb) { el.src = fb; return; }
    }
    el.parentElement.innerHTML = '<div class="no-img">No Image</div>';
}

// Load deals on page load
loadDeals();

// Version check - proves new code is running
(function() {
    var vx = new XMLHttpRequest();
    vx.open('GET', '/api/version');
    vx.onload = function() {
        if (vx.status === 200) {
            var v = JSON.parse(vx.responseText);
            console.log('Server version: ' + v.version);
            var tag = document.createElement('div');
            tag.style.cssText = 'position:fixed;bottom:8px;right:8px;background:var(--bg-card,#1a1f35);color:var(--text-muted,#64748b);padding:4px 10px;border-radius:6px;font-size:11px;border:1px solid rgba(148,163,184,.08);z-index:9999;font-family:Inter,sans-serif';
            tag.textContent = v.version;
            document.body.appendChild(tag);
        } else {
            console.log('Version check failed - OLD CODE may be running');
            var tag = document.createElement('div');
            tag.style.cssText = 'position:fixed;bottom:8px;right:8px;background:var(--red,#ef4444);color:#fff;padding:4px 10px;border-radius:6px;font-size:11px;z-index:9999;font-family:Inter,sans-serif';
            tag.textContent = 'OLD CODE - restart server';
            document.body.appendChild(tag);
        }
    };
    vx.onerror = function() {
        console.log('Version check error');
    };
    vx.send();
})();
</script>
</body>
</html>'''

SEARCH_LINKS_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>No-Mo Cars | Search Links</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg-primary:#0c0f1a;--bg-secondary:#141829;--bg-card:#1a1f35;--bg-card-hover:#222842;--accent:#22c55e;--accent-glow:rgba(34,197,94,.15);--blue:#3b82f6;--blue-dim:#2563eb;--text-primary:#f1f5f9;--text-secondary:#94a3b8;--text-muted:#64748b;--border:rgba(148,163,184,.08);--border-accent:rgba(34,197,94,.2);--radius:12px;--radius-lg:16px}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg-primary);color:var(--text-primary);padding:20px;min-height:100vh}
.container{max-width:1400px;margin:0 auto}
.navbar{display:flex;align-items:center;justify-content:space-between;padding:16px 28px;background:var(--bg-secondary);border-bottom:1px solid var(--border);margin-bottom:28px;border-radius:var(--radius-lg)}
.brand{display:flex;align-items:center;gap:12px}
.brand-icon{width:42px;height:42px;background:linear-gradient(135deg,var(--accent),#10b981);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;color:#fff;font-family:'Space Grotesk',sans-serif;letter-spacing:-1px}
.brand-text{font-family:'Space Grotesk',sans-serif;font-size:1.6em;font-weight:700;letter-spacing:-.5px}
.brand-text span{color:var(--accent)}
.brand-tag{font-size:.7em;color:var(--text-muted);font-weight:400;letter-spacing:1px;text-transform:uppercase}
.back{padding:10px 20px;background:transparent;color:var(--text-secondary);border:1px solid var(--border);text-decoration:none;border-radius:8px;font-weight:600;font-size:.85em;transition:all .2s}
.back:hover{border-color:var(--accent);color:var(--accent)}
.section-title{font-family:'Space Grotesk',sans-serif;font-size:1.2em;font-weight:600;color:var(--text-primary);text-align:center;margin-bottom:24px;color:var(--text-muted)}
.car-section{background:var(--bg-secondary);border-radius:var(--radius-lg);padding:24px;margin-bottom:16px;border:1px solid var(--border);transition:border-color .2s}
.car-section:hover{border-color:var(--border-accent)}
.car-header{margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid var(--border)}
.car-name{font-family:'Space Grotesk',sans-serif;font-size:1.3em;color:var(--text-primary);font-weight:700}
.car-info{color:var(--text-muted);font-size:.8em;margin-top:4px}
.links-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.site-link{background:var(--bg-card);padding:18px;border-radius:var(--radius);border:1px solid var(--border);text-decoration:none;display:block;transition:all .2s}
.site-link:hover{border-color:var(--border-accent);background:var(--bg-card-hover)}
.site-name{font-size:1em;color:var(--blue);font-weight:700;margin-bottom:8px}
.open-btn{display:inline-block;padding:6px 14px;background:var(--blue);color:#fff;border-radius:6px;font-size:.8em;font-weight:600}
</style>
</head>
<body>
<div class="container">
    <nav class="navbar">
        <div class="brand">
            <div class="brand-icon">NM</div>
            <div>
                <div class="brand-text">No-Mo <span>Cars</span></div>
                <div class="brand-tag">Search Links</div>
            </div>
        </div>
        <a href="/" class="back">&larr; Back to Dashboard</a>
    </nav>
    <p class="section-title">Direct links to car listings with pre-filled search criteria</p>
    {{CAR_SECTIONS}}
</div>
</body>
</html>'''


if __name__ == '__main__':
    app.config['START_TIME'] = datetime.now().isoformat()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Start with empty deals - user clicks Scrape to begin
    latest_deals = []

    print("\n" + "="*60)
    print("  NO-MO CARS WEB APP STARTING")
    print("="*60)
    print("\nDashboard: http://localhost:5000")
    print("API:       http://localhost:5000/api/deals")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
