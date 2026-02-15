#!/usr/bin/env python3
"""
Car Arbitrage Scraper - Liverpool to Northern Ireland
Scrapes AutoTrader, Gumtree, and PistonHeads for car deals
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
import argparse
import sys
from typing import List, Dict, Tuple
import re
from urllib.parse import urlencode, quote_plus
import random

# Configuration
LIVERPOOL_COORDS = (53.4084, -2.9916)
MAX_DISTANCE_MILES = 300  # VERY LENIENT - covers most of England
OUTPUT_DIR = "./car_deals"
COSTS_PER_CAR = 650  # Ferry £200 + Fuel £100 + Insurance £250 + Admin £100

# TEMPORARY: VERY LENIENT SETTINGS - Testing to prove scraper works
TARGET_CARS = {
    'peugeot_306_dturbo': {
        'search_terms': ['Peugeot 306 D-Turbo', 'Peugeot 306 DTurbo', '306 D Turbo', '306 Diesel'],
        'make': 'Peugeot', 'model': '306',
        'max_price': 5000,
        'ni_markup': 2700,
        'min_profit': 1000,
        'avg_uk_price': 3500,
        'avg_ni_price': 6200
    },
    'lexus_is200': {
        'search_terms': ['Lexus IS200', 'Lexus IS-200', 'IS200 Sport', 'IS200 manual'],
        'make': 'Lexus', 'model': 'IS',
        'max_price': 6000,
        'ni_markup': 2700,
        'min_profit': 1000,
        'avg_uk_price': 3000,
        'avg_ni_price': 5700
    },
    'bmw_e46_330': {
        'search_terms': ['BMW 330i', 'BMW 330ci', 'E46 330', '330i Sport', '330ci M Sport'],
        'make': 'BMW', 'model': '3 Series',
        'max_price': 8000,
        'ni_markup': 2800,
        'min_profit': 1000,
        'avg_uk_price': 5000,
        'avg_ni_price': 7800
    },
    'honda_civic_ep3_type_r': {
        'search_terms': ['Honda Civic Type R EP3', 'Civic EP3 Type R', 'EP3 Type R', 'Honda Civic Type R'],
        'make': 'Honda', 'model': 'Civic',
        'max_price': 12000,
        'ni_markup': 3500,
        'min_profit': 1000,
        'avg_uk_price': 7500,
        'avg_ni_price': 11000,
        'year_min': 2001, 'year_max': 2005,
        'exclude_keywords': ['fn2', 'fk2', 'fk8', 'fl5', '2006', '2007', '2008', '2009', '2010', '2011']
    },
    'bmw_e60_530d': {
        'search_terms': ['BMW 530d', 'E60 530d', '530d Sport', 'BMW 530 diesel'],
        'make': 'BMW', 'model': '5 Series',
        'max_price': 7000,
        'ni_markup': 2700,
        'min_profit': 1000,
        'avg_uk_price': 4500,
        'avg_ni_price': 7200
    },
    'bmw_e60_535d': {
        'search_terms': ['BMW 535d', 'E60 535d', '535d M-Sport', 'BMW 535 diesel'],
        'make': 'BMW', 'model': '5 Series',
        'max_price': 9000,
        'ni_markup': 2800,
        'min_profit': 1000,
        'avg_uk_price': 5500,
        'avg_ni_price': 8300
    },
    'bmw_f30_330d': {
        'search_terms': ['BMW 330d', 'F30 330d', '330d Sport', '330d M-Sport'],
        'make': 'BMW', 'model': '3 Series',
        'max_price': 18000,
        'ni_markup': 3000,
        'min_profit': 1000,
        'avg_uk_price': 12000,
        'avg_ni_price': 15000
    },
    'bmw_f30_335d': {
        'search_terms': ['BMW 335d', 'F30 335d', '335d M-Sport', '335d xDrive'],
        'make': 'BMW', 'model': '3 Series',
        'max_price': 22000,
        'ni_markup': 3500,
        'min_profit': 1000,
        'avg_uk_price': 15000,
        'avg_ni_price': 18500
    }
}

# Fallback images per model (Wikimedia Commons / free stock)
MODEL_IMAGES = {
    'peugeot_306_dturbo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Peugeot_306_front_20080822.jpg/640px-Peugeot_306_front_20080822.jpg',
    'lexus_is200': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/1999-2005_Lexus_IS_200_%28GXE10R%29_sedan_01.jpg/640px-1999-2005_Lexus_IS_200_%28GXE10R%29_sedan_01.jpg',
    'bmw_e46_330': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/BMW_E46_Coup%C3%A9_front_20080111.jpg/640px-BMW_E46_Coup%C3%A9_front_20080111.jpg',
    'honda_civic_ep3_type_r': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Honda_Civic_Type_R_%28EP3%29.jpg/640px-Honda_Civic_Type_R_%28EP3%29.jpg',
    'bmw_e60_530d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/BMW_E60_front_20080417.jpg/640px-BMW_E60_front_20080417.jpg',
    'bmw_e60_535d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/BMW_E60_front_20080417.jpg/640px-BMW_E60_front_20080417.jpg',
    'bmw_f30_330d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/BMW_F30_320d_Sportline_Mineralgrau.jpg/640px-BMW_F30_320d_Sportline_Mineralgrau.jpg',
    'bmw_f30_335d': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/BMW_F30_320d_Sportline_Mineralgrau.jpg/640px-BMW_F30_320d_Sportline_Mineralgrau.jpg',
}

# Headers to mimic a real browser (Linux-compatible)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between two coordinates in miles"""
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return c * 3959


def extract_price(price_str: str) -> int:
    """Extract numeric price from string"""
    if not price_str:
        return 0
    price_str = re.sub(r'[£,\s]', '', str(price_str))
    match = re.search(r'\d+', price_str)
    return int(match.group()) if match else 0


def geocode_location(location: str) -> Tuple[float, float]:
    """Geocode a UK location to approximate coordinates"""
    locations = {
        'manchester': (53.4808, -2.2426),
        'liverpool': (53.4084, -2.9916),
        'chester': (53.1908, -2.8908),
        'warrington': (53.3900, -2.5970),
        'preston': (53.7632, -2.7031),
        'blackpool': (53.8175, -3.0357),
        'bolton': (53.5768, -2.4282),
        'wigan': (53.5450, -2.6318),
        'southport': (53.6472, -3.0054),
        'blackburn': (53.7480, -2.4821),
        'burnley': (53.7895, -2.2482),
        'lancaster': (54.0466, -2.8007),
        'crewe': (53.0979, -2.4416),
        'stoke': (53.0027, -2.1794),
        'leeds': (53.8008, -1.5491),
        'sheffield': (53.3811, -1.4701),
        'york': (53.9600, -1.0873),
        'bradford': (53.7960, -1.7594),
        'huddersfield': (53.6458, -1.7850),
        'birmingham': (52.4862, -1.8904),
        'nottingham': (52.9548, -1.1581),
        'leicester': (52.6369, -1.1398),
        'derby': (52.9225, -1.4746),
        'coventry': (52.4068, -1.5197),
        'wolverhampton': (52.5867, -2.1290),
        'cardiff': (51.4816, -3.1791),
        'swansea': (51.6214, -3.9436),
        'wrexham': (53.0462, -2.9930),
        'newcastle': (54.9783, -1.6178),
        'carlisle': (54.8951, -2.9382),
        'london': (51.5074, -0.1278),
        'bristol': (51.4545, -2.5879),
        'oxford': (51.7520, -1.2577),
        'cambridge': (52.2053, 0.1218),
        'norwich': (52.6309, 1.2974),
        'southampton': (50.9097, -1.4044),
        'portsmouth': (50.8198, -1.0880),
        'brighton': (50.8225, -0.1372),
        'exeter': (50.7184, -3.5339),
        'plymouth': (50.3755, -4.1427),
        'hull': (53.7676, -0.3274),
        'middlesbrough': (54.5742, -1.2350),
        'sunderland': (54.9069, -1.3838),
        'doncaster': (53.5228, -1.1285),
        'wakefield': (53.6833, -1.4977),
        'harrogate': (53.9921, -1.5418),
    }

    location_lower = location.lower().strip()
    for city, coords in locations.items():
        if city in location_lower:
            return coords

    return LIVERPOOL_COORDS


class CarListing:
    """Represents a car listing"""

    def __init__(self, data: dict):
        self.model_type = data.get('model_type', '')
        self.title = data.get('title', '')
        self.price = data.get('price', 0)
        self.location = data.get('location', '')
        self.coords = data.get('coords', LIVERPOOL_COORDS)
        self.url = data.get('url', '')
        self.year = data.get('year', '')
        self.mileage = data.get('mileage', '')
        self.source = data.get('source', '')
        self.image = data.get('image', '') or MODEL_IMAGES.get(self.model_type, '')

        car_config = TARGET_CARS.get(self.model_type, {})
        self.ni_markup = car_config.get('ni_markup', 0)
        self.expected_ni_price = self.price + self.ni_markup
        self.gross_profit = self.ni_markup
        self.net_profit = self.ni_markup - COSTS_PER_CAR
        self.profit_margin = (self.net_profit / self.price * 100) if self.price > 0 else 0

        self.avg_uk_price = car_config.get('avg_uk_price', 0)
        self.avg_ni_price = car_config.get('avg_ni_price', 0)
        self.uk_saving = self.avg_uk_price - self.price
        self.ni_margin = self.avg_ni_price - self.expected_ni_price

        self.distance = haversine_distance(LIVERPOOL_COORDS, self.coords)

    def is_profitable(self) -> bool:
        """Check if this listing meets profit criteria"""
        car_config = TARGET_CARS.get(self.model_type, {})
        title_lower = self.title.lower()

        # Filter out "WANTED" posts (people looking to buy, not selling)
        wanted_keywords = ['wanted', 'looking for', 'wtb', 'want to buy', 'searching for', 'iso']
        for kw in wanted_keywords:
            if kw in title_lower:
                return False

        # Filter out touring / estate variants
        estate_keywords = ['touring', 'estate', 'tourer', 'avant', 'sportback']
        for kw in estate_keywords:
            if kw in title_lower:
                return False

        # Check exclude keywords (e.g. filter out FN2 from EP3 searches)
        exclude_keywords = car_config.get('exclude_keywords', [])
        if exclude_keywords:
            for kw in exclude_keywords:
                if kw.lower() in title_lower:
                    return False

        # Check year range if specified (e.g. EP3 = 2001-2005 only)
        year_min = car_config.get('year_min')
        year_max = car_config.get('year_max')
        if year_min or year_max:
            try:
                year_val = int(re.search(r'(19|20)\d{2}', str(self.year)).group())
                if year_min and year_val < year_min:
                    return False
                if year_max and year_val > year_max:
                    return False
            except (AttributeError, ValueError, TypeError):
                pass  # If year can't be parsed, allow it through

        return (
            self.price > 0 and
            self.price <= car_config.get('max_price', 999999) and
            self.distance <= MAX_DISTANCE_MILES and
            self.net_profit >= car_config.get('min_profit', 0)
        )

    def to_dict(self) -> dict:
        return {
            'Model Type': self.model_type,
            'Title': self.title,
            'Buy Price': f'£{self.price:,}',
            'Avg UK Price': f'£{self.avg_uk_price:,}',
            'UK Saving': f'£{self.uk_saving:,}',
            'Expected NI Sell': f'£{self.expected_ni_price:,}',
            'Avg NI Price': f'£{self.avg_ni_price:,}',
            'Net Profit': f'£{self.net_profit:,}',
            'Profit Margin': f'{self.profit_margin:.1f}%',
            'Location': self.location,
            'Distance (miles)': f'{self.distance:.1f}',
            'Year': self.year,
            'Mileage': self.mileage,
            'Source': self.source,
            'URL': self.url
        }


class AutoTraderScraper:
    """Scraper for AutoTrader UK - tries multiple data extraction methods.
    Note: AutoTrader uses a fully client-rendered React SPA which limits
    what can be extracted with simple requests. Results may be limited."""

    BASE_URL = "https://www.autotrader.co.uk"

    def search(self, model_type: str, search_term: str) -> List[CarListing]:
        """Search AutoTrader using their structured URL params"""
        listings = []
        config = TARGET_CARS[model_type]

        print(f"  → AutoTrader: {search_term}")

        try:
            params = {
                'postcode': 'L1 1AA',
                'radius': str(min(MAX_DISTANCE_MILES, 200)),
                'make': config.get('make', ''),
                'model': config.get('model', ''),
                'price-to': str(config['max_price']),
                'sort': 'price-asc',
                'include-delivery-option': 'on',
                'page': '1',
            }

            # Add keyword for specific sub-models
            keyword = self._get_keyword(model_type, search_term)
            if keyword:
                params['keyword'] = keyword

            search_url = f"{self.BASE_URL}/car-search?{urlencode(params)}"
            response = requests.get(search_url, headers=HEADERS, timeout=20)
            response.raise_for_status()

            html = response.text

            # Method 1: Extract __NEXT_DATA__ JSON (Next.js embedded data)
            next_data = self._extract_next_data(html)
            if next_data:
                listings = self._parse_next_data(next_data, model_type)
                if listings:
                    print(f"     ✓ Found {len(listings)} from embedded JSON")
                    return listings

            # Method 2: Try _next/data JSON API endpoint
            build_id = self._extract_build_id(html)
            if build_id:
                listings = self._try_next_data_api(build_id, params, model_type)
                if listings:
                    print(f"     ✓ Found {len(listings)} from _next/data API")
                    return listings

            # Method 3: Try to extract from inline JSON/script blocks
            script_listings = self._extract_script_data(html)
            if script_listings:
                listings = self._parse_script_listings(script_listings, model_type)
                if listings:
                    print(f"     ✓ Found {len(listings)} from script data")
                    return listings

            # Method 4: Traditional HTML parsing with multiple selectors
            soup = BeautifulSoup(html, 'html.parser')
            listings = self._parse_html(soup, model_type, search_term)
            if listings:
                print(f"     ✓ Found {len(listings)} from HTML parsing")
                return listings

            # AutoTrader is a client-rendered SPA - data loads via JavaScript
            # Check for skeleton cards (empty placeholders that indicate SPA)
            if 'skeleton-advertCard' in html or ('sauron' in html and len(listings) == 0):
                print(f"     - SPA detected (client-rendered, no server-side data)")
            else:
                print(f"     - No results (page size: {len(html)} bytes)")

        except requests.RequestException as e:
            print(f"     ✗ Request failed: {str(e)[:80]}")
        except Exception as e:
            print(f"     ✗ Error: {str(e)[:80]}")

        return listings

    def _get_keyword(self, model_type, search_term):
        """Get keyword filter for specific sub-models"""
        keywords = {
            'peugeot_306_dturbo': 'turbo',
            'bmw_e46_330': '330',
            'bmw_e60_530d': '530d',
            'bmw_e60_535d': '535d',
            'bmw_f30_330d': '330d',
            'bmw_f30_335d': '335d',
            'honda_civic_ep3_type_r': 'type r',
        }
        return keywords.get(model_type, '')

    def _extract_build_id(self, html):
        """Extract Next.js build ID for _next/data API"""
        try:
            # Try buildId in inline config
            match = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
            if match:
                return match.group(1)
            # Try from _buildManifest URL
            match = re.search(r'/_next/static/([a-zA-Z0-9_-]+)/_buildManifest', html)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None

    def _try_next_data_api(self, build_id, params, model_type):
        """Try fetching data via Next.js _next/data JSON endpoint"""
        listings = []
        try:
            data_url = f"{self.BASE_URL}/_next/data/{build_id}/car-search.json"
            response = requests.get(data_url, params=params, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                data = json.loads(response.text)
                page_props = data.get('pageProps', {})
                # Try to find listings in the response
                search_results = (
                    page_props.get('searchResults', {}).get('results', []) or
                    page_props.get('listings', []) or
                    page_props.get('results', []) or
                    []
                )
                for item in search_results[:15]:
                    try:
                        title = item.get('title', '') or item.get('name', '')
                        price = extract_price(str(item.get('price', '')))
                        if price > 0:
                            location = item.get('location', '') or item.get('sellerLocation', '')
                            if isinstance(location, dict):
                                location = location.get('town', '')
                            url = item.get('url', '')
                            if url and not url.startswith('http'):
                                url = f"{self.BASE_URL}{url}"
                            image = ''
                            img_data = item.get('images', item.get('imageUrls', []))
                            if isinstance(img_data, list) and img_data:
                                first_img = img_data[0]
                                image = first_img if isinstance(first_img, str) else first_img.get('url', '')
                            if not image:
                                image = item.get('imageUrl', item.get('image', ''))
                            listings.append(CarListing({
                                'model_type': model_type,
                                'title': title or 'AutoTrader Listing',
                                'price': price,
                                'location': str(location) or 'Unknown',
                                'coords': geocode_location(str(location)),
                                'url': url,
                                'year': str(item.get('year', 'Unknown')),
                                'mileage': str(item.get('mileage', 'Unknown')),
                                'source': 'AutoTrader',
                                'image': image or ''
                            }))
                    except Exception:
                        continue
        except Exception:
            pass
        return listings

    def _extract_next_data(self, html):
        """Extract __NEXT_DATA__ JSON from the page"""
        try:
            match = re.search(r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>', html, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    def _parse_next_data(self, data, model_type):
        """Parse listings from Next.js data"""
        listings = []
        try:
            # Navigate the Next.js data structure to find listings
            props = data.get('props', {}).get('pageProps', {})

            # Try different possible paths for listing data
            search_results = (
                props.get('searchResults', {}).get('results', []) or
                props.get('listings', []) or
                props.get('results', []) or
                []
            )

            # Also check for ads/adverts key
            if not search_results:
                for key in ['adverts', 'ads', 'vehicles', 'items']:
                    if key in props:
                        search_results = props[key]
                        break

            for item in search_results[:15]:
                try:
                    title = item.get('title', '') or item.get('name', '') or item.get('heading', '')
                    price = extract_price(str(item.get('price', '') or item.get('otrPrice', '')))
                    location = item.get('location', '') or item.get('sellerLocation', '') or item.get('town', '')
                    if isinstance(location, dict):
                        location = location.get('town', '') or location.get('area', '')

                    url = item.get('url', '') or item.get('href', '')
                    if url and not url.startswith('http'):
                        url = f"{self.BASE_URL}{url}"

                    year = str(item.get('year', '') or item.get('registrationYear', ''))
                    mileage = str(item.get('mileage', '') or item.get('odometerReading', ''))

                    # Try to get image
                    image = ''
                    img_data = item.get('images', item.get('imageUrls', item.get('photos', [])))
                    if isinstance(img_data, list) and img_data:
                        first_img = img_data[0]
                        image = first_img if isinstance(first_img, str) else first_img.get('url', first_img.get('src', ''))
                    elif isinstance(img_data, str):
                        image = img_data
                    if not image:
                        image = item.get('imageUrl', item.get('image', item.get('thumbnailUrl', '')))

                    if price > 0:
                        listings.append(CarListing({
                            'model_type': model_type,
                            'title': title or f"AutoTrader Listing",
                            'price': price,
                            'location': str(location) or 'Unknown',
                            'coords': geocode_location(str(location)),
                            'url': url,
                            'year': year or 'Unknown',
                            'mileage': mileage or 'Unknown',
                            'source': 'AutoTrader',
                            'image': image
                        }))
                except Exception:
                    continue
        except Exception as e:
            print(f"     - Next.js parse error: {str(e)[:50]}")

        return listings

    def _extract_script_data(self, html):
        """Extract listing data from inline scripts"""
        patterns = [
            r'window\.__data__\s*=\s*({.*?});',
            r'window\.searchResults\s*=\s*({.*?});',
            r'"searchResults"\s*:\s*(\[.*?\])',
            r'"listings"\s*:\s*(\[.*?\])',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _parse_script_listings(self, data, model_type):
        """Parse listings from script-extracted data"""
        listings = []
        items = data if isinstance(data, list) else data.get('results', data.get('listings', []))
        for item in items[:15]:
            try:
                if isinstance(item, dict):
                    price = extract_price(str(item.get('price', 0)))
                    if price > 0:
                        image = item.get('imageUrl', item.get('image', item.get('thumbnailUrl', '')))
                        listings.append(CarListing({
                            'model_type': model_type,
                            'title': item.get('title', 'AutoTrader Listing'),
                            'price': price,
                            'location': str(item.get('location', 'Unknown')),
                            'coords': geocode_location(str(item.get('location', ''))),
                            'url': item.get('url', ''),
                            'year': str(item.get('year', 'Unknown')),
                            'mileage': str(item.get('mileage', 'Unknown')),
                            'source': 'AutoTrader',
                            'image': image or ''
                        }))
            except Exception:
                continue
        return listings

    def _parse_html(self, soup, model_type, search_term):
        """Traditional HTML parsing as last resort"""
        listings = []

        # Try multiple selector patterns
        selectors = [
            ('article', {'data-testid': re.compile(r'trader-seller-listing')}),
            ('li', {'class': re.compile(r'search-page__result')}),
            ('section', {'class': re.compile(r'product-card')}),
            ('div', {'class': re.compile(r'listing-card')}),
            ('article', {}),
        ]

        for tag, attrs in selectors:
            articles = soup.find_all(tag, attrs)
            if articles:
                for article in articles[:15]:
                    try:
                        title_el = article.find(['h2', 'h3', 'a'])
                        title = title_el.get_text(strip=True) if title_el else search_term

                        price_el = article.find(string=re.compile(r'£[\d,]+'))
                        price = extract_price(price_el) if price_el else 0

                        if price == 0:
                            continue

                        link = article.find('a', href=True)
                        url = ''
                        if link:
                            url = link['href']
                            if not url.startswith('http'):
                                url = f"{self.BASE_URL}{url}"

                        text = article.get_text()
                        year_match = re.search(r'(19|20)\d{2}', text)
                        mileage_match = re.search(r'([\d,]+)\s*miles', text, re.IGNORECASE)

                        # Try to get image from listing
                        image = ''
                        img_el = article.find('img', src=True)
                        if img_el:
                            image = img_el.get('src', '') or img_el.get('data-src', '')

                        listings.append(CarListing({
                            'model_type': model_type,
                            'title': title,
                            'price': price,
                            'location': 'Liverpool area',
                            'coords': LIVERPOOL_COORDS,
                            'url': url,
                            'year': year_match.group() if year_match else 'Unknown',
                            'mileage': mileage_match.group(1) if mileage_match else 'Unknown',
                            'source': 'AutoTrader',
                            'image': image
                        }))
                    except Exception:
                        continue

                if listings:
                    break

        return listings


class GumtreeScraper:
    """Scraper for Gumtree UK"""

    BASE_URL = "https://www.gumtree.com"

    def search(self, model_type: str, search_term: str) -> List[CarListing]:
        """Search Gumtree for cars"""
        listings = []

        print(f"  → Gumtree: {search_term}")

        try:
            # Gumtree URL format for cars
            search_url = f"{self.BASE_URL}/search"
            params = {
                'search_category': 'cars',
                'q': search_term,
                'search_location': 'Liverpool',
                'distance': str(min(MAX_DISTANCE_MILES, 100)),
                'max_price': str(TARGET_CARS[model_type]['max_price']),
                'vehicle_type': 'cars',
            }

            response = requests.get(search_url, params=params, headers=HEADERS, timeout=20, allow_redirects=True)
            response.raise_for_status()

            html = response.text

            # Method 1: Look for embedded JSON data
            json_data = self._extract_json_data(html)
            if json_data:
                listings = self._parse_json_listings(json_data, model_type)
                if listings:
                    print(f"     ✓ Found {len(listings)} from JSON")
                    return listings

            # Method 2: Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            listings = self._parse_html(soup, model_type, search_term)

            print(f"     {'✓ Found ' + str(len(listings)) if listings else '- No results'} (page: {len(html)} bytes)")

        except requests.RequestException as e:
            print(f"     ✗ Request failed: {str(e)[:80]}")
        except Exception as e:
            print(f"     ✗ Error: {str(e)[:80]}")

        return listings

    def _extract_json_data(self, html):
        """Extract embedded JSON listing data"""
        patterns = [
            r'window\.__data__\s*=\s*({.*?});\s*</script>',
            r'"results"\s*:\s*(\[{.*?}\])',
            r'"ads"\s*:\s*(\[{.*?}\])',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _parse_json_listings(self, data, model_type):
        """Parse listings from Gumtree JSON data"""
        listings = []
        items = data if isinstance(data, list) else data.get('results', data.get('ads', []))
        for item in items[:15]:
            try:
                price = extract_price(str(item.get('price', 0)))
                if price > 0:
                    location = item.get('location', 'Liverpool')
                    if isinstance(location, dict):
                        location = location.get('name', 'Liverpool')
                    image = item.get('imageUrl', item.get('image', item.get('thumbnailUrl', '')))
                    img_list = item.get('images', item.get('imageUrls', []))
                    if not image and isinstance(img_list, list) and img_list:
                        first = img_list[0]
                        image = first if isinstance(first, str) else first.get('url', first.get('src', ''))
                    listings.append(CarListing({
                        'model_type': model_type,
                        'title': item.get('title', 'Gumtree Listing'),
                        'price': price,
                        'location': str(location),
                        'coords': geocode_location(str(location)),
                        'url': item.get('url', ''),
                        'year': str(item.get('year', 'Unknown')),
                        'mileage': str(item.get('mileage', 'Unknown')),
                        'source': 'Gumtree',
                        'image': image or ''
                    }))
            except Exception:
                continue
        return listings

    def _parse_html(self, soup, model_type, search_term):
        """Parse Gumtree HTML results"""
        listings = []

        # Try multiple selectors
        selectors = [
            ('article', {'class': re.compile(r'listing')}),
            ('li', {'class': re.compile(r'natural')}),
            ('div', {'class': re.compile(r'listing-card')}),
            ('div', {'data-q': re.compile(r'search-result')}),
        ]

        for tag, attrs in selectors:
            elements = soup.find_all(tag, attrs)
            if elements:
                for el in elements[:15]:
                    try:
                        title_el = el.find(['h2', 'h3', 'a'])
                        title = title_el.get_text(strip=True) if title_el else search_term

                        price_text = el.find(string=re.compile(r'£[\d,]+'))
                        price = extract_price(price_text) if price_text else 0
                        if price == 0:
                            continue

                        link = el.find('a', href=True)
                        url = ''
                        if link:
                            url = link['href']
                            if not url.startswith('http'):
                                url = f"{self.BASE_URL}{url}"

                        text = el.get_text()
                        year_match = re.search(r'(19|20)\d{2}', text)
                        mileage_match = re.search(r'([\d,]+)\s*(miles|mi)', text, re.IGNORECASE)

                        image = ''
                        img_el = el.find('img')
                        if img_el:
                            image = img_el.get('src', '') or img_el.get('data-src', '') or img_el.get('data-lazy-src', '')
                            # Skip placeholder/tracking pixels
                            if image and ('pixel' in image or 'spacer' in image or '1x1' in image or image.startswith('data:')):
                                image = ''
                            # Try srcset as fallback
                            if not image:
                                srcset = img_el.get('srcset', '')
                                if srcset:
                                    image = srcset.split(',')[0].strip().split(' ')[0]

                        listings.append(CarListing({
                            'model_type': model_type,
                            'title': title,
                            'price': price,
                            'location': 'Liverpool area',
                            'coords': LIVERPOOL_COORDS,
                            'url': url,
                            'year': year_match.group() if year_match else 'Unknown',
                            'mileage': mileage_match.group(1) if mileage_match else 'Unknown',
                            'source': 'Gumtree',
                            'image': image
                        }))
                    except Exception:
                        continue
                if listings:
                    break

        return listings


class PistonHeadsScraper:
    """Scraper for PistonHeads classifieds - browses /buy/{make} to get Apollo state adverts"""

    BASE_URL = "https://www.pistonheads.com"

    # Map our make names to PistonHeads URL slugs
    MAKE_SLUGS = {
        'Peugeot': 'peugeot',
        'Lexus': 'lexus',
        'BMW': 'bmw',
        'Honda': 'honda',
    }

    def search(self, model_type: str, search_term: str) -> List[CarListing]:
        """Search PistonHeads by browsing /buy/{make} and filtering Apollo state adverts"""
        listings = []
        config = TARGET_CARS[model_type]

        print(f"  → PistonHeads: {search_term}")

        try:
            make = config.get('make', '')
            make_slug = self.MAKE_SLUGS.get(make, make.lower())

            # Browse the make-specific page to get real adverts in Apollo state
            search_url = f"{self.BASE_URL}/buy/{make_slug}"
            response = requests.get(search_url, headers=HEADERS, timeout=20, allow_redirects=True)
            response.raise_for_status()

            html = response.text

            # Method 1: Extract Apollo state from __NEXT_DATA__
            apollo_state = self._extract_apollo_state(html)
            if apollo_state:
                listings = self._parse_apollo_adverts(apollo_state, model_type, config)
                if listings:
                    print(f"     ✓ Found {len(listings)} from Apollo state")
                    return listings

            # Method 2: Parse server-rendered MUI Card HTML
            soup = BeautifulSoup(html, 'html.parser')
            listings = self._parse_mui_cards(soup, model_type, search_term, config)
            if listings:
                print(f"     ✓ Found {len(listings)} from HTML")
                return listings

            print(f"     - No matching results (page: {len(html)} bytes)")

        except requests.RequestException as e:
            print(f"     ✗ Request failed: {str(e)[:80]}")
        except Exception as e:
            print(f"     ✗ Error: {str(e)[:80]}")

        return listings

    def _extract_apollo_state(self, html):
        """Extract Apollo state containing Advert entries from __NEXT_DATA__"""
        try:
            match = re.search(r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>', html, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                apollo = data.get('props', {}).get('pageProps', {}).get('__APOLLO_STATE__', {})
                if apollo:
                    return apollo
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    def _parse_apollo_adverts(self, apollo_state, model_type, config):
        """Parse listings from PistonHeads Apollo state (Advert:XXXXX entries).
        Filters adverts by model name and price range since Apollo state
        contains all featured adverts for the make, not just our target model."""
        listings = []

        # Build model matching keywords
        model_name = config.get('model', '').lower()
        # Additional keywords to match the right model
        model_keywords = {
            'peugeot_306_dturbo': ['306'],
            'lexus_is200': ['is200', 'is 200', 'is-200'],
            'bmw_e46_330': ['330i', '330ci', '330'],
            'honda_civic_ep3_type_r': ['civic', 'type r', 'type-r'],
            'bmw_e60_530d': ['530d', '530'],
            'bmw_e60_535d': ['535d', '535'],
            'bmw_f30_330d': ['330d'],
            'bmw_f30_335d': ['335d'],
        }
        keywords = model_keywords.get(model_type, [model_name])
        max_price = config.get('max_price', 999999)

        for key, item in apollo_state.items():
            if not key.startswith('Advert:') and not key.startswith('FeaturedAdvert:'):
                continue

            try:
                price = int(item.get('price', 0))
                if price <= 0 or price > max_price:
                    continue

                headline = item.get('headline', 'PistonHeads Listing')
                headline_lower = headline.lower()

                # Check if this advert matches our target model
                model_analytics = (item.get('modelAnalyticsName', '') or '').lower()
                combined_text = f"{headline_lower} {model_analytics}"

                if not any(kw in combined_text for kw in keywords):
                    continue

                year = str(item.get('year', 'Unknown'))
                advert_id = item.get('id', '')

                # Extract image from fullSizeImageUrls
                image = ''
                img_urls = item.get('fullSizeImageUrls', [])
                if isinstance(img_urls, list) and img_urls:
                    image = img_urls[0] if isinstance(img_urls[0], str) else ''

                # Extract mileage from specificationData
                spec = item.get('specificationData', {})
                mileage = 'Unknown'
                if isinstance(spec, dict):
                    mileage = str(spec.get('mileage', 'Unknown'))

                # Try to get seller location
                location = 'Unknown'
                seller_ref = item.get('seller', {})
                if isinstance(seller_ref, dict):
                    seller_key = seller_ref.get('__ref', '')
                    if seller_key and seller_key in apollo_state:
                        seller = apollo_state[seller_key]
                        location = seller.get('location', seller.get('town', 'Unknown'))
                        if isinstance(location, dict):
                            location = location.get('town', location.get('name', 'Unknown'))

                url = f"{self.BASE_URL}/buy/listing/{advert_id}" if advert_id else ''

                listings.append(CarListing({
                    'model_type': model_type,
                    'title': headline,
                    'price': price,
                    'location': str(location),
                    'coords': geocode_location(str(location)),
                    'url': url,
                    'year': year,
                    'mileage': mileage,
                    'source': 'PistonHeads',
                    'image': image
                }))
            except Exception:
                continue

        return listings

    def _parse_mui_cards(self, soup, model_type, search_term, config):
        """Parse PistonHeads server-rendered MUI Card components.
        Filters cards by model-specific keywords since the page shows all make's listings."""
        listings = []

        # Build model matching keywords (same as Apollo parser)
        model_keywords = {
            'peugeot_306_dturbo': ['306'],
            'lexus_is200': ['is200', 'is 200', 'is-200'],
            'bmw_e46_330': ['330i', '330ci', '330 ', 'e46'],
            'honda_civic_ep3_type_r': ['civic', 'type r', 'type-r'],
            'bmw_e60_530d': ['530d', '530 '],
            'bmw_e60_535d': ['535d', '535 '],
            'bmw_f30_330d': ['330d'],
            'bmw_f30_335d': ['335d'],
        }
        keywords = model_keywords.get(model_type, [config.get('model', '').lower()])
        max_price = config.get('max_price', 999999)

        # PistonHeads uses Material-UI cards - find only top-level cards
        cards = soup.find_all('div', class_=re.compile(r'CardOfSearchResult_card__'))
        if not cards:
            cards = soup.find_all('div', class_=re.compile(r'MuiCard-root'))

        seen = set()  # Deduplicate

        for card in cards[:40]:
            try:
                text = card.get_text(separator=' ')
                text_lower = text.lower()

                # Extract price
                price_match = re.search(r'£([\d,]+)', text)
                if not price_match:
                    continue
                price = extract_price(price_match.group())
                if price <= 0 or price > max_price:
                    continue

                # Filter: must match target model keywords
                if not any(kw in text_lower for kw in keywords):
                    continue

                # Deduplicate by price + first chars of text
                card_key = f"{price}_{text_lower[:80]}"
                if card_key in seen:
                    continue
                seen.add(card_key)

                # Extract title from the card text
                # PistonHeads format: "Sponsored £XX,XXX Title 2022 BodyType NNN miles"
                # Remove price, then take text before year/body type
                clean_text = re.sub(r'(?:Navigate\s+\w+|Sponsored|Featured)\s*', '', text).strip()
                clean_text = re.sub(r'£[\d,]+\s*', '', clean_text).strip()
                # Take first substantial chunk as title
                title_match = re.match(r'(.{10,80}?)(?:\d{4}\s*[A-Z])', clean_text)
                title = title_match.group(1).strip() if title_match else clean_text[:80].strip()
                if not title or len(title) < 5:
                    title = search_term

                # Extract year
                year_match = re.search(r'(19|20)\d{2}', text)
                year = year_match.group() if year_match else 'Unknown'

                # Extract mileage
                mileage_match = re.search(r'([\d,]+)\s*mil', text, re.IGNORECASE)
                mileage = mileage_match.group(1) if mileage_match else 'Unknown'

                # Extract link
                url = ''
                link = card.find('a', href=True)
                if link:
                    url = link['href']
                    if not url.startswith('http'):
                        url = f"{self.BASE_URL}{url}"

                # Extract image (skip SVG placeholders)
                image = ''
                img_el = card.find('img')
                if img_el:
                    src = img_el.get('src', '') or img_el.get('data-src', '')
                    if src and not src.startswith('data:'):
                        image = src

                listings.append(CarListing({
                    'model_type': model_type,
                    'title': title,
                    'price': price,
                    'location': 'Unknown',
                    'coords': LIVERPOOL_COORDS,
                    'url': url,
                    'year': year,
                    'mileage': mileage,
                    'source': 'PistonHeads',
                    'image': image
                }))
            except Exception:
                continue

        return listings


class CarArbitrageFinder:
    """Main orchestrator for finding car arbitrage opportunities"""

    def __init__(self, progress_callback=None):
        self.scrapers = [
            AutoTraderScraper(),
            GumtreeScraper(),
            PistonHeadsScraper()
        ]
        self.all_listings = []
        self.profitable_deals = []
        self.progress_callback = progress_callback

    def _log(self, message):
        """Log message to callback and stdout"""
        if self.progress_callback:
            self.progress_callback(message)
        print(message)

    def search_all(self):
        """Search all sources for all target cars"""
        print("\n" + "="*60)
        print("  CAR ARBITRAGE FINDER - Liverpool → Northern Ireland")
        print("="*60 + "\n")

        total_searches = len(TARGET_CARS) * len(self.scrapers)
        completed = 0

        self._log(f"🚀 Starting scraper - {len(TARGET_CARS)} car models, {total_searches} searches")

        for model_type, config in TARGET_CARS.items():
            model_name = model_type.replace('_', ' ').title()
            self._log(f"🔍 Searching for {model_name} (max £{config['max_price']:,})")

            search_term = config['search_terms'][0]

            for scraper in self.scrapers:
                try:
                    scraper_name = scraper.__class__.__name__.replace('Scraper', '')

                    self._log(f"📡 {scraper_name}: Searching '{search_term}'...")

                    listings = scraper.search(model_type, search_term)

                    # For Gumtree (our most reliable source), try a 2nd search term
                    # if the first returned few results, to maximize coverage
                    if isinstance(scraper, GumtreeScraper) and len(listings) < 5 and len(config['search_terms']) > 1:
                        time.sleep(random.uniform(1.0, 2.0))
                        alt_term = config['search_terms'][1]
                        self._log(f"📡 {scraper_name}: Trying alternate term '{alt_term}'...")
                        alt_listings = scraper.search(model_type, alt_term)
                        # Add only new listings (avoid dups by URL)
                        existing_urls = {l.url for l in listings if l.url}
                        for l in alt_listings:
                            if not l.url or l.url not in existing_urls:
                                listings.append(l)
                                existing_urls.add(l.url)

                    self.all_listings.extend(listings)

                    profitable = [l for l in listings if l.is_profitable()]
                    self.profitable_deals.extend(profitable)

                    completed += 1
                    progress_pct = int((completed / total_searches) * 100)

                    if profitable:
                        self._log(f"✅ {scraper_name}: Found {len(profitable)} deals! ({progress_pct}% complete)")
                    elif listings:
                        self._log(f"📋 {scraper_name}: {len(listings)} listings, none profitable ({progress_pct}% complete)")
                    else:
                        self._log(f"   {scraper_name}: No results ({progress_pct}% complete)")

                    # Shorter delay - 1 to 2 seconds between requests
                    time.sleep(random.uniform(1.0, 2.0))

                except Exception as e:
                    completed += 1
                    progress_pct = int((completed / total_searches) * 100)
                    self._log(f"⚠️ {scraper.__class__.__name__}: Error - {str(e)[:60]} ({progress_pct}% complete)")

        # Remove duplicates based on URL
        seen_urls = set()
        unique_deals = []
        for deal in self.profitable_deals:
            if deal.url and deal.url not in seen_urls:
                seen_urls.add(deal.url)
                unique_deals.append(deal)
            elif not deal.url:
                unique_deals.append(deal)

        self.profitable_deals = unique_deals

        self._log(f"🏁 Complete! {len(self.all_listings)} total listings, {len(self.profitable_deals)} profitable deals")

    def export_csv(self, filename: str):
        """Export results to CSV"""
        if not self.profitable_deals:
            print("\n⚠️  No profitable deals found to export")
            return

        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(self.profitable_deals[0].to_dict().keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for deal in sorted(self.profitable_deals, key=lambda x: x.net_profit, reverse=True):
                writer.writerow(deal.to_dict())

        print(f"\n✓ CSV exported: {filename}")

    def export_html(self, filename: str):
        """Export results to HTML report"""
        if not self.profitable_deals:
            return

        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        sorted_deals = sorted(self.profitable_deals, key=lambda x: x.net_profit, reverse=True)
        total_profit = sum(d.net_profit for d in sorted_deals)
        avg_profit = total_profit / len(sorted_deals)
        best_margin = max(d.profit_margin for d in sorted_deals)

        # Build list of unique model types for filter dropdown
        model_labels = {
            'peugeot_306_dturbo': 'Peugeot 306 D-Turbo',
            'lexus_is200': 'Lexus IS200',
            'bmw_e46_330': 'BMW E46 330i/ci',
            'honda_civic_ep3_type_r': 'Honda Civic EP3 Type R',
            'bmw_e60_530d': 'BMW E60 530d',
            'bmw_e60_535d': 'BMW E60 535d',
            'bmw_f30_330d': 'BMW F30 330d',
            'bmw_f30_335d': 'BMW F30 335d',
        }

        car_data_json = []
        unique_models = set()
        unique_sources = set()
        for deal in sorted_deals:
            unique_models.add(deal.model_type)
            unique_sources.add(deal.source)
            car_data_json.append({
                'model': deal.model_type,
                'title': deal.title,
                'price': f'£{deal.price:,}',
                'ni_price': f'£{deal.expected_ni_price:,}',
                'profit': f'£{deal.net_profit:,}',
                'margin': f'{deal.profit_margin:.1f}%',
                'location': deal.location,
                'distance': f'{deal.distance:.1f}',
                'year': deal.year,
                'mileage': deal.mileage,
                'source': deal.source,
                'url': deal.url
            })

        # Build dropdown options
        model_options = ''.join(
            f'<option value="{m}">{model_labels.get(m, m)}</option>'
            for m in sorted(unique_models)
        )
        source_options = ''.join(
            f'<option value="{s}">{s}</option>'
            for s in sorted(unique_sources)
        )

        html_content = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Car Arbitrage Report</title>
<style>
body{{font-family:sans-serif;background:#0a0e27;color:#e0e0e0;padding:20px;}}
h1{{color:#00ff88;text-align:center;}}
.filters{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:20px 0;}}
.filters select{{background:#1a1f3a;color:#e0e0e0;border:1px solid #00ff88;padding:10px 16px;border-radius:6px;font-size:14px;cursor:pointer;min-width:200px;}}
.filters select:hover{{border-color:#00ffaa;}}
.filter-label{{color:#888;font-size:12px;text-align:center;margin-bottom:4px;}}
.stats{{text-align:center;color:#888;margin:10px 0;}}
.stats span{{color:#00ff88;font-weight:bold;}}
table{{width:100%;border-collapse:collapse;margin-top:20px;}}
th{{background:#00ff88;color:#0a0e27;padding:12px;text-align:left;cursor:pointer;user-select:none;}}
th:hover{{background:#00ddaa;}}
td{{padding:10px;border-bottom:1px solid #2a2f4a;}}
tr:hover{{background:#252a45;}}
tr.hidden{{display:none;}}
.profit{{color:#00ff88;font-weight:bold;}}
a{{color:#6666ff;}}
</style></head>
<body>
<h1>Car Arbitrage Report - {datetime.now().strftime("%Y-%m-%d %H:%M")}</h1>
<p class="stats">{len(sorted_deals)} deals | £{total_profit:,} total profit | £{avg_profit:,.0f} avg</p>

<div class="filters">
  <div>
    <div class="filter-label">Filter by Model</div>
    <select id="modelFilter" onchange="applyFilters()">
      <option value="all">All Models</option>
      {model_options}
    </select>
  </div>
  <div>
    <div class="filter-label">Filter by Source</div>
    <select id="sourceFilter" onchange="applyFilters()">
      <option value="all">All Sources</option>
      {source_options}
    </select>
  </div>
</div>
<p class="stats" id="filteredStats"></p>

<table>
<thead><tr><th>Car</th><th>Year</th><th>Price</th><th>NI Price</th><th>Profit</th><th>Margin</th><th>Location</th><th>Source</th><th>Link</th></tr></thead>
<tbody id="dealRows">'''

        for deal in car_data_json:
            html_content += (
                f'<tr data-model="{deal["model"]}" data-source="{deal["source"]}">'
                f'<td>{deal["title"]}</td>'
                f'<td>{deal["year"]}</td>'
                f'<td>{deal["price"]}</td>'
                f'<td>{deal["ni_price"]}</td>'
                f'<td class="profit">{deal["profit"]}</td>'
                f'<td>{deal["margin"]}</td>'
                f'<td>{deal["location"]}</td>'
                f'<td>{deal["source"]}</td>'
                f'<td><a href="{deal["url"]}" target="_blank">View</a></td>'
                f'</tr>'
            )

        html_content += '''</tbody></table>
<script>
function applyFilters() {
  var model = document.getElementById('modelFilter').value;
  var source = document.getElementById('sourceFilter').value;
  var rows = document.querySelectorAll('#dealRows tr');
  var shown = 0;
  rows.forEach(function(row) {
    var matchModel = (model === 'all' || row.getAttribute('data-model') === model);
    var matchSource = (source === 'all' || row.getAttribute('data-source') === source);
    if (matchModel && matchSource) {
      row.classList.remove('hidden');
      shown++;
    } else {
      row.classList.add('hidden');
    }
  });
  document.getElementById('filteredStats').textContent = 'Showing ' + shown + ' of ' + rows.length + ' deals';
}
applyFilters();
</script>
</body></html>'''

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n✓ HTML report exported: {filename}")

    def print_summary(self):
        """Print summary of findings"""
        print("\n" + "="*60)
        print("  SUMMARY")
        print("="*60)

        if not self.profitable_deals:
            print("\n⚠️  No profitable deals found matching criteria")
            return

        total_potential_profit = sum(d.net_profit for d in self.profitable_deals)
        avg_profit = total_potential_profit / len(self.profitable_deals)
        best_deal = max(self.profitable_deals, key=lambda x: x.net_profit)

        print(f"\n📊 Deals found: {len(self.profitable_deals)}")
        print(f"💰 Total potential profit: £{total_potential_profit:,}")
        print(f"📈 Average profit per car: £{avg_profit:,.0f}")
        print(f"🏆 Best deal: £{best_deal.net_profit:,} ({best_deal.title})")


def create_sample_data():
    """Create sample data for demonstration"""
    samples = [
        {
            'model_type': 'peugeot_306_dturbo',
            'title': 'Peugeot 306 D-Turbo - 3 Door - Full Service History',
            'price': 3800, 'location': 'Manchester',
            'coords': (53.4808, -2.2426),
            'url': 'https://www.gumtree.com/p/cars/peugeot-306-d-turbo/1234567890',
            'year': '1999', 'mileage': '145,000', 'source': 'Gumtree'
        },
        {
            'model_type': 'peugeot_306_dturbo',
            'title': 'Peugeot 306 DTurbo 3dr - Clean Example',
            'price': 4200, 'location': 'Leeds',
            'coords': (53.8008, -1.5491),
            'url': 'https://www.autotrader.co.uk/car-details/202602150001',
            'year': '2000', 'mileage': '128,000', 'source': 'AutoTrader'
        },
        {
            'model_type': 'lexus_is200',
            'title': 'Lexus IS200 Sport Manual - Excellent Condition',
            'price': 3200, 'location': 'Chester',
            'coords': (53.1908, -2.8908),
            'url': 'https://www.autotrader.co.uk/car-details/202602150002',
            'year': '2003', 'mileage': '112,000', 'source': 'AutoTrader'
        },
        {
            'model_type': 'lexus_is200',
            'title': 'Lexus IS-200 SE Manual 6 Speed - FSH',
            'price': 2900, 'location': 'Birmingham',
            'coords': (52.4862, -1.8904),
            'url': 'https://www.gumtree.com/p/cars/lexus-is200-manual/1234567891',
            'year': '2002', 'mileage': '135,000', 'source': 'Gumtree'
        },
        {
            'model_type': 'bmw_e46_330',
            'title': 'BMW E46 330i M Sport Manual - Full History',
            'price': 4500, 'location': 'Preston',
            'coords': (53.7632, -2.7031),
            'url': 'https://www.autotrader.co.uk/car-details/202602150003',
            'year': '2004', 'mileage': '95,000', 'source': 'AutoTrader'
        },
        {
            'model_type': 'bmw_e46_330',
            'title': 'BMW 330ci E46 Coupe Manual - Excellent',
            'price': 3800, 'location': 'Sheffield',
            'coords': (53.3811, -1.4701),
            'url': 'https://www.pistonheads.com/classifieds/used-cars/bmw/e46/12345678',
            'year': '2003', 'mileage': '118,000', 'source': 'PistonHeads'
        },
        {
            'model_type': 'honda_civic_ep3_type_r',
            'title': 'Honda Civic Type R EP3 - Championship White - FSH',
            'price': 7200, 'location': 'Bolton',
            'coords': (53.5768, -2.4282),
            'url': 'https://www.autotrader.co.uk/car-details/202602150004',
            'year': '2005', 'mileage': '82,000', 'source': 'AutoTrader'
        },
        {
            'model_type': 'honda_civic_ep3_type_r',
            'title': 'Honda Civic EP3 Type-R - Recaro Seats - HPI Clear',
            'price': 6500, 'location': 'Warrington',
            'coords': (53.3900, -2.5970),
            'url': 'https://www.pistonheads.com/classifieds/used-cars/honda/civic/12345679',
            'year': '2004', 'mileage': '98,000', 'source': 'PistonHeads'
        },
        {
            'model_type': 'bmw_e60_530d',
            'title': 'BMW 530d E60 M Sport Auto - Full BMW History',
            'price': 3500, 'location': 'Liverpool',
            'coords': (53.4084, -2.9916),
            'url': 'https://www.autotrader.co.uk/car-details/202602150006',
            'year': '2007', 'mileage': '142,000', 'source': 'AutoTrader'
        },
        {
            'model_type': 'bmw_f30_330d',
            'title': 'BMW 330d F30 M Sport - Pro Nav - Leather',
            'price': 9800, 'location': 'Manchester',
            'coords': (53.4808, -2.2426),
            'url': 'https://www.autotrader.co.uk/car-details/202602150007',
            'year': '2015', 'mileage': '87,000', 'source': 'AutoTrader'
        },
    ]

    return [CarListing(s) for s in samples]


def main():
    parser = argparse.ArgumentParser(description='Car Arbitrage Finder - Liverpool to NI')
    parser.add_argument('--demo', action='store_true', help='Run with sample data')
    parser.add_argument('--output', default=None, help='Output base filename')

    args = parser.parse_args()

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = args.output if args.output else f'{OUTPUT_DIR}/deals_{timestamp}'

    finder = CarArbitrageFinder()

    if args.demo:
        print("\n🎬 Running in DEMO mode with sample data\n")
        finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
    else:
        finder.search_all()

    finder.print_summary()

    if finder.profitable_deals:
        csv_file = f"{base_filename}.csv"
        html_file = f"{base_filename}.html"
        finder.export_csv(csv_file)
        finder.export_html(html_file)
        print(f"\n📊 Exported: {csv_file}, {html_file}")


if __name__ == "__main__":
    main()
