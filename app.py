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
        'url': d.url
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
<title>Car Arbitrage - Liverpool to NI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#0a0e27,#1a1f3a);color:#e0e0e0;padding:20px;min-height:100vh}
.container{max-width:1600px;margin:0 auto}
header{text-align:center;margin-bottom:30px;padding:30px 20px;background:rgba(26,31,58,.6);border-radius:16px;border:1px solid #00ff8833}
h1{color:#00ff88;font-size:2.5em;margin-bottom:10px;text-shadow:0 0 30px rgba(0,255,136,.6)}
.subtitle{color:#888;font-size:1.1em;margin-bottom:20px}
.controls{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-top:20px}
.btn{border:none;padding:12px 24px;border-radius:8px;font-size:.95em;font-weight:700;cursor:pointer;transition:all .3s;text-transform:uppercase;letter-spacing:1px;text-decoration:none;display:inline-block;color:#0a0e27}
.btn-primary{background:linear-gradient(135deg,#00ff88,#00cc6a)}
.btn-secondary{background:linear-gradient(135deg,#6666ff,#4444dd);color:#fff}
.btn-search{background:linear-gradient(135deg,#ffaa00,#ff8800);color:#fff}
.btn:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,255,136,.3)}
.btn:disabled{background:#555;color:#888;cursor:not-allowed;transform:none;box-shadow:none}

.progress-box{background:#1a1f3a;border-radius:12px;padding:20px;margin:20px 0;border:1px solid #6666ff44;display:none}
.progress-bar{background:#2a2f4a;height:28px;border-radius:14px;overflow:hidden;margin:12px 0}
.progress-fill{background:linear-gradient(90deg,#00ff88,#00cc6a);height:100%;width:0%;transition:width .4s;display:flex;align-items:center;justify-content:center;color:#0a0e27;font-weight:bold;font-size:.85em;min-width:40px}
.progress-fill.error{background:linear-gradient(90deg,#ff4444,#cc0000)}
.action-text{color:#00ff88;font-size:1em;padding:8px 10px;background:#2a2f4a;border-radius:6px;border-left:3px solid #00ff88;margin:8px 0}
.action-text.error{color:#ff4444;border-left-color:#ff4444}
.log-box{max-height:180px;overflow-y:auto;background:#0f1329;border-radius:6px;padding:8px;margin-top:10px}
.log-item{padding:4px 8px;font-size:.85em;color:#999;border-left:2px solid #333;margin:2px 0}
.log-item .t{color:#6666ff;margin-right:6px;font-family:monospace}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin:20px 0;display:none}
.stat-card{background:linear-gradient(135deg,#1a1f3a,#2a2f4a);padding:20px;border-radius:12px;border:1px solid #00ff8833;text-align:center}
.stat-val{font-size:2.2em;color:#00ff88;font-weight:bold}
.stat-lbl{color:#888;text-transform:uppercase;font-size:.8em;letter-spacing:1px;margin-top:4px}

.deals-box{background:#1a1f3a;border-radius:16px;padding:25px;margin:25px 0;border:1px solid #00ff8833}
.deal-card{background:#2a2f4a;padding:18px;margin:12px 0;border-radius:10px;border-left:4px solid #00ff88;transition:transform .2s}
.deal-card:hover{transform:translateX(4px);box-shadow:0 4px 15px rgba(0,255,136,.2)}
.deal-title{font-size:1.2em;color:#fff;font-weight:600;margin-bottom:10px}
.deal-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:10px 0}
.deal-lbl{color:#888;font-size:.75em;text-transform:uppercase}
.deal-val{color:#fff;font-size:1em;font-weight:600}
.deal-profit{color:#00ff88;font-size:1.3em}
.deal-link{display:inline-block;margin-top:10px;padding:8px 16px;background:linear-gradient(135deg,#6666ff,#4444dd);color:#fff;text-decoration:none;border-radius:6px;font-weight:600;font-size:.9em}
.deal-link:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(102,102,255,.4)}

.loading{text-align:center;padding:30px;color:#888;font-size:1.1em}
.spinner{border:3px solid #2a2f4a;border-top:3px solid #00ff88;border-radius:50%;width:36px;height:36px;animation:spin 1s linear infinite;margin:15px auto}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Car Arbitrage Dashboard</h1>
        <p class="subtitle">Liverpool &rarr; Northern Ireland | Live Car Deals</p>
        <div class="controls">
            <a href="/search-links" class="btn btn-search">Manual Search Links</a>
            <button onclick="doScrape(false)" id="scrape-btn" class="btn btn-primary">Scrape Live Data</button>
            <button onclick="doScrape(true)" class="btn btn-secondary">Demo Mode</button>
            <button onclick="loadDeals()" class="btn btn-secondary">Refresh</button>
        </div>
    </header>

    <div id="msg" style="display:none"></div>

    <div id="progress-box" class="progress-box">
        <strong style="color:#6666ff">Scraping Progress</strong>
        <div class="progress-bar"><div id="pbar" class="progress-fill">0%</div></div>
        <div id="action-text" class="action-text">Waiting...</div>
        <details open>
            <summary style="color:#888;cursor:pointer;margin-top:10px;font-size:.9em">Action Log</summary>
            <div id="log-box" class="log-box"></div>
        </details>
    </div>

    <div class="stats" id="stats">
        <div class="stat-card"><div class="stat-val" id="s-deals">0</div><div class="stat-lbl">Deals Found</div></div>
        <div class="stat-card"><div class="stat-val" id="s-profit">&pound;0</div><div class="stat-lbl">Total Profit</div></div>
        <div class="stat-card"><div class="stat-val" id="s-avg">&pound;0</div><div class="stat-lbl">Avg Profit</div></div>
        <div class="stat-card"><div class="stat-val" id="s-margin">0%</div><div class="stat-lbl">Best Margin</div></div>
    </div>

    <div class="deals-box">
        <h2 style="color:#00ff88;margin-bottom:15px">Profitable Deals</h2>
        <div id="deals"></div>
    </div>
</div>

<script>
var polling = null;
var statusPoll = null;

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
        var deals = JSON.parse(xhr.responseText);
        var container = document.getElementById('deals');

        if (deals.length === 0) {
            container.innerHTML = '<div class="loading">No deals found yet. Click "Scrape Live Data" or "Demo Mode" to find deals.</div>';
            document.getElementById('stats').style.display = 'none';
            return;
        }

        // Update stats
        var totalProfit = 0;
        var bestMargin = 0;
        for (var i = 0; i < deals.length; i++) {
            totalProfit += deals[i].net_profit;
            if (deals[i].profit_margin > bestMargin) bestMargin = deals[i].profit_margin;
        }
        var avgProfit = Math.round(totalProfit / deals.length);

        document.getElementById('s-deals').textContent = deals.length;
        document.getElementById('s-profit').innerHTML = '&pound;' + totalProfit.toLocaleString();
        document.getElementById('s-avg').innerHTML = '&pound;' + avgProfit.toLocaleString();
        document.getElementById('s-margin').textContent = bestMargin.toFixed(1) + '%';
        document.getElementById('stats').style.display = 'grid';

        // Render deal cards
        var html = '';
        for (var i = 0; i < deals.length; i++) {
            var d = deals[i];
            html += '<div class="deal-card">';
            html += '<div class="deal-title">' + escHtml(d.title) + '</div>';
            html += '<div class="deal-grid">';
            html += '<div><div class="deal-lbl">Buy Price</div><div class="deal-val">&pound;' + d.price.toLocaleString() + '</div></div>';
            html += '<div><div class="deal-lbl">Sell Price (NI)</div><div class="deal-val">&pound;' + d.expected_ni_price.toLocaleString() + '</div></div>';
            html += '<div><div class="deal-lbl">Net Profit</div><div class="deal-val deal-profit">&pound;' + d.net_profit.toLocaleString() + '</div></div>';
            html += '<div><div class="deal-lbl">Margin</div><div class="deal-val">' + d.profit_margin.toFixed(1) + '%</div></div>';
            html += '<div><div class="deal-lbl">Location</div><div class="deal-val">' + escHtml(d.location) + ' (' + d.distance + ' mi)</div></div>';
            html += '<div><div class="deal-lbl">Source</div><div class="deal-val">' + escHtml(d.source) + '</div></div>';
            html += '</div>';
            if (d.url) {
                html += '<a href="' + escAttr(d.url) + '" target="_blank" class="deal-link">View Listing &rarr;</a>';
            }
            html += '</div>';
        }
        container.innerHTML = html;
    };
    xhr.onerror = function() {};
    xhr.send();
}

function showMsg(text, color) {
    var el = document.getElementById('msg');
    el.textContent = text;
    el.style.display = 'block';
    el.style.textAlign = 'center';
    el.style.padding = '12px';
    el.style.margin = '15px 0';
    el.style.borderRadius = '8px';
    el.style.fontSize = '1em';
    el.style.color = color;
    el.style.background = 'rgba(' + (color === '#ff4444' ? '255,68,68' : color === '#00ff88' ? '0,255,136' : '255,170,0') + ',.15)';
    el.style.border = '1px solid ' + color;

    if (color === '#00ff88') {
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
            tag.style.cssText = 'position:fixed;bottom:5px;right:5px;background:#1a1f3a;color:#6666ff;padding:4px 10px;border-radius:4px;font-size:11px;border:1px solid #6666ff44;z-index:9999';
            tag.textContent = v.version;
            document.body.appendChild(tag);
        } else {
            console.log('Version check failed - OLD CODE may be running');
            var tag = document.createElement('div');
            tag.style.cssText = 'position:fixed;bottom:5px;right:5px;background:#ff4444;color:#fff;padding:4px 10px;border-radius:4px;font-size:11px;z-index:9999';
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
<title>Search Links - Car Arbitrage</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#0a0e27,#1a1f3a);color:#e0e0e0;padding:20px;min-height:100vh}
.container{max-width:1400px;margin:0 auto}
header{text-align:center;margin-bottom:30px;padding:25px;background:rgba(26,31,58,.6);border-radius:16px;border:1px solid #00ff8833}
h1{color:#00ff88;font-size:2em;margin-bottom:8px}
.back{display:inline-block;margin-top:12px;padding:8px 18px;background:linear-gradient(135deg,#6666ff,#4444dd);color:#fff;text-decoration:none;border-radius:8px;font-weight:600}
.car-section{background:#1a1f3a;border-radius:12px;padding:22px;margin-bottom:18px;border:1px solid #00ff8833}
.car-header{margin-bottom:15px;padding-bottom:12px;border-bottom:1px solid #2a2f4a}
.car-name{font-size:1.4em;color:#00ff88;font-weight:700}
.car-info{color:#888;font-size:.85em;margin-top:4px}
.links-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.site-link{background:#2a2f4a;padding:18px;border-radius:10px;border:1px solid #00ff8844;text-decoration:none;display:block;transition:all .3s}
.site-link:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,255,136,.2);border-color:#00ff88}
.site-name{font-size:1.1em;color:#6666ff;font-weight:700;margin-bottom:6px}
.open-btn{display:inline-block;padding:6px 14px;background:linear-gradient(135deg,#6666ff,#4444dd);color:#fff;border-radius:6px;font-size:.85em;font-weight:600}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Quick Search Links</h1>
        <p style="color:#888">Direct links to car listings with pre-filled search criteria</p>
        <a href="/" class="back">&larr; Back to Dashboard</a>
    </header>
    {{CAR_SECTIONS}}
</div>
</body>
</html>'''


if __name__ == '__main__':
    app.config['START_TIME'] = datetime.now().isoformat()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load demo data on startup
    try:
        finder = CarArbitrageFinder()
        finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
        latest_deals = [deal_to_dict(d) for d in sorted(finder.profitable_deals, key=lambda x: x.net_profit, reverse=True)]
        print(f"Loaded {len(latest_deals)} demo deals on startup")
    except Exception as e:
        print(f"WARNING: Could not load demo data: {e}")
        latest_deals = []

    print("\n" + "="*60)
    print("  CAR ARBITRAGE WEB APP STARTING")
    print("="*60)
    print("\nDashboard: http://localhost:5000")
    print("API:       http://localhost:5000/api/deals")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
