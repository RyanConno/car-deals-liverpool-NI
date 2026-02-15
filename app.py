#!/usr/bin/env python3
"""
Flask Web Application for Car Arbitrage Scraper
Provides REST API and web interface for car deals
"""

from flask import Flask, jsonify, render_template_string, send_file, request
from flask_cors import CORS
import os
import json
from datetime import datetime
import threading
from pathlib import Path

# Import the scraper
from car_scraper import CarArbitrageFinder, create_sample_data, OUTPUT_DIR, TARGET_CARS

app = Flask(__name__)
CORS(app)

# Global state
scraper_status = {
    'running': False,
    'last_run': None,
    'last_result': None,
    'error': None
}

latest_deals = []
current_finder = None  # Reference to active scraper instance


def update_deals_from_finder(finder):
    """Convert finder's deals to API format"""
    global latest_deals
    latest_deals = [
        {
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
        for d in sorted(finder.profitable_deals, key=lambda x: x.net_profit, reverse=True)
    ]


def run_scraper_background(use_demo=False):
    """Run the scraper in background"""
    global scraper_status, latest_deals, current_finder

    try:
        scraper_status['running'] = True
        scraper_status['error'] = None
        latest_deals = []  # Clear existing deals immediately

        finder = CarArbitrageFinder()
        current_finder = finder  # Make finder accessible globally

        if use_demo:
            finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
            update_deals_from_finder(finder)
        else:
            # Start a monitor thread to update deals in real-time
            def monitor_deals():
                while scraper_status['running']:
                    if finder.profitable_deals:
                        update_deals_from_finder(finder)
                    threading.Event().wait(2)  # Update every 2 seconds

            monitor_thread = threading.Thread(target=monitor_deals, daemon=True)
            monitor_thread.start()

            finder.search_all()
            update_deals_from_finder(finder)  # Final update

        # Store results (keep existing code)
        update_deals_from_finder(finder)

        # Export files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"{OUTPUT_DIR}/deals_{timestamp}.csv"
        html_file = f"{OUTPUT_DIR}/deals_{timestamp}.html"

        finder.export_csv(csv_file)
        finder.export_html(html_file)

        scraper_status['last_run'] = datetime.now().isoformat()
        scraper_status['last_result'] = {
            'total_deals': len(latest_deals),
            'total_profit': sum(d['net_profit'] for d in latest_deals),
            'csv_file': csv_file,
            'html_file': html_file
        }

    except Exception as e:
        scraper_status['error'] = str(e)
        print(f"Scraper error: {e}")
    finally:
        scraper_status['running'] = False


@app.route('/')
def index():
    """Main dashboard - shows live car deals"""
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Car Arbitrage - Liverpool to NI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
            background: rgba(26, 31, 58, 0.6);
            border-radius: 16px;
            border: 1px solid #00ff8833;
        }
        h1 {
            color: #00ff88;
            font-size: 3em;
            margin-bottom: 15px;
            text-shadow: 0 0 30px rgba(0,255,136,0.6);
        }
        .subtitle { color: #888; font-size: 1.2em; margin-bottom: 20px; }
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 25px;
        }
        button, .btn-link {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #0a0e27;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-decoration: none;
            display: inline-block;
        }
        button:hover, .btn-link:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,255,136,0.4);
        }
        button:disabled {
            background: #555;
            color: #888;
            cursor: not-allowed;
            transform: none;
        }
        .btn-secondary {
            background: linear-gradient(135deg, #6666ff 0%, #4444dd 100%);
            color: white;
        }
        .btn-search {
            background: linear-gradient(135deg, #ffaa00 0%, #ff8800 100%);
            color: white;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #00ff8833;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            color: #00ff88;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .stat-label {
            color: #888;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }
        .status {
            text-align: center;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            font-size: 1.1em;
        }
        .status.running {
            background: rgba(255,170,0,0.2);
            color: #ffaa00;
            border: 1px solid #ffaa00;
        }
        .status.success {
            background: rgba(0,255,136,0.2);
            color: #00ff88;
            border: 1px solid #00ff88;
        }
        .status.error {
            background: rgba(255,68,68,0.2);
            color: #ff4444;
            border: 1px solid #ff4444;
        }
        .deals-container {
            background: #1a1f3a;
            border-radius: 16px;
            padding: 30px;
            margin: 30px 0;
            border: 1px solid #00ff8833;
        }
        .deal-card {
            background: #2a2f4a;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 4px solid #00ff88;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .deal-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 20px rgba(0,255,136,0.3);
        }
        .deal-title {
            font-size: 1.3em;
            color: #fff;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .deal-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin: 15px 0;
        }
        .info-item {
            display: flex;
            flex-direction: column;
        }
        .info-label {
            color: #888;
            font-size: 0.8em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .info-value {
            color: #fff;
            font-size: 1.1em;
            font-weight: 600;
        }
        .profit-highlight {
            color: #00ff88;
            font-size: 1.4em;
        }
        .link-btn {
            display: inline-block;
            margin-top: 12px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6666ff 0%, #4444dd 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .link-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102,102,255,0.4);
        }
        .api-docs {
            background: #1a1f3a;
            padding: 25px;
            border-radius: 12px;
            margin: 30px 0;
            border: 1px solid #6666ff33;
        }
        .api-docs h2 {
            color: #6666ff;
            margin-bottom: 15px;
        }
        .api-endpoint {
            background: #2a2f4a;
            padding: 12px 15px;
            margin: 10px 0;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            color: #00ff88;
            border-left: 3px solid #6666ff;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #888;
        }
        .spinner {
            border: 4px solid #2a2f4a;
            border-top: 4px solid #00ff88;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏎️ Car Arbitrage Dashboard</h1>
            <p class="subtitle">Liverpool → Northern Ireland | Live Drift & Race Car Deals</p>
            <div class="controls">
                <a href="/search-links" class="btn-link btn-search">🔗 Manual Search Links</a>
                <button onclick="runScraper(false)" id="scrape-btn">🔍 Scrape Live Data</button>
                <button onclick="runScraper(true)" class="btn-secondary">🎬 Demo Mode</button>
                <button onclick="loadDeals()" class="btn-secondary">🔄 Refresh</button>
            </div>
        </header>

        <div id="status"></div>

        <div class="stats" id="stats" style="display:none;">
            <div class="stat-card">
                <div class="stat-value" id="total-deals">0</div>
                <div class="stat-label">Total Deals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-profit">£0</div>
                <div class="stat-label">Total Profit</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-profit">£0</div>
                <div class="stat-label">Avg Profit/Car</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="best-margin">0%</div>
                <div class="stat-label">Best Margin</div>
            </div>
        </div>

        <div class="deals-container">
            <h2 style="color: #00ff88; margin-bottom: 20px;">💰 Profitable Deals</h2>
            <div id="deals-list"></div>
        </div>

        <div class="api-docs">
            <h2>📡 Quick Links</h2>
            <p style="color: #888; margin-bottom: 15px;">Direct access to tools and searches:</p>
            <div class="api-endpoint"><a href="/search-links" style="color: #00ff88; text-decoration: none;">🔗 Quick Search Links - Browse cars on AutoTrader, Gumtree, PistonHeads</a></div>
            <div class="api-endpoint">GET /api/deals - Get all current deals (JSON)</div>
            <div class="api-endpoint">GET /api/status - Get scraper status</div>
            <div class="api-endpoint">POST /api/scrape?demo=true - Run scraper</div>
            <div class="api-endpoint">GET /api/models - Get target car models</div>
        </div>
    </div>

    <script>
        let statusCheckInterval;
        let dealsPollingInterval;

        async function runScraper(demo) {
            const btn = document.getElementById('scrape-btn');
            btn.disabled = true;

            // Clear existing deals immediately
            const dealsList = document.getElementById('deals-list');
            dealsList.innerHTML = '<div class="loading"><div class="spinner"></div>Searching for deals...</div>';
            document.getElementById('stats').style.display = 'none';

            const url = demo ? '/api/scrape?demo=true' : '/api/scrape';

            try {
                const response = await fetch(url, { method: 'POST' });
                const data = await response.json();

                if (data.status === 'started') {
                    showStatus('Scraper running... This may take 5-15 minutes', 'running');
                    statusCheckInterval = setInterval(checkStatus, 3000);

                    // Start polling for deals in real-time
                    dealsPollingInterval = setInterval(loadDeals, 2000);
                }
            } catch (error) {
                showStatus('Error starting scraper: ' + error.message, 'error');
                btn.disabled = false;
            }
        }

        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                if (!data.running && data.last_run) {
                    clearInterval(statusCheckInterval);
                    clearInterval(dealsPollingInterval);  // Stop polling
                    document.getElementById('scrape-btn').disabled = false;

                    if (data.error) {
                        showStatus('Scraper error: ' + data.error, 'error');
                    } else {
                        showStatus('✓ Scraper completed successfully!', 'success');
                        loadDeals();  // Final update
                    }
                }
            } catch (error) {
                console.error('Status check failed:', error);
            }
        }

        async function loadDeals() {
            const dealsList = document.getElementById('deals-list');

            try {
                const response = await fetch('/api/deals');
                const deals = await response.json();

                // Check if scraper is running
                const statusResponse = await fetch('/api/status');
                const status = await statusResponse.json();

                if (deals.length === 0) {
                    if (status.running) {
                        dealsList.innerHTML = '<div class="loading"><div class="spinner"></div>Searching... No deals found yet.</div>';
                    } else {
                        dealsList.innerHTML = '<div class="loading">No deals found. Run the scraper to find opportunities!</div>';
                    }
                    document.getElementById('stats').style.display = 'none';
                    return;
                }

                // Update stats
                const totalProfit = deals.reduce((sum, d) => sum + d.net_profit, 0);
                const avgProfit = totalProfit / deals.length;
                const bestMargin = Math.max(...deals.map(d => d.profit_margin));

                document.getElementById('total-deals').textContent = deals.length;
                document.getElementById('total-profit').textContent = '£' + totalProfit.toLocaleString();
                document.getElementById('avg-profit').textContent = '£' + Math.round(avgProfit).toLocaleString();
                document.getElementById('best-margin').textContent = bestMargin.toFixed(1) + '%';
                document.getElementById('stats').style.display = 'grid';

                // Add live update indicator if scraper is running
                let liveIndicator = '';
                if (status.running) {
                    liveIndicator = '<div style="background: rgba(255, 170, 0, 0.2); border-left: 4px solid #ffaa00; padding: 15px; margin-bottom: 20px; border-radius: 8px;"><strong>🔄 Live Updates:</strong> Deals are being added as they\'re found...</div>';
                }

                // Render deals
                dealsList.innerHTML = liveIndicator + deals.map(deal => `
                    <div class="deal-card">
                        <div class="deal-title">${deal.title}</div>
                        <div class="deal-info">
                            <div class="info-item">
                                <span class="info-label">Buy Price</span>
                                <span class="info-value">£${deal.price.toLocaleString()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Avg UK Price</span>
                                <span class="info-value" style="color: #888;">£${deal.avg_uk_price.toLocaleString()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Sell Price (NI)</span>
                                <span class="info-value">£${deal.expected_ni_price.toLocaleString()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Avg NI Price</span>
                                <span class="info-value" style="color: #888;">£${deal.avg_ni_price.toLocaleString()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Net Profit</span>
                                <span class="info-value profit-highlight">£${deal.net_profit.toLocaleString()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Margin</span>
                                <span class="info-value">${deal.profit_margin.toFixed(1)}%</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Location</span>
                                <span class="info-value">${deal.location} (${deal.distance} mi)</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Details</span>
                                <span class="info-value">${deal.year} | ${deal.mileage} mi</span>
                            </div>
                        </div>
                        <a href="${deal.url}" target="_blank" class="link-btn">View Listing →</a>
                    </div>
                `).join('');

            } catch (error) {
                dealsList.innerHTML = `<div class="loading">Error loading deals: ${error.message}</div>`;
            }
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = message;
            statusDiv.className = `status ${type}`;
            statusDiv.style.display = 'block';

            if (type === 'success') {
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);
            }
        }

        // Load deals on page load
        loadDeals();
    </script>
</body>
</html>
    '''
    return render_template_string(html)


@app.route('/api/deals')
def get_deals():
    """API endpoint to get current deals as JSON"""
    return jsonify(latest_deals)


@app.route('/api/status')
def get_status():
    """Get scraper status"""
    return jsonify(scraper_status)


@app.route('/api/scrape', methods=['POST'])
def run_scrape():
    """Trigger a scraper run"""
    if scraper_status['running']:
        return jsonify({'status': 'already_running'}), 409

    use_demo = request.args.get('demo', 'false').lower() == 'true'

    # Run in background thread
    thread = threading.Thread(target=run_scraper_background, args=(use_demo,))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'demo': use_demo})


@app.route('/api/models')
def get_models():
    """Get target car models configuration"""
    models_info = {
        model: {
            'search_terms': config['search_terms'],
            'max_price': config['max_price'],
            'ni_markup': config['ni_markup'],
            'min_profit': config['min_profit']
        }
        for model, config in TARGET_CARS.items()
    }
    return jsonify(models_info)


@app.route('/health')
def health():
    """Health check endpoint for load balancers"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/search-links')
def search_links():
    """Generate direct search links to car websites"""
    from urllib.parse import urlencode

    car_models = []
    for model_key, config in TARGET_CARS.items():
        search_term = config['search_terms'][0]  # Use first search term
        max_price = config['max_price']

        # AutoTrader link
        autotrader_params = {
            'postcode': 'L1',
            'radius': '200',
            'price-to': str(max_price),
            'sort': 'price-asc'
        }
        autotrader_url = f"https://www.autotrader.co.uk/car-search?{urlencode(autotrader_params)}&search={search_term.replace(' ', '+')}"

        # Gumtree link
        gumtree_params = {
            'search_category': 'cars',
            'q': search_term,
            'search_location': 'Liverpool',
            'distance': '200',
            'max_price': str(max_price),
            'sort': 'price_asc'
        }
        gumtree_url = f"https://www.gumtree.com/search?{urlencode(gumtree_params)}"

        # PistonHeads link
        pistonheads_params = {
            'keywords': search_term,
            'price_to': str(max_price)
        }
        pistonheads_url = f"https://www.pistonheads.com/classifieds/used-cars?{urlencode(pistonheads_params)}"

        car_models.append({
            'name': model_key.replace('_', ' ').title(),
            'search_term': search_term,
            'max_price': max_price,
            'autotrader': autotrader_url,
            'gumtree': gumtree_url,
            'pistonheads': pistonheads_url
        })

    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quick Search Links - Car Arbitrage</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 20px;
            background: rgba(26, 31, 58, 0.6);
            border-radius: 16px;
            border: 1px solid #00ff8833;
        }
        h1 {
            color: #00ff88;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 0 30px rgba(0,255,136,0.6);
        }
        .subtitle { color: #888; font-size: 1em; }
        .back-btn {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #6666ff 0%, #4444dd 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }
        .back-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102,102,255,0.4);
        }
        .controls {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #00ff8833;
        }
        .controls label {
            color: #00ff88;
            font-weight: 600;
            margin-right: 10px;
        }
        .controls input {
            background: #2a2f4a;
            color: #e0e0e0;
            border: 1px solid #00ff8833;
            padding: 8px 12px;
            border-radius: 6px;
            margin: 5px;
            width: 120px;
        }
        .controls button {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #0a0e27;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            margin-left: 10px;
        }
        .car-section {
            background: #1a1f3a;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid #00ff8833;
        }
        .car-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #2a2f4a;
        }
        .car-name {
            font-size: 1.5em;
            color: #00ff88;
            font-weight: 700;
        }
        .car-info {
            color: #888;
            font-size: 0.9em;
        }
        .links-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        .site-link {
            background: linear-gradient(135deg, #2a2f4a 0%, #3a3f5a 100%);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #00ff8844;
            transition: all 0.3s;
            text-decoration: none;
            display: block;
        }
        .site-link:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,255,136,0.3);
            border-color: #00ff88;
        }
        .site-name {
            font-size: 1.2em;
            color: #6666ff;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .site-desc {
            color: #aaa;
            font-size: 0.85em;
            margin-bottom: 12px;
        }
        .open-btn {
            display: inline-block;
            padding: 8px 16px;
            background: linear-gradient(135deg, #6666ff 0%, #4444dd 100%);
            color: white;
            border-radius: 6px;
            font-size: 0.9em;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔗 Quick Search Links</h1>
            <p class="subtitle">Direct links to car listings with pre-filled search criteria</p>
            <a href="/" class="back-btn">← Back to Dashboard</a>
        </header>

        <div class="controls">
            <label>📍 Location:</label>
            <input type="text" id="location" value="Liverpool" placeholder="Liverpool">

            <label>📏 Radius:</label>
            <input type="number" id="radius" value="200" placeholder="200"> miles

            <button onclick="updateLinks()">🔄 Update Links</button>
        </div>

        <div id="cars-list">
    '''

    for car in car_models:
        html += f'''
        <div class="car-section">
            <div class="car-header">
                <div>
                    <div class="car-name">{car['name']}</div>
                    <div class="car-info">Search: "{car['search_term']}" | Max Price: £{car['max_price']:,}</div>
                </div>
            </div>
            <div class="links-grid">
                <a href="{car['autotrader']}" target="_blank" class="site-link">
                    <div class="site-name">🚗 AutoTrader UK</div>
                    <div class="site-desc">UK's largest digital automotive marketplace</div>
                    <span class="open-btn">Open Search →</span>
                </a>
                <a href="{car['gumtree']}" target="_blank" class="site-link">
                    <div class="site-name">📋 Gumtree</div>
                    <div class="site-desc">Free classified ads - often bargains here</div>
                    <span class="open-btn">Open Search →</span>
                </a>
                <a href="{car['pistonheads']}" target="_blank" class="site-link">
                    <div class="site-name">🏎️ PistonHeads</div>
                    <div class="site-desc">Enthusiast cars and performance vehicles</div>
                    <span class="open-btn">Open Search →</span>
                </a>
            </div>
        </div>
        '''

    html += '''
        </div>
    </div>

    <script>
        function updateLinks() {
            const location = document.getElementById('location').value;
            const radius = document.getElementById('radius').value;

            // Reload page with new parameters
            window.location.href = `/search-links?location=${encodeURIComponent(location)}&radius=${radius}`;
        }
    </script>
</body>
</html>
    '''

    return html


if __name__ == '__main__':
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load demo data on startup
    finder = CarArbitrageFinder()
    finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
    latest_deals = [
        {
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
        for d in sorted(finder.profitable_deals, key=lambda x: x.net_profit, reverse=True)
    ]

    # Run Flask app
    print("\n" + "="*60)
    print("  CAR ARBITRAGE WEB APP STARTING")
    print("="*60)
    print("\n🌐 Access the dashboard at: http://localhost:5000")
    print("📡 API endpoints available at: http://localhost:5000/api/*")
    print("\n" + "="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
