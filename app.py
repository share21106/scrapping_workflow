"""
Flippa Scraper API - Flask Application
"""

import json
import time
from flask import Flask, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

app = Flask(__name__)
CORS(app)

URL = "https://flippa.com/search"

def start_driver():
    options = Options()
    options.add_argument("--headless=new")            # HIDE CHROME (new headless mode)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")   # Required for some sites in headless mode

    return webdriver.Chrome(options=options)

def scrape():
    driver = start_driver()
    driver.get(URL)

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='listing-']")))

    listings = driver.find_elements(By.CSS_SELECTOR, "div[id^='listing-']")
    print("Found listings:", len(listings))

    items = []

    # Only scrape first 5 items
    for card in listings[:3]:

        # TITLE
        try:
            title = card.find_element(By.CSS_SELECTOR, "h6").text.strip()
        except:
            title = ""

        # INDUSTRY
        try:
            industry = card.find_element(
                By.XPATH, ".//div[div[contains(text(), 'Industry')]]/div[2]"
            ).text.strip()
        except:
            industry = ""

        print(title, "|", industry)

        items.append({
            "title": title,
            "industry": industry
        })

    return items

@app.route('/', methods=['GET'])
def home():
    """Scrape Flippa listings"""
    try:
        items = scrape()
        return jsonify(items)
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
