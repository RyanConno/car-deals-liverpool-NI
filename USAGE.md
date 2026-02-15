# Car Arbitrage Scraper - Complete Usage Guide

## Installation

### 1. Install Python
Make sure you have Python 3.8 or higher installed:
```bash
python --version
# or
python3 --version
```

If not installed, download from [python.org](https://www.python.org/downloads/)

### 2. Install Dependencies
```bash
# Navigate to the project directory
cd c:\Users\Ryan Connolly\Downloads\files

# Install required packages
pip install -r requirements.txt

# Or install manually
pip install requests beautifulsoup4 lxml
```

## Running the Scraper

### Demo Mode (Safe Testing)

Run with sample data to see how everything works:

```bash
python car_scraper.py --demo
```

**What happens:**
- Uses 7 pre-loaded sample car listings
- Calculates profit margins
- Generates HTML report and CSV file
- No actual web requests made
- Safe to run unlimited times

**Output:**
```
car_deals/
├── deals_20260212_143022.csv   # Spreadsheet data
└── deals_20260212_143022.html  # Interactive dashboard
```

### Live Mode (Real Web Scraping)

Search actual websites for real deals:

```bash
python car_scraper.py
```

**What happens:**
1. Displays legal/ethical notice
2. Searches AutoTrader UK
3. Searches Gumtree UK
4. Searches PistonHeads
5. Filters for profitable deals
6. Generates reports

**Expected runtime:** 5-15 minutes depending on results found

**Legal considerations displayed:**
```
⚖️  This scraper respects robots.txt and uses rate limiting
⏱️  Random delays (2-5s) between requests to avoid server load
🤝 Please use responsibly and respect website Terms of Service
```

## Understanding the Output

### HTML Report (Interactive Dashboard)

Open `car_deals/deals_TIMESTAMP.html` in your browser to see:

**Statistics Dashboard:**
- Total profitable deals found
- Total potential profit
- Average profit per car
- Best profit margin

**Interactive Filters:**
- Filter by car model
- Minimum profit threshold
- Maximum distance from Liverpool

**Sortable Table:**
- Click column headers to sort
- Hover over rows for highlight
- Click "View →" to open listing

### CSV File (Spreadsheet Data)

Open `car_deals/deals_TIMESTAMP.csv` in Excel/Google Sheets:

**Columns:**
- Model Type
- Title
- Price (Buy price)
- Expected NI Price (Sell price)
- Net Profit (After £450 costs)
- Profit Margin %
- Location
- Distance from Liverpool
- Year
- Mileage
- Source (Website)
- URL (Direct link)

## Customization

### Change Search Location

Edit [car_scraper.py](car_scraper.py#L20):
```python
LIVERPOOL_COORDS = (53.4084, -2.9916)  # Change to your coordinates
MAX_DISTANCE_MILES = 100  # Adjust search radius
```

### Change Costs

Edit [car_scraper.py](car_scraper.py#L23):
```python
COSTS_PER_CAR = 450  # Adjust based on your actual costs

# Breakdown:
# - Ferry: £150 (Liverpool-Belfast return)
# - Fuel: £50
# - Insurance/Admin: £200
# - Your time: £50
```

### Add/Remove Car Models

Edit [car_scraper.py](car_scraper.py#L26):
```python
TARGET_CARS = {
    'your_custom_model': {
        'search_terms': ['Search Term 1', 'Search Term 2'],
        'max_price': 15000,      # Maximum purchase price
        'ni_markup': 3000,       # Expected NI market premium
        'min_profit': 1500       # Minimum acceptable profit
    }
}
```

### Change Profit Thresholds

Adjust per-model in TARGET_CARS:
```python
'bmw_e46_330': {
    'search_terms': ['BMW 330i', 'BMW 330ci', 'E46 330'],
    'max_price': 12000,    # Increase to see higher-priced cars
    'ni_markup': 2500,     # Adjust based on market research
    'min_profit': 1000     # Raise to filter for better deals only
}
```

## Real-World Usage Examples

### Example 1: Daily Deal Hunting

```bash
# Run once in the morning
python car_scraper.py

# Review the HTML report
# Contact sellers for top 3-5 opportunities
# Check if cars are still available
```

**Best practice:** Run 1-2 times per day maximum

### Example 2: Focus on Specific Models

Edit TARGET_CARS to only include models you're interested in:

```python
TARGET_CARS = {
    'nissan_200sx': {  # Only search for 200SX
        'search_terms': ['Nissan 200SX', 'Nissan Silvia', '200SX S13', '200SX S14'],
        'max_price': 20000,
        'ni_markup': 4000,
        'min_profit': 2000
    }
}
```

### Example 3: Higher Profit Margins Only

Increase min_profit across all models:

```python
'bmw_e46_330': {
    'search_terms': ['BMW 330i', 'BMW 330ci', 'E46 330'],
    'max_price': 10000,
    'ni_markup': 2000,
    'min_profit': 1500  # Changed from 800 to 1500
}
```

## Troubleshooting

### No Results Found

**Problem:** Scraper runs but finds 0 profitable deals

**Solutions:**
1. **Lower profit threshold:**
   ```python
   'min_profit': 500  # Instead of 800+
   ```

2. **Increase max price:**
   ```python
   'max_price': 15000  # Instead of 10000
   ```

3. **Expand search radius:**
   ```python
   MAX_DISTANCE_MILES = 150  # Instead of 100
   ```

4. **Run multiple times:** Listings change throughout the day

### Connection Errors

**Problem:** `RequestException` or `ConnectionError`

**Solutions:**
- Check your internet connection
- Some sites may be temporarily down
- Try again in a few minutes
- VPN may interfere with some sites

### HTML Report Not Opening

**Problem:** HTML file won't open or looks broken

**Solutions:**
- Right-click → Open With → Chrome/Firefox/Edge
- Check that the file isn't corrupted (should be ~50KB+)
- Re-run the scraper to generate a fresh report

### Python Not Found

**Problem:** `Python was not found`

**Solutions:**
```bash
# Windows: Download from python.org
# Make sure to check "Add Python to PATH" during installation

# macOS:
brew install python3

# Linux:
sudo apt-get install python3
```

## Legal & Ethical Guidelines

### ✅ DO:
- Run 1-3 times per day maximum
- Review results manually
- Respect rate limiting (built-in)
- Use for personal deal hunting
- Consider using official APIs for commercial use

### ❌ DON'T:
- Run continuously or very frequently
- Circumvent rate limiting
- Ignore robots.txt (script respects it automatically)
- Use for large-scale commercial scraping without permission
- Modify scraper to be more aggressive

### Website Terms of Service

Be aware that web scraping may violate some website Terms of Service:

- **AutoTrader UK:** Has official Dealer API for commercial use
- **Gumtree UK:** Allows public data viewing but may restrict automation
- **PistonHeads:** Generally enthusiast-friendly but check ToS

**Recommendation for commercial use:**
- Contact websites for API access
- Join dealer programs where available
- Use manual saved searches with email alerts

## Advanced Usage

### Custom Output Location

```bash
python car_scraper.py --output custom_name

# Generates:
# - custom_name.csv
# - custom_name.html
```

### Analyzing Historical Data

Run daily and compare CSV files:
```bash
python car_scraper.py --output "deals_$(date +%Y%m%d)"

# Creates dated files:
# deals_20260212.csv
# deals_20260213.csv
# etc.

# Import into Excel/Google Sheets to track:
# - Price trends
# - Which models appear most often
# - Average profit margins over time
```

### Integration Ideas

**Send Results via Email:**
```python
# Add at end of main():
import smtplib
from email.mime.text import MIMEText

# Send email with HTML report attached
```

**Telegram/Discord Notifications:**
```python
import requests

# Post to webhook when good deals found
if len(finder.profitable_deals) > 0:
    webhook_url = "YOUR_WEBHOOK_URL"
    requests.post(webhook_url, json={"text": f"Found {len(finder.profitable_deals)} deals!"})
```

## Next Steps After Finding Deals

1. **Verify Listing:**
   - Click "View →" button in HTML report
   - Check if car is still available
   - Verify photos match description

2. **Research NI Market:**
   - Check DoneDeal.ie for similar cars
   - Verify your expected sell price is realistic
   - Check JDM NI Facebook groups

3. **Contact Seller:**
   - Ask for additional photos
   - Request service history
   - Check MOT history online
   - Arrange viewing

4. **Calculate True Profit:**
   ```
   Buy Price:          £8,500
   Ferry:              £150
   Fuel:               £50
   Insurance/Admin:    £200
   Unexpected costs:   £100
   -------------------------
   Total Cost:         £9,000

   Expected NI Sale:   £10,500
   -------------------------
   Net Profit:         £1,500
   ```

5. **Due Diligence:**
   - HPI check
   - Test drive
   - Inspection
   - Negotiate price

## Support & Questions

For issues with the scraper:
1. Check this USAGE.md file
2. Review README.md
3. Check error messages in terminal
4. Verify Python dependencies are installed

For Northern Ireland car market questions:
- RMS Motoring Forum
- DriftedNI Facebook
- JDM Northern Ireland groups

## Tips for Success

**Market Knowledge:**
- Join NI car shows and groups first
- Understand what's in demand
- Build relationships with buyers
- Know realistic NI prices

**Finding Best Deals:**
- Run scraper in morning (new listings)
- Act fast on good deals (they sell within hours)
- Build rapport with sellers
- Be ready to collect immediately

**Maximizing Profit:**
- Negotiate purchase price
- Book cheap ferry times
- Buy multiple cars per trip (split ferry cost)
- Focus on high-margin models (Nissan 200SX, Skylines)
- Sell at peak times (Feb-March, Sept-Oct)

Good luck finding profitable deals! 🏎️💰
