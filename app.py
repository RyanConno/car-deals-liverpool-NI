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


def run_scraper_background(use_demo=False):
    """Run the scraper in background"""
    global scraper_status, latest_deals

    try:
        scraper_status['running'] = True
        scraper_status['error'] = None

        finder = CarArbitrageFinder()

        if use_demo:
            finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
        else:
            finder.search_all()

        # Store results
        latest_deals = [
            {
                'model_type': d.model_type,
                'title': d.title,
                'price': d.price,
                'expected_ni_price': d.expected_ni_price,
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
        button {
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
        }
        button:hover {
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
            <h2>📡 API Endpoints</h2>
            <p style="color: #888; margin-bottom: 15px;">Access car deals programmatically:</p>
            <div class="api-endpoint">GET /api/deals - Get all current deals (JSON)</div>
            <div class="api-endpoint">GET /api/status - Get scraper status</div>
            <div class="api-endpoint">POST /api/scrape?demo=true - Run scraper</div>
            <div class="api-endpoint">GET /api/models - Get target car models</div>
        </div>
    </div>

    <script>
        let statusCheckInterval;

        async function runScraper(demo) {
            const btn = document.getElementById('scrape-btn');
            btn.disabled = true;

            const url = demo ? '/api/scrape?demo=true' : '/api/scrape';

            try {
                const response = await fetch(url, { method: 'POST' });
                const data = await response.json();

                if (data.status === 'started') {
                    showStatus('Scraper running... This may take 5-15 minutes', 'running');
                    statusCheckInterval = setInterval(checkStatus, 3000);
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
                    document.getElementById('scrape-btn').disabled = false;

                    if (data.error) {
                        showStatus('Scraper error: ' + data.error, 'error');
                    } else {
                        showStatus('✓ Scraper completed successfully!', 'success');
                        loadDeals();
                    }
                }
            } catch (error) {
                console.error('Status check failed:', error);
            }
        }

        async function loadDeals() {
            const dealsList = document.getElementById('deals-list');
            dealsList.innerHTML = '<div class="loading"><div class="spinner"></div>Loading deals...</div>';

            try {
                const response = await fetch('/api/deals');
                const deals = await response.json();

                if (deals.length === 0) {
                    dealsList.innerHTML = '<div class="loading">No deals found. Run the scraper to find opportunities!</div>';
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

                // Render deals
                dealsList.innerHTML = deals.map(deal => `
                    <div class="deal-card">
                        <div class="deal-title">${deal.title}</div>
                        <div class="deal-info">
                            <div class="info-item">
                                <span class="info-label">Buy Price</span>
                                <span class="info-value">£${deal.price.toLocaleString()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Sell Price (NI)</span>
                                <span class="info-value">£${deal.expected_ni_price.toLocaleString()}</span>
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
            'expected_ni_price': d.expected_ni_price,
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
