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

def scrape_flippa(url='https://flippa.com/search?search_template=most_relevant&filter%5Bsale_method%5D=auction,classified&filter%5Bstatus%5D=open&filter%5Bproperty_type%5D=website,fba,saas,ecommerce_store,plugin_and_extension,ai_apps_and_tools,youtube,ios_app,android_app,game,crypto_app,social_media,newsletter,service_and_agency,service,projects_and_concepts,other&filter%5Brevenue_generating%5D=T,F', max_listings=5, filters=None):
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
        listing_containers = []
        # Find divs with listing or card in class name
        for div in soup.find_all('div'):
            classes = div.get('class', [])
            class_str = ' '.join(classes).lower() if classes else ''
            if 'listing' in class_str or 'card' in class_str:
                listing_containers.append(div)
        # Also include all articles
        listing_containers.extend(soup.find_all('article'))
        
        print(f"Found {len(listing_containers)} potential listings")
        
        for idx, container in enumerate(listing_containers[:max_listings]):
            try:
                listing = {
                    'id': idx + 1,
                    'scraped_at': datetime.now().isoformat()
                }
                
                # Extract title from h6 tag
                title_elem = container.find('h6')
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
                
                # Extract key_data fields (Type, Industry, Monetization, Site Age, Net Profit)
                # Look for divs with label (tw-text-gray-600) and value (tw-font-semibold) pattern
                key_data_items = {}
                
                # Find all divs in container
                all_divs = container.find_all('div', recursive=True)
                
                # Collect label and value divs
                label_divs = []
                value_divs = []
                
                for div in all_divs:
                    div_classes = div.get('class', [])
                    if div_classes:
                        div_class_str = ' '.join(div_classes).lower()
                        if 'tw-text-gray-600' in div_class_str:
                            label_divs.append(div)
                        elif 'tw-font-semibold' in div_class_str:
                            value_divs.append(div)
                
                # Match labels with values
                for label_div in label_divs:
                    label_text = label_div.get_text(strip=True)
                    if label_text in ['Type', 'Industry', 'Monetization', 'Site Age', 'Net Profit']:
                        # Find corresponding value - check next sibling first
                        value_text = 'N/A'
                        next_sib = label_div.find_next_sibling('div')
                        if next_sib:
                            next_classes = next_sib.get('class', [])
                            if next_classes and 'tw-font-semibold' in ' '.join(next_classes).lower():
                                value_text = next_sib.get_text(strip=True)
                        
                        # If not found, check parent's value divs
                        if value_text == 'N/A' and label_div.parent:
                            parent = label_div.parent
                            for val_div in value_divs:
                                if val_div in parent.find_all('div') and val_div != label_div:
                                    value_text = val_div.get_text(strip=True)
                                    break
                        
                        # If still not found, use any nearby value div
                        if value_text == 'N/A' and value_divs:
                            value_text = value_divs[0].get_text(strip=True)
                        
                        if value_text != 'N/A':
                            key_data_items[label_text.lower().replace(' ', '_')] = value_text
                
                listing['type'] = key_data_items.get('type', 'N/A')
                listing['industry'] = key_data_items.get('industry', 'N/A')
                listing['monetization'] = key_data_items.get('monetization', 'N/A')
                listing['site_age'] = key_data_items.get('site_age', 'N/A')
                listing['net_profit'] = key_data_items.get('net_profit', 'N/A')
                
                # Set default values for other fields
                listing['revenue'] = 'N/A'
                listing['profit'] = 'N/A'
                listing['category'] = 'N/A'
                listing['description'] = 'N/A'
                
                # Extract country - look for div with ng-if="listing.country_name" or div with svg and span
                listing['country'] = 'N/A'
                for div in container.find_all('div'):
                    ng_if = div.get('ng-if', '')
                    if 'country_name' in ng_if:
                        # Find span with ng-binding class inside this div
                        for span in div.find_all('span'):
                            classes = span.get('class', [])
                            if 'ng-binding' in ' '.join(classes).lower():
                                country_text = span.get_text(strip=True)
                                if country_text and len(country_text) < 50 and not country_text.replace(' ', '').isdigit():
                                    listing['country'] = country_text
                                    break
                        if listing['country'] != 'N/A':
                            break
                    # Also check for div with svg (map pin icon) and span
                    elif div.find('svg') and div.find('span'):
                        for span in div.find_all('span'):
                            classes = span.get('class', [])
                            if 'ng-binding' in ' '.join(classes).lower():
                                country_text = span.get_text(strip=True)
                                if country_text and len(country_text) < 50 and not country_text.replace(' ', '').isdigit():
                                    listing['country'] = country_text
                                    break
                        if listing['country'] != 'N/A':
                            break
                
                # Extract price - look for USD $ pattern
                price_elem = container.find('h5')
                if price_elem:
                    listing['price'] = price_elem.get_text(strip=True)
                else:
                    # Fallback: look for $ symbols
                    price_text = container.get_text()
                    price_matches = [t for t in price_text.split() if '$' in t]
                    listing['price'] = price_matches[0] if price_matches else 'N/A'
                
                # Extract image
                img = container.find('img', src=True)
                listing['image_url'] = img['src'] if img else 'N/A'
                
                # Add all listings regardless of data completeness
                listings.append(listing)
                title_display = listing['title'][:50] if listing['title'] != 'N/A' else f"Listing {idx + 1}"
                print(f"✓ Scraped: {title_display}")
                
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
        "url": "https://flippa.com/search?search_template=most_relevant&filter%5Bsale_method%5D=auction,classified&filter%5Bstatus%5D=open&filter%5Bproperty_type%5D=website,fba,saas,ecommerce_store,plugin_and_extension,ai_apps_and_tools,youtube,ios_app,android_app,game,crypto_app,social_media,newsletter,service_and_agency,service,projects_and_concepts,other&filter%5Brevenue_generating%5D=T,F",
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
        
        url = data.get('url', 'https://flippa.com/search?search_template=most_relevant&filter%5Bsale_method%5D=auction,classified&filter%5Bstatus%5D=open&filter%5Bproperty_type%5D=website,fba,saas,ecommerce_store,plugin_and_extension,ai_apps_and_tools,youtube,ios_app,android_app,game,crypto_app,social_media,newsletter,service_and_agency,service,projects_and_concepts,other&filter%5Brevenue_generating%5D=T,F')
        max_listings = data.get('max_listings', 5)
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