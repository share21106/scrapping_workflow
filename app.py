"""
Flippa Scraper API - Flask Application
Deploy this to Railway, Render, or Heroku
Then call it from n8n using HTTP Request node
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for n8n requests

def get_chrome_driver():
    """Setup Chrome driver for different environments"""
    chrome_options = Options()
    
    # Essential options for headless operation
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # For deployment environments (Railway, Render, Heroku)
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_flippa(url='https://flippa.com/search', max_listings=20, filters=None):
    """
    Main scraping function for Flippa
    
    Args:
        url: Flippa search URL
        max_listings: Maximum number of listings to scrape
        filters: Dictionary of filters (min_price, max_price, category)
    
    Returns:
        Dictionary with scraped data
    """
    driver = None
    
    try:
        # Build URL with filters
        if filters:
            params = []
            if filters.get('min_price'):
                params.append(f"min_price={filters['min_price']}")
            if filters.get('max_price'):
                params.append(f"max_price={filters['max_price']}")
            if filters.get('category'):
                params.append(f"filter[property_type][]={filters['category']}")
            
            if params:
                url = f"{url}?{'&'.join(params)}"
        
        print(f"Scraping: {url}")
        driver = get_chrome_driver()
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Scroll to trigger lazy loading
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Get page source
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find listings - multiple strategies
        listings = []
        
        # Strategy 1: Find by common patterns
        listing_containers = (
            soup.find_all('div', class_=lambda x: x and 'listing' in str(x).lower()) or
            soup.find_all('article') or
            soup.find_all('div', class_=lambda x: x and 'card' in str(x).lower())
        )
        
        print(f"Found {len(listing_containers)} potential listings")
        
        for idx, container in enumerate(listing_containers[:max_listings]):
            try:
                listing = {
                    'id': idx + 1,
                    'scraped_at': datetime.now().isoformat()
                }
                
                # Extract title
                title_elem = (
                    container.find('h2') or 
                    container.find('h3') or 
                    container.find('h4') or
                    container.find('a', class_=lambda x: x and 'title' in str(x).lower())
                )
                listing['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
                
                # Extract URL
                link = container.find('a', href=True)
                if link:
                    href = link['href']
                    listing['url'] = href if href.startswith('http') else f"https://flippa.com{href}"
                    # Extract listing ID from URL
                    listing['listing_id'] = href.split('/')[-1] if '/' in href else 'N/A'
                else:
                    listing['url'] = 'N/A'
                    listing['listing_id'] = f'item_{idx}'
                
                # Extract price - look for $ symbols
                price_text = container.get_text()
                price_matches = [t for t in price_text.split() if '$' in t]
                listing['price'] = price_matches[0] if price_matches else 'N/A'
                
                # Extract revenue
                revenue_elem = container.find(string=lambda x: x and 'revenue' in str(x).lower())
                listing['revenue'] = revenue_elem.strip() if revenue_elem else 'N/A'
                
                # Extract profit
                profit_elem = container.find(string=lambda x: x and 'profit' in str(x).lower())
                listing['profit'] = profit_elem.strip() if profit_elem else 'N/A'
                
                # Extract category/type
                category_elem = container.find(class_=lambda x: x and ('badge' in str(x).lower() or 'category' in str(x).lower()))
                listing['category'] = category_elem.get_text(strip=True) if category_elem else 'N/A'
                
                # Extract description snippet
                desc_elem = container.find('p')
                listing['description'] = desc_elem.get_text(strip=True)[:200] if desc_elem else 'N/A'
                
                # Extract image
                img = container.find('img', src=True)
                listing['image_url'] = img['src'] if img else 'N/A'
                
                # Only add if has meaningful data
                if listing['title'] != 'N/A' or listing['url'] != 'N/A':
                    listings.append(listing)
                    print(f"✓ Scraped: {listing['title'][:50]}")
                
            except Exception as e:
                print(f"Error parsing listing {idx}: {e}")
                continue
        
        return {
            'success': True,
            'total_listings': len(listings),
            'listings': listings,
            'url': url,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Scraping error: {e}")
        return {
            'success': False,
            'error': str(e),
            'listings': [],
            'timestamp': datetime.now().isoformat()
        }
        
    finally:
        if driver:
            driver.quit()


# API Endpoints

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'Flippa Scraper API',
        'version': '1.0',
        'endpoints': {
            '/scrape': 'POST - Scrape Flippa listings',
            '/health': 'GET - Health check'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check for monitoring"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Main scraping endpoint
    
    Expected JSON body:
    {
        "url": "https://flippa.com/search",
        "max_listings": 20,
        "filters": {
            "min_price": 1000,
            "max_price": 50000,
            "category": "ecommerce"
        }
    }
    """
    try:
        data = request.get_json() or {}
        
        url = data.get('url', 'https://flippa.com/search')
        max_listings = data.get('max_listings', 20)
        filters = data.get('filters', {})
        
        # Validate max_listings
        if max_listings > 50:
            return jsonify({
                'success': False,
                'error': 'max_listings cannot exceed 50'
            }), 400
        
        # Run scraper
        result = scrape_flippa(url, max_listings, filters)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)