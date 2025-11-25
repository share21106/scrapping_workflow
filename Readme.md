# ============================================
# FILE 1: requirements.txt
# ============================================
Flask==3.0.0
flask-cors==4.0.0
selenium==4.15.2
beautifulsoup4==4.12.2
lxml==4.9.3
gunicorn==21.2.0

# ============================================
# FILE 2: Procfile (for Heroku/Railway)
# ============================================
web: gunicorn app:app

# ============================================
# FILE 3: runtime.txt (for Heroku)
# ============================================
python-3.11.6

# ============================================
# FILE 4: railway.json (for Railway)
# ============================================
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}

# ============================================
# FILE 5: render.yaml (for Render)
# ============================================
services:
  - type: web
    name: flippa-scraper
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.6

# ============================================
# FILE 6: .gitignore
# ============================================
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv
*.log
.DS_Store
.env

# ============================================
# FILE 7: Dockerfile (Optional - for custom deployment)
# ============================================
FROM python:3.11-slim

# Install Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]

# ============================================
# FILE 8: README.md (Deployment Instructions)
# ============================================

# Flippa Scraper API

A Flask API for scraping Flippa.com business listings, designed to work with n8n.

## Quick Deploy

### Option 1: Railway (Recommended - FREE)
1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub account
4. Select this repository
5. Railway will auto-detect and deploy
6. Copy your API URL: `https://your-app.railway.app`

### Option 2: Render (FREE)
1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Render will auto-deploy
5. Copy your API URL: `https://your-app.onrender.com`

### Option 3: Heroku
1. Install Heroku CLI
2. Run:
```bash
heroku login
heroku create flippa-scraper
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-google-chrome
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-chromedriver
git push heroku main
```

## Testing Your API

```bash
# Test health check
curl https://your-api-url.com/health

# Test scraping
curl -X POST https://your-api-url.com/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://flippa.com/search",
    "max_listings": 10,
    "filters": {
      "category": "ecommerce"
    }
  }'
```

## Using with n8n

1. Add **HTTP Request** node in n8n
2. Set:
   - Method: POST
   - URL: `https://your-api-url.com/scrape`
   - Body Content Type: JSON
   - Body:
   ```json
   {
     "url": "https://flippa.com/search",
     "max_listings": 20,
     "filters": {
       "min_price": 1000,
       "max_price": 50000,
       "category": "ecommerce"
     }
   }
   ```

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /scrape` - Scrape Flippa listings

## Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| url | string | Flippa search URL | https://flippa.com/search |
| max_listings | integer | Max listings to scrape (max: 50) | 20 |
| filters.min_price | integer | Minimum price filter | - |
| filters.max_price | integer | Maximum price filter | - |
| filters.category | string | Category filter (ecommerce, saas, content, apps) | - |

## Response Format

```json
{
  "success": true,
  "total_listings": 20,
  "listings": [
    {
      "id": 1,
      "listing_id": "12345",
      "title": "E-commerce Store",
      "url": "https://flippa.com/...",
      "price": "$50,000",
      "revenue": "$10,000/mo",
      "profit": "$5,000/mo",
      "category": "E-commerce",
      "description": "...",
      "image_url": "...",
      "scraped_at": "2024-01-01T12:00:00"
    }
  ],
  "url": "https://flippa.com/search",
  "timestamp": "2024-01-01T12:00:00"
}
```