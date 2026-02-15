# Scraper Configuration Guide

## Current Issue: No Results

If you're getting no results, try these adjustments:

### Quick Fix - More Lenient Settings

Edit `car_scraper.py` and change these values:

```python
# Line 24: Increase search radius
MAX_DISTANCE_MILES = 150  # Was 100

# Lower min_profit for all models to £100-200
# Increase max_price by 20-30%
```

### Recommended Changes:

**BMW E46 330i:**
```python
'max_price': 10000,  # Was 8000
'min_profit': 200,   # Was 500
```

**Lexus IS200:**
```python
'max_price': 6000,   # Was 4500
'min_profit': 100,   # Was 250
```

**BMW E36 328i:**
```python
'max_price': 8000,   # Was 6000
'min_profit': 200,   # Was 400
```

**Nissan 350Z:**
```python
'max_price': 16000,  # Was 14000
'min_profit': 500,   # Was 1000
```

### Add More Car Models

```python
'mazda_mx5': {
    'search_terms': ['Mazda MX-5', 'Mazda MX5', 'Miata'],
    'max_price': 8000,
    'ni_markup': 800,
    'min_profit': 200,
    'avg_uk_price': 5000,
    'avg_ni_price': 5800
},
'bmw_e46_320': {
    'search_terms': ['BMW 320i', 'BMW 320ci', 'E46 320'],
    'max_price': 6000,
    'ni_markup': 600,
    'min_profit': 100,
    'avg_uk_price': 3500,
    'avg_ni_price': 4100
}
```

## Why No Results?

### 1. Web Scraping Not Working
The actual scrapers might not be finding listings. This could be because:
- Website HTML structure changed
- Robots.txt blocking
- Rate limiting
- Wrong CSS selectors

**Test:** Run demo mode to see if filtering works:
```bash
python car_scraper.py --demo
```

If demo works but live doesn't, the scraping logic needs fixing.

### 2. Filters Too Strict
Current settings might be filtering out all deals:
- `min_profit` too high
- `max_price` too low
- `MAX_DISTANCE_MILES` too small

### 3. Not Enough Search Terms
Some models need more search variations:
```python
'search_terms': ['BMW 330i', 'BMW 330ci', 'E46 330', '330i Sport', '330ci M Sport']
```

## Testing Strategy

### Step 1: Test Demo Mode
```bash
python car_scraper.py --demo
```
If this shows results, filtering works.

### Step 2: Test with Very Lenient Settings
Temporarily set:
```python
MAX_DISTANCE_MILES = 200
'min_profit': 0  # Accept any profit
'max_price': 999999  # Accept any price
```

### Step 3: Check Scraper Output
Add debug to see what's being found:
```bash
python car_scraper.py 2>&1 | tee scraper_debug.log
```

Look for:
- "Found X listings on AutoTrader"
- "Found X listings on Gumtree"
- HTTP errors
- Empty responses

## Alternative Approach

If web scraping isn't working well, consider:

1. **Manual Data Entry**: Update sample_data with real deals you find manually
2. **API Access**: Contact AutoTrader/PistonHeads for API access
3. **RSS Feeds**: Some sites offer RSS for new listings
4. **Email Alerts**: Set up saved searches on each platform

## Real-Time Market Check

Visit these URLs to see if cars exist in your criteria:

- **AutoTrader**: https://www.autotrader.co.uk/car-search?postcode=L1&radius=100&make=BMW&model=3%20Series&price-to=10000
- **PistonHeads**: https://www.pistonheads.com/classifieds/used-cars/bmw/e46-3-series-98-06
- **Gumtree**: https://www.gumtree.com/cars/liverpool/bmw+330i

If you see deals manually but scraper finds nothing, the scraping logic needs work.
