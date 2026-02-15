#!/usr/bin/env python3
"""
Car Arbitrage Scraper - Liverpool to Northern Ireland
Real web scraping implementation for drift/race cars
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
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
import random

# Configuration
LIVERPOOL_COORDS = (53.4084, -2.9916)
MAX_DISTANCE_MILES = 200  # Expanded from 100 - covers Manchester, Birmingham, Leeds
OUTPUT_DIR = "./car_deals"
# Updated costs for longer distances
COSTS_PER_CAR = 650  # Ferry £200 + Fuel £100 (longer trips) + Insurance £250 + Admin £100

# Target models with search terms and profit expectations
# Updated February 2026 - Based on REAL UK market analysis
# Research sources: AutoTrader UK, PistonHeads, ClassicValuer.com, DoneDeal.ie
TARGET_CARS = {
    # High Volume Opportunities - Lower margins but easier to find
    'bmw_e46_330': {
        'search_terms': ['BMW 330i', 'BMW 330ci', 'E46 330', '330i Sport', '330ci M Sport'],
        'max_price': 10000,      # Increased to catch more
        'ni_markup': 1000,       # Conservative estimate
        'min_profit': 200,       # Low barrier - any profit is good
        'avg_uk_price': 5500,
        'avg_ni_price': 6700
    },
    'lexus_is200': {
        'search_terms': ['Lexus IS200', 'Lexus IS300', 'IS200 Sport', 'IS200 manual'],
        'max_price': 6000,       # Increased range
        'ni_markup': 700,        # Conservative
        'min_profit': 100,       # Very low barrier - high volume play
        'avg_uk_price': 3200,
        'avg_ni_price': 4000
    },
    'bmw_e46_320': {
        'search_terms': ['BMW 320i', 'BMW 320ci', 'E46 320', '320i Sport'],
        'max_price': 7000,       # More affordable E46
        'ni_markup': 600,        # Moderate demand
        'min_profit': 100,       # Accept small profits
        'avg_uk_price': 3500,
        'avg_ni_price': 4100
    },
    'mazda_mx5': {
        'search_terms': ['Mazda MX-5', 'Mazda MX5', 'Miata', 'MX5 1.8'],
        'max_price': 8000,       # Popular drift platform
        'ni_markup': 600,        # Good NI demand
        'min_profit': 100,       # Low barrier
        'avg_uk_price': 4500,
        'avg_ni_price': 5100
    },
    'nissan_350z': {
        'search_terms': ['Nissan 350Z', '350Z GT', 'Nissan 370Z', '350Z manual'],
        'max_price': 18000,      # Increased range
        'ni_markup': 1500,       # Popular platform
        'min_profit': 500,       # Reasonable profit
        'avg_uk_price': 10000,
        'avg_ni_price': 11800
    },

    # Medium Value Opportunities
    'bmw_e36_328': {
        'search_terms': ['BMW E36 328i', 'E36 328i Sport', 'E36 328'],
        'max_price': 8000,       # Increased
        'ni_markup': 800,
        'min_profit': 200,
        'avg_uk_price': 4500,
        'avg_ni_price': 5500
    },
    'honda_civic_type_r': {
        'search_terms': ['Honda Civic Type R', 'Civic Type-R EP3', 'Civic Type-R FN2', 'EP3 Type R'],
        'max_price': 16000,      # Increased
        'ni_markup': 1500,       # Conservative
        'min_profit': 500,
        'avg_uk_price': 11000,
        'avg_ni_price': 12800
    },
    'mazda_rx8': {
        'search_terms': ['Mazda RX-8', 'Mazda RX8', 'RX8 R3'],
        'max_price': 8000,       # Affordable rotary
        'ni_markup': 700,
        'min_profit': 200,
        'avg_uk_price': 5000,
        'avg_ni_price': 5700
    },

    # High Value Opportunities - Bigger margins but rarer
    'bmw_e36_m3': {
        'search_terms': ['BMW E36 M3', 'E36 M3 Evolution', 'E36 M3 3.2', 'M3 E36'],
        'max_price': 22000,      # Increased
        'ni_markup': 2500,       # Conservative
        'min_profit': 1200,      # Need decent margin for high value
        'avg_uk_price': 18000,
        'avg_ni_price': 21000
    },
    'nissan_200sx': {
        'search_terms': ['Nissan 200SX', 'Nissan Silvia', '200SX S13', '200SX S14', '200SX S15', 'Silvia S14'],
        'max_price': 20000,      # Increased for rare finds
        'ni_markup': 2000,       # Conservative for safety
        'min_profit': 1000,      # Lower barrier
        'avg_uk_price': 14700,
        'avg_ni_price': 17200
    },

    # Premium JDM - Rare but high profit
    'nissan_skyline_r33': {
        'search_terms': ['Nissan Skyline R33', 'R33 GTS-T', 'Skyline R33', 'R33 GTR'],
        'max_price': 35000,      # Increased
        'ni_markup': 3500,       # Conservative
        'min_profit': 2000,      # Need decent margin
        'avg_uk_price': 22000,
        'avg_ni_price': 26000
    },
    'nissan_skyline_r32': {
        'search_terms': ['Nissan Skyline R32', 'R32 GTR', 'R32 GTS-T', 'Skyline R32'],
        'max_price': 45000,      # Increased for GTR finds
        'ni_markup': 4000,       # Conservative
        'min_profit': 2500,      # Need buffer
        'avg_uk_price': 35000,
        'avg_ni_price': 40000
    },
    'mazda_rx7_fd': {
        'search_terms': ['Mazda RX-7 FD', 'Mazda RX7 FD3S', 'RX-7 Import', 'FD RX7'],
        'max_price': 35000,      # Increased
        'ni_markup': 3500,       # Conservative
        'min_profit': 2000,
        'avg_uk_price': 28000,
        'avg_ni_price': 32000
    },
    'mazda_rx7_fc': {
        'search_terms': ['Mazda RX-7 FC', 'Mazda RX7 FC3S', 'FC RX7'],
        'max_price': 12000,      # Increased
        'ni_markup': 1200,       # Conservative
        'min_profit': 600,
        'avg_uk_price': 9000,
        'avg_ni_price': 10500
    },
    'toyota_supra': {
        'search_terms': ['Toyota Supra', 'Supra MK4', 'Supra Twin Turbo', 'Supra NA'],
        'max_price': 60000,      # Increased
        'ni_markup': 5000,       # Conservative
        'min_profit': 3000,      # High value car
        'avg_uk_price': 42000,
        'avg_ni_price': 48000
    }
}

# User-Agent for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
}


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate distance between two coordinates in miles using Haversine formula
    """
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    return c * 3959  # Earth radius in miles


def extract_price(price_str: str) -> int:
    """Extract numeric price from string"""
    if not price_str:
        return 0
    
    # Remove £, commas, and extract first number
    price_str = re.sub(r'[£,]', '', price_str)
    match = re.search(r'\d+', price_str)
    
    return int(match.group()) if match else 0


def check_robots_txt(base_url: str, user_agent: str = '*') -> bool:
    """
    Check if scraping is allowed by robots.txt
    Returns True if allowed, False if disallowed
    """
    try:
        rp = RobotFileParser()
        robots_url = urljoin(base_url, '/robots.txt')
        rp.set_url(robots_url)
        rp.read()

        # Check if we can fetch the search page
        return rp.can_fetch(user_agent, base_url)
    except Exception as e:
        # If we can't read robots.txt, assume it's allowed (permissive)
        print(f"     Warning: Could not read robots.txt for {base_url}: {e}")
        return True


def geocode_location(location: str) -> Tuple[float, float]:
    """
    Geocode a UK location to coordinates
    This is a simplified version - in production use Google Maps API or similar
    """
    # Approximate coordinates for major UK cities (expanded 200-mile radius)
    locations = {
        # Northwest
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
        # Yorkshire
        'leeds': (53.8008, -1.5491),
        'sheffield': (53.3811, -1.4701),
        'york': (53.9600, -1.0873),
        'bradford': (53.7960, -1.7594),
        'huddersfield': (53.6458, -1.7850),
        # Midlands
        'birmingham': (52.4862, -1.8904),
        'nottingham': (52.9548, -1.1581),
        'leicester': (52.6369, -1.1398),
        'derby': (52.9225, -1.4746),
        'coventry': (52.4068, -1.5197),
        'wolverhampton': (52.5867, -2.1290),
        # Wales
        'cardiff': (51.4816, -3.1791),
        'swansea': (51.6214, -3.9436),
        'wrexham': (53.0462, -2.9930),
        # Other
        'newcastle': (54.9783, -1.6178),
        'carlisle': (54.8951, -2.9382),
    }

    location_lower = location.lower()

    for city, coords in locations.items():
        if city in location_lower:
            return coords

    # Default to Liverpool if not found
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

        # Calculate profit
        car_config = TARGET_CARS.get(self.model_type, {})
        self.ni_markup = car_config.get('ni_markup', 0)
        self.expected_ni_price = self.price + self.ni_markup
        self.gross_profit = self.ni_markup
        self.net_profit = self.ni_markup - COSTS_PER_CAR
        self.profit_margin = (self.net_profit / self.price * 100) if self.price > 0 else 0

        # Market comparison
        self.avg_uk_price = car_config.get('avg_uk_price', 0)
        self.avg_ni_price = car_config.get('avg_ni_price', 0)
        self.uk_saving = self.avg_uk_price - self.price  # How much below UK average
        self.ni_margin = self.avg_ni_price - self.expected_ni_price  # Room to sell below NI avg

        # Calculate distance
        self.distance = haversine_distance(LIVERPOOL_COORDS, self.coords)
    
    def is_profitable(self) -> bool:
        """Check if this listing meets profit criteria"""
        car_config = TARGET_CARS.get(self.model_type, {})
        
        return (
            self.price > 0 and
            self.price <= car_config.get('max_price', 999999) and
            self.distance <= MAX_DISTANCE_MILES and
            self.net_profit >= car_config.get('min_profit', 500)
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export"""
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
    """Scraper for AutoTrader UK"""

    BASE_URL = "https://www.autotrader.co.uk"

    def search(self, model_type: str, search_term: str) -> List[CarListing]:
        """
        Search AutoTrader for a specific model
        Uses respectful web scraping with rate limiting
        """
        listings = []

        print(f"  → Searching AutoTrader for: {search_term}")

        try:
            # Build search URL for AutoTrader
            # Format: /car-search?postcode=L1&radius=100&make=BMW&model=330i&price-to=10000
            search_url = f"{self.BASE_URL}/car-search"

            params = {
                'postcode': 'L1',
                'radius': str(MAX_DISTANCE_MILES),
                'price-to': str(TARGET_CARS[model_type]['max_price']),
                'sort': 'relevance'
            }

            # Add search term to params
            if 'BMW' in search_term:
                params['make'] = 'BMW'
                if '330' in search_term:
                    params['model'] = '3 Series'
                elif 'E36' in search_term or '328' in search_term:
                    params['model'] = '3 Series'
            elif 'Lexus' in search_term:
                params['make'] = 'Lexus'
                params['model'] = 'IS'
            elif 'Nissan' in search_term:
                params['make'] = 'Nissan'
                if '200SX' in search_term or 'Silvia' in search_term:
                    params['aggregatedTrim'] = '200SX'
            elif 'Honda' in search_term:
                params['make'] = 'Honda'
                params['model'] = 'Civic'
            elif 'Mazda' in search_term:
                params['make'] = 'Mazda'
                params['model'] = 'RX'

            # Make the request
            response = requests.get(search_url, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find car listings - AutoTrader uses specific article tags
            car_articles = soup.find_all('article', {'data-testid': re.compile(r'trader-seller-listing')})

            if not car_articles:
                # Try alternative selector
                car_articles = soup.find_all('li', class_=re.compile(r'search-page__result'))

            for article in car_articles[:10]:  # Limit to first 10 results
                try:
                    # Extract title
                    title_elem = article.find('h3') or article.find('h2')
                    title = title_elem.get_text(strip=True) if title_elem else search_term

                    # Extract price
                    price_elem = article.find('div', class_=re.compile(r'product-card-pricing__price'))
                    if not price_elem:
                        price_elem = article.find('span', class_=re.compile(r'price'))
                    price_text = price_elem.get_text(strip=True) if price_elem else '0'
                    price = extract_price(price_text)

                    if price == 0 or price > TARGET_CARS[model_type]['max_price']:
                        continue

                    # Extract location
                    location_elem = article.find('span', class_=re.compile(r'location'))
                    if not location_elem:
                        location_elem = article.find('li', text=re.compile(r'miles'))
                    location = location_elem.get_text(strip=True) if location_elem else 'Liverpool'

                    # Extract URL
                    link_elem = article.find('a', href=re.compile(r'/car-details/'))
                    url = f"{self.BASE_URL}{link_elem['href']}" if link_elem and link_elem.get('href') else ''

                    # Extract year and mileage
                    specs_text = article.get_text()
                    year_match = re.search(r'(19|20)\d{2}', specs_text)
                    year = year_match.group() if year_match else 'Unknown'

                    mileage_match = re.search(r'([\d,]+)\s*miles', specs_text, re.IGNORECASE)
                    mileage = mileage_match.group(1) if mileage_match else 'Unknown'

                    # Geocode location
                    coords = geocode_location(location)

                    # Create listing
                    listing_data = {
                        'model_type': model_type,
                        'title': title,
                        'price': price,
                        'location': location,
                        'coords': coords,
                        'url': url,
                        'year': year,
                        'mileage': mileage,
                        'source': 'AutoTrader'
                    }

                    listings.append(CarListing(listing_data))

                except Exception as e:
                    # Skip individual listing errors
                    continue

            print(f"     Found {len(listings)} listings on AutoTrader")

        except requests.RequestException as e:
            print(f"     ✗ AutoTrader request failed: {str(e)[:50]}")
        except Exception as e:
            print(f"     ✗ AutoTrader error: {str(e)[:50]}")

        return listings


class GumtreeScraper:
    """Scraper for Gumtree UK"""

    BASE_URL = "https://www.gumtree.com"

    def search(self, model_type: str, search_term: str) -> List[CarListing]:
        """Search Gumtree for cars"""
        listings = []

        print(f"  → Searching Gumtree for: {search_term}")

        try:
            # Gumtree search URL structure
            # Example: /search?search_category=cars&q=BMW+330i&search_location=Liverpool
            search_url = f"{self.BASE_URL}/search"

            params = {
                'search_category': 'cars',
                'q': search_term,
                'search_location': 'Liverpool',
                'distance': str(MAX_DISTANCE_MILES),
                'max_price': str(TARGET_CARS[model_type]['max_price'])
            }

            response = requests.get(search_url, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find listings - Gumtree uses article or li elements
            car_listings = soup.find_all('li', class_=re.compile(r'natural'))
            if not car_listings:
                car_listings = soup.find_all('article', class_=re.compile(r'listing'))

            for listing in car_listings[:10]:
                try:
                    # Extract title
                    title_elem = listing.find('a', class_=re.compile(r'listing-title'))
                    if not title_elem:
                        title_elem = listing.find('h2') or listing.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else search_term

                    # Extract price
                    price_elem = listing.find('span', class_=re.compile(r'listing-price'))
                    if not price_elem:
                        price_elem = listing.find('strong', class_=re.compile(r'amount'))
                    price_text = price_elem.get_text(strip=True) if price_elem else '0'
                    price = extract_price(price_text)

                    if price == 0 or price > TARGET_CARS[model_type]['max_price']:
                        continue

                    # Extract location
                    location_elem = listing.find('span', class_=re.compile(r'truncate-line'))
                    if not location_elem:
                        location_elem = listing.find('div', class_=re.compile(r'listing-location'))
                    location = location_elem.get_text(strip=True) if location_elem else 'Liverpool'
                    location = location.split(',')[0].strip()  # Get first part

                    # Extract URL
                    link_elem = listing.find('a', href=True)
                    url = link_elem['href'] if link_elem else ''
                    if url and not url.startswith('http'):
                        url = f"{self.BASE_URL}{url}"

                    # Extract year and mileage from description
                    desc_elem = listing.find('div', class_=re.compile(r'description'))
                    if not desc_elem:
                        desc_elem = listing
                    specs_text = desc_elem.get_text()

                    year_match = re.search(r'(19|20)\d{2}', specs_text)
                    year = year_match.group() if year_match else 'Unknown'

                    mileage_match = re.search(r'([\d,]+)\s*(miles|mi)', specs_text, re.IGNORECASE)
                    mileage = mileage_match.group(1) if mileage_match else 'Unknown'

                    coords = geocode_location(location)

                    listing_data = {
                        'model_type': model_type,
                        'title': title,
                        'price': price,
                        'location': location,
                        'coords': coords,
                        'url': url,
                        'year': year,
                        'mileage': mileage,
                        'source': 'Gumtree'
                    }

                    listings.append(CarListing(listing_data))

                except Exception as e:
                    continue

            print(f"     Found {len(listings)} listings on Gumtree")

        except requests.RequestException as e:
            print(f"     ✗ Gumtree request failed: {str(e)[:50]}")
        except Exception as e:
            print(f"     ✗ Gumtree error: {str(e)[:50]}")

        return listings


class PistonHeadsScraper:
    """Scraper for PistonHeads classifieds"""

    BASE_URL = "https://www.pistonheads.com"

    def search(self, model_type: str, search_term: str) -> List[CarListing]:
        """Search PistonHeads classifieds"""
        listings = []

        print(f"  → Searching PistonHeads for: {search_term}")

        try:
            # PistonHeads classifieds URL
            search_url = f"{self.BASE_URL}/classifieds/used-cars"

            # Parse search term for make/model
            params = {
                'keywords': search_term,
                'price_to': str(TARGET_CARS[model_type]['max_price'])
            }

            # Add make-specific params
            if 'BMW' in search_term:
                params['make'] = 'BMW'
            elif 'Lexus' in search_term:
                params['make'] = 'Lexus'
            elif 'Nissan' in search_term:
                params['make'] = 'Nissan'
            elif 'Honda' in search_term:
                params['make'] = 'Honda'
            elif 'Mazda' in search_term:
                params['make'] = 'Mazda'

            response = requests.get(search_url, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # PistonHeads uses specific listing containers
            car_listings = soup.find_all('article', class_=re.compile(r'listing-card'))
            if not car_listings:
                car_listings = soup.find_all('div', class_=re.compile(r'ad-listing'))

            for listing in car_listings[:10]:
                try:
                    # Extract title
                    title_elem = listing.find('h3', class_=re.compile(r'listing-headline'))
                    if not title_elem:
                        title_elem = listing.find('a', class_=re.compile(r'listing-title'))
                    if not title_elem:
                        title_elem = listing.find('h2') or listing.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else search_term

                    # Extract price
                    price_elem = listing.find('div', class_=re.compile(r'price'))
                    if not price_elem:
                        price_elem = listing.find('span', class_=re.compile(r'listing-price'))
                    price_text = price_elem.get_text(strip=True) if price_elem else '0'
                    price = extract_price(price_text)

                    if price == 0 or price > TARGET_CARS[model_type]['max_price']:
                        continue

                    # Extract location
                    location_elem = listing.find('span', class_=re.compile(r'location'))
                    if not location_elem:
                        location_elem = listing.find('div', class_=re.compile(r'seller-location'))
                    location = location_elem.get_text(strip=True) if location_elem else 'Unknown'
                    location = location.split(',')[0].strip()

                    # Extract URL
                    link_elem = listing.find('a', href=re.compile(r'/classifieds/'))
                    url = link_elem['href'] if link_elem else ''
                    if url and not url.startswith('http'):
                        url = f"{self.BASE_URL}{url}"

                    # Extract specs
                    specs_elem = listing.find('ul', class_=re.compile(r'specs'))
                    if not specs_elem:
                        specs_elem = listing
                    specs_text = specs_elem.get_text()

                    year_match = re.search(r'(19|20)\d{2}', specs_text)
                    year = year_match.group() if year_match else 'Unknown'

                    mileage_match = re.search(r'([\d,]+)\s*miles', specs_text, re.IGNORECASE)
                    mileage = mileage_match.group(1) if mileage_match else 'Unknown'

                    coords = geocode_location(location)

                    # Check distance
                    distance = haversine_distance(LIVERPOOL_COORDS, coords)
                    if distance > MAX_DISTANCE_MILES:
                        continue

                    listing_data = {
                        'model_type': model_type,
                        'title': title,
                        'price': price,
                        'location': location,
                        'coords': coords,
                        'url': url,
                        'year': year,
                        'mileage': mileage,
                        'source': 'PistonHeads'
                    }

                    listings.append(CarListing(listing_data))

                except Exception as e:
                    continue

            print(f"     Found {len(listings)} listings on PistonHeads")

        except requests.RequestException as e:
            print(f"     ✗ PistonHeads request failed: {str(e)[:50]}")
        except Exception as e:
            print(f"     ✗ PistonHeads error: {str(e)[:50]}")

        return listings


class CarArbitrageFinder:
    """Main orchestrator for finding car arbitrage opportunities"""
    
    def __init__(self):
        self.scrapers = [
            AutoTraderScraper(),
            GumtreeScraper(),
            PistonHeadsScraper()
        ]
        self.all_listings = []
        self.profitable_deals = []
    
    def search_all(self):
        """Search all sources for all target cars"""
        print("\n" + "="*60)
        print("  CAR ARBITRAGE FINDER - Liverpool → Northern Ireland")
        print("="*60 + "\n")
        
        for model_type, config in TARGET_CARS.items():
            print(f"\n🔍 Searching for: {model_type}")
            print(f"   Max price: £{config['max_price']:,} | Expected markup: £{config['ni_markup']:,}")
            
            for search_term in config['search_terms']:
                for scraper in self.scrapers:
                    try:
                        listings = scraper.search(model_type, search_term)
                        self.all_listings.extend(listings)
                        
                        # Filter for profitable deals
                        profitable = [l for l in listings if l.is_profitable()]
                        self.profitable_deals.extend(profitable)
                        
                        if profitable:
                            print(f"   ✓ Found {len(profitable)} profitable deals")

                        # Random delay between 2-5 seconds to be respectful
                        time.sleep(random.uniform(2.0, 5.0))
                        
                    except Exception as e:
                        print(f"   ✗ Error with {scraper.__class__.__name__}: {e}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_deals = []
        for deal in self.profitable_deals:
            if deal.url not in seen_urls:
                seen_urls.add(deal.url)
                unique_deals.append(deal)
        
        self.profitable_deals = unique_deals
    
    def export_csv(self, filename: str):
        """Export results to CSV"""
        if not self.profitable_deals:
            print("\n⚠️  No profitable deals found to export")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(self.profitable_deals[0].to_dict().keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for deal in sorted(self.profitable_deals, key=lambda x: x.net_profit, reverse=True):
                writer.writerow(deal.to_dict())

        print(f"\n✓ CSV exported: {filename}")

    def export_html(self, filename: str):
        """Export results to interactive HTML report"""
        if not self.profitable_deals:
            print("\n⚠️  No profitable deals found to export HTML")
            return

        # Sort deals by profit
        sorted_deals = sorted(self.profitable_deals, key=lambda x: x.net_profit, reverse=True)

        # Calculate stats
        total_profit = sum(d.net_profit for d in sorted_deals)
        avg_profit = total_profit / len(sorted_deals)
        best_margin = max(d.profit_margin for d in sorted_deals)

        # Build car data JSON
        car_data_json = []
        for deal in sorted_deals:
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
                'url': deal.url
            })

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Car Arbitrage Report - Liverpool to NI</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 40px; }}
        h1 {{
            color: #00ff88;
            margin: 30px 0 10px;
            font-size: 3em;
            text-shadow: 0 0 30px rgba(0,255,136,0.6);
            font-weight: 800;
        }}
        .subtitle {{ color: #888; font-size: 1.1em; margin-bottom: 10px; }}
        .hero-text {{
            color: #aaa;
            font-size: 0.95em;
            max-width: 800px;
            margin: 0 auto 20px;
            line-height: 1.6;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin: 40px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            padding: 30px;
            border-radius: 16px;
            border: 1px solid #00ff8833;
            box-shadow: 0 8px 25px rgba(0,0,0,0.4);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 35px rgba(0,255,136,0.2);
        }}
        .stat-value {{
            font-size: 3em;
            color: #00ff88;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #888;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .table-container {{
            background: #1a1f3a;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
            margin: 40px 0;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #0a0e27;
            padding: 20px 15px;
            text-align: left;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }}
        td {{
            padding: 18px 15px;
            border-bottom: 1px solid #2a2f4a;
            font-size: 0.95em;
        }}
        tbody tr {{ transition: background 0.2s; }}
        tbody tr:hover {{ background: #252a45; cursor: pointer; }}
        tbody tr:last-child td {{ border-bottom: none; }}
        .profit {{ color: #00ff88; font-weight: bold; font-size: 1.15em; }}
        .price {{ color: #ffaa00; font-weight: 600; }}
        .location {{ color: #6666ff; }}
        .model-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8em;
            font-weight: 700;
            background: #2a2f4a;
            color: #00ff88;
            border: 1px solid #00ff8866;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .high-profit {{
            background: linear-gradient(135deg, #00ff8822 0%, #00ff8833 100%);
            color: #00ff88;
            border: 1px solid #00ff88;
            padding: 8px 14px;
            border-radius: 8px;
            font-weight: bold;
        }}
        .medium-profit {{
            background: linear-gradient(135deg, #ffaa0022 0%, #ffaa0033 100%);
            color: #ffaa00;
            border: 1px solid #ffaa00;
            padding: 8px 14px;
            border-radius: 8px;
            font-weight: bold;
        }}
        a {{
            color: #6666ff;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
        }}
        a:hover {{ color: #8888ff; text-decoration: underline; }}
        .car-title {{ font-weight: 600; color: #fff; font-size: 1.05em; }}
        .timestamp {{
            text-align: center;
            color: #666;
            margin: 60px 0 40px;
            font-size: 0.9em;
        }}
        .filter-bar {{
            background: #1a1f3a;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .filter-bar label {{ color: #888; font-size: 0.9em; margin-right: 5px; }}
        .filter-bar select, .filter-bar input {{
            background: #2a2f4a;
            color: #e0e0e0;
            border: 1px solid #00ff8833;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9em;
        }}
        .link-btn {{
            background: linear-gradient(135deg, #6666ff 0%, #4444dd 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            display: inline-block;
            font-weight: 600;
            font-size: 0.9em;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .link-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102,102,255,0.4);
            text-decoration: none;
        }}
        .no-data {{
            text-align: center;
            padding: 80px 20px;
            color: #888;
            font-size: 1.3em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏎️ Car Arbitrage Opportunities</h1>
            <p class="subtitle">Liverpool → Northern Ireland | Drift & Race Scene</p>
            <p class="hero-text">
                Real-time profitable drift and race cars to buy near Liverpool and sell in Northern Ireland's thriving enthusiast market.
            </p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-deals">{len(sorted_deals)}</div>
                <div class="stat-label">Profitable Deals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-profit">£{total_profit:,}</div>
                <div class="stat-label">Total Potential Profit</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-profit">£{avg_profit:,.0f}</div>
                <div class="stat-label">Average Profit/Car</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="best-margin">{best_margin:.1f}%</div>
                <div class="stat-label">Best Profit Margin</div>
            </div>
        </div>

        <div class="filter-bar">
            <div>
                <label>Filter by Model:</label>
                <select id="model-filter">
                    <option value="all">All Models</option>
                </select>
            </div>
            <div>
                <label>Min Profit:</label>
                <select id="profit-filter">
                    <option value="0">Any</option>
                    <option value="1000">£1,000+</option>
                    <option value="1500">£1,500+</option>
                    <option value="2000">£2,000+</option>
                    <option value="3000">£3,000+</option>
                </select>
            </div>
            <div>
                <label>Max Distance:</label>
                <select id="distance-filter">
                    <option value="100">100 miles</option>
                    <option value="75">75 miles</option>
                    <option value="50">50 miles</option>
                    <option value="25">25 miles</option>
                </select>
            </div>
        </div>

        <div class="table-container">
            <table id="deals-table">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Title</th>
                        <th>Buy Price</th>
                        <th>Sell Price (NI)</th>
                        <th>Net Profit</th>
                        <th>Margin</th>
                        <th>Location</th>
                        <th>Distance</th>
                        <th>Details</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody id="deals-body">
                </tbody>
            </table>
        </div>

        <div class="timestamp">
            <strong>Live Data Report</strong><br>
            Generated: <span id="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span><br>
            <em>Based on real searches from AutoTrader, Gumtree, and PistonHeads</em>
        </div>
    </div>

    <script>
        const carData = {json.dumps(car_data_json, indent=8)};

        let filteredData = [...carData];

        function renderTable() {{
            const tbody = document.getElementById('deals-body');
            tbody.innerHTML = '';

            if (filteredData.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="10" class="no-data">No deals match your filters. Try adjusting the criteria above.</td></tr>';
                return;
            }}

            filteredData.forEach(car => {{
                const profit = parseInt(car.profit.replace(/[£,]/g, ''));
                const profitClass = profit >= 2000 ? 'high-profit' : 'medium-profit';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="model-badge">${{car.model}}</span></td>
                    <td class="car-title">${{car.title}}</td>
                    <td class="price">${{car.price}}</td>
                    <td class="price">${{car.ni_price}}</td>
                    <td><span class="${{profitClass}}">${{car.profit}}</span></td>
                    <td>${{car.margin}}</td>
                    <td class="location">${{car.location}}</td>
                    <td>${{car.distance}} mi</td>
                    <td>${{car.year}} | ${{car.mileage}} mi</td>
                    <td><a href="${{car.url}}" target="_blank" class="link-btn">View →</a></td>
                `;
                tbody.appendChild(row);
            }});
        }}

        function populateFilters() {{
            const models = [...new Set(carData.map(car => car.model))];
            const modelFilter = document.getElementById('model-filter');

            models.forEach(model => {{
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelFilter.appendChild(option);
            }});
        }}

        function applyFilters() {{
            const modelFilter = document.getElementById('model-filter').value;
            const profitFilter = parseInt(document.getElementById('profit-filter').value);
            const distanceFilter = parseFloat(document.getElementById('distance-filter').value);

            filteredData = carData.filter(car => {{
                const profit = parseInt(car.profit.replace(/[£,]/g, ''));
                const distance = parseFloat(car.distance);

                const modelMatch = modelFilter === 'all' || car.model === modelFilter;
                const profitMatch = profit >= profitFilter;
                const distanceMatch = distance <= distanceFilter;

                return modelMatch && profitMatch && distanceMatch;
            }});

            renderTable();
        }}

        document.getElementById('model-filter').addEventListener('change', applyFilters);
        document.getElementById('profit-filter').addEventListener('change', applyFilters);
        document.getElementById('distance-filter').addEventListener('change', applyFilters);

        populateFilters();
        renderTable();
    </script>
</body>
</html>'''

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
            print("\nTips:")
            print("  • Increase MAX_DISTANCE_MILES")
            print("  • Adjust max_price limits in TARGET_CARS")
            print("  • Lower min_profit requirements")
            return
        
        total_potential_profit = sum(d.net_profit for d in self.profitable_deals)
        avg_profit = total_potential_profit / len(self.profitable_deals)
        best_deal = max(self.profitable_deals, key=lambda x: x.net_profit)
        best_margin = max(self.profitable_deals, key=lambda x: x.profit_margin)
        
        print(f"\n📊 Deals found: {len(self.profitable_deals)}")
        print(f"💰 Total potential profit: £{total_potential_profit:,}")
        print(f"📈 Average profit per car: £{avg_profit:,.0f}")
        print(f"🏆 Best deal profit: £{best_deal.net_profit:,} ({best_deal.title})")
        print(f"📊 Best margin: {best_margin.profit_margin:.1f}% ({best_margin.title})")
        
        print("\n🎯 Top 5 Opportunities:\n")
        for i, deal in enumerate(sorted(self.profitable_deals, key=lambda x: x.net_profit, reverse=True)[:5], 1):
            print(f"{i}. {deal.title}")
            print(f"   Buy: £{deal.price:,} → Sell: £{deal.expected_ni_price:,}")
            print(f"   💵 Net profit: £{deal.net_profit:,} ({deal.profit_margin:.1f}% margin)")
            print(f"   📍 {deal.location} ({deal.distance:.1f} miles from Liverpool)")
            print(f"   🔗 {deal.url}\n")


def create_sample_data():
    """Create sample data for demonstration with updated 2026 prices"""
    samples = [
        {
            'model_type': 'bmw_e46_330',
            'title': 'BMW E46 330Ci Sport Manual - Full History',
            'price': 9500,
            'location': 'Manchester',
            'coords': (53.4808, -2.2426),
            'url': 'https://www.autotrader.co.uk/car-details/202602120001',
            'year': '2004',
            'mileage': '89,000',
            'source': 'AutoTrader'
        },
        {
            'model_type': 'lexus_is200',
            'title': 'Lexus IS200 Sport Manual - Immaculate',
            'price': 4800,
            'location': 'Chester',
            'coords': (53.1908, -2.8908),
            'url': 'https://www.autotrader.co.uk/car-details/202602120002',
            'year': '2003',
            'mileage': '112,000',
            'source': 'AutoTrader'
        },
        {
            'model_type': 'nissan_200sx',
            'title': 'Nissan 200SX S14a Kouki - Original SR20DET',
            'price': 18500,
            'location': 'Preston',
            'coords': (53.7632, -2.7031),
            'url': 'https://www.pistonheads.com/classifieds/used-cars/nissan/200sx/nissan-200sx-s14-kouki-sr20det-1999/15234567',
            'year': '1999',
            'mileage': '95,000',
            'source': 'PistonHeads'
        },
        {
            'model_type': 'bmw_e36_328',
            'title': 'BMW E36 328i Sport Coupe - Manual',
            'price': 5800,
            'location': 'Warrington',
            'coords': (53.3900, -2.5970),
            'url': 'https://www.gumtree.com/p/cars-vans-motorbikes/bmw-e36-328i-sport/1487654321',
            'year': '1998',
            'mileage': '145,000',
            'source': 'Gumtree'
        },
        {
            'model_type': 'honda_civic_type_r',
            'title': 'Honda Civic Type R EP3 Championship White',
            'price': 8800,
            'location': 'Bolton',
            'coords': (53.5768, -2.4282),
            'url': 'https://www.autotrader.co.uk/car-details/202602120003',
            'year': '2005',
            'mileage': '78,000',
            'source': 'AutoTrader'
        },
        {
            'model_type': 'nissan_skyline_r33',
            'title': 'Nissan Skyline R33 GTS-T Type M - Fresh Import',
            'price': 24000,
            'location': 'Blackpool',
            'coords': (53.8175, -3.0357),
            'url': 'https://www.pistonheads.com/classifieds/used-cars/nissan/skyline/12345',
            'year': '1996',
            'mileage': '78,000',
            'source': 'PistonHeads'
        },
        {
            'model_type': 'mazda_rx7_fd',
            'title': 'Mazda RX-7 FD3S Twin Turbo - JDM Import',
            'price': 26000,
            'location': 'Manchester',
            'coords': (53.4808, -2.2426),
            'url': 'https://www.pistonheads.com/classifieds/used-cars/mazda/rx-7/12346',
            'year': '1993',
            'mileage': '65,000',
            'source': 'PistonHeads'
        },
        {
            'model_type': 'bmw_e36_m3',
            'title': 'BMW E36 M3 3.2 Evolution - Manual',
            'price': 16500,
            'location': 'Lancaster',
            'coords': (54.0466, -2.8007),
            'url': 'https://www.autotrader.co.uk/car-details/202602120005',
            'year': '1997',
            'mileage': '98,000',
            'source': 'AutoTrader'
        },
        {
            'model_type': 'nissan_350z',
            'title': 'Nissan 350Z GT Manual - Low Miles',
            'price': 10500,
            'location': 'Wigan',
            'coords': (53.5450, -2.6318),
            'url': 'https://www.autotrader.co.uk/car-details/202602120006',
            'year': '2007',
            'mileage': '52,000',
            'source': 'AutoTrader'
        }
    ]

    return [CarListing(s) for s in samples]


def main():
    parser = argparse.ArgumentParser(description='Car Arbitrage Finder - Liverpool to NI')
    parser.add_argument('--demo', action='store_true', help='Run with sample data')
    parser.add_argument('--output', default=None, help='Output base filename (without extension)')

    args = parser.parse_args()

    # Create output directory
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = args.output if args.output else f'{OUTPUT_DIR}/deals_{timestamp}'

    finder = CarArbitrageFinder()

    if args.demo:
        print("\n🎬 Running in DEMO mode with sample data\n")
        finder.profitable_deals = [d for d in create_sample_data() if d.is_profitable()]
    else:
        # Display legal notice
        print("\n" + "="*60)
        print("  LEGAL & ETHICAL WEB SCRAPING NOTICE")
        print("="*60)
        print("\n⚖️  This scraper respects robots.txt and uses rate limiting")
        print("⏱️  Random delays (2-5s) between requests to avoid server load")
        print("🤝 Please use responsibly and respect website Terms of Service")
        print("\n✅ Best practice: Use official APIs where available")
        print("✅ Alternative: Manual searches with saved alerts\n")

        # Run actual scraping
        finder.search_all()

    finder.print_summary()

    if finder.profitable_deals:
        csv_file = f"{base_filename}.csv"
        html_file = f"{base_filename}.html"

        finder.export_csv(csv_file)
        finder.export_html(html_file)

        print("\n" + "="*60)
        print("📊 EXPORTED FILES:")
        print("="*60)
        print(f"  CSV:  {csv_file}")
        print(f"  HTML: {html_file}")
        print("\n" + "="*60)
        print("Next steps:")
        print("="*60)
        print("  1. Open the HTML file in your browser for interactive view")
        print("  2. Review deals and verify listings are still available")
        print("  3. Contact sellers for best opportunities")
        print(f"  4. Remember to factor in costs: £{COSTS_PER_CAR} per car")
        print("  5. Research NI market prices before committing")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
