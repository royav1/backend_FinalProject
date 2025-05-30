# 🛒 Amazon Price Tracker (Backend)

This is the Django backend for the Amazon Price Tracker app. It allows users to track Amazon product prices, organize them into watchlists,
view price history, and set up target-based alerts via scraping automation.


## 📦 Setting Up the Environment

### 1. Create and activate a virtual environment:
py -m venv cleanenv
.\cleanenv\Scripts\activate


### 2. Install dependencies:
pip install -r requirements.txt


### 3. Run database migrations:
python manage.py migrate


### 4. Start the development server:
python manage.py runserver


## 🧠 What This Program Does
### This backend powers an Amazon scraping app with full support for:

* User registration and authentication
* Product tracking
* Watchlist organization
* Price history recording
* Scheduled and manual scraping
* Target-price alert mock notifications
* Sale event tracking


# 🚀 Backend Features:

## 🔐 Authentication
### 1. Register – Create new users
### 2. Login – JWT-based login
### 3. Logout – Secure logout
### 4. Get user info – Fetch username and email

## 📦 Product Tracking
### 5. Search Amazon – Scrape product search results
### 6. Track product – Add a product to your tracked list
### 7. Delete product – Remove from tracked list but keep history
### 8. Set target price – Track when a product drops below threshold

## 📁 Watchlists
### 9. Create watchlist – Name and organize groups
### 10. Rename/delete watchlist
### 11. Add/remove products to/from watchlist
### 12. Toggle global scraping ON/OFF

## 📈 Price History
### 13. View price history – See historical data for tracked products
### 14. Filter by date – Choose 7d / 30d / 90d / 6mo / 1yr
### 15. Filter by sale events – Limit results to special sales
### 16. Snapshot fallback – View history even for deleted products

## 🕒 Scraping Logic
### 17. Scheduled scraping – Runs daily and respects sale events
### 18. Manual scraping – Trigger from UI on demand
### 19. Event-based alerts – Trigger notifications when price drops
### 20. Floating frontend notification – Mock email shown in browser


## 🧪 Scraper Modules

### 1. `playwright_scraper.py`
The primary scraper used by the app. It supports both:
- **Manual scraping** (when triggered from the UI), and  
- **Scheduled scraping** (for automation).

It handles:
- Keyword-based search
- CAPTCHA solving
- Pagination (based on selected depth)
- Extraction of product details (title, price, rating, reviews, availability, URL)
- Storing results temporarily for user selection (manual)
- Saving price history and triggering alerts (scheduled)

---

### 2. `refinement_scraper.py`
This is a **debugging and precision-focused scraper**, used independently from the app interface.

Key features:
- Accepts any search query as input.
- Scrapes full product result pages from Amazon and extracts **all matching product URLs**.
- Navigates to each product page to extract:
  - Title
  - Price (both text and numeric)
  - Rating
  - Review count
  - Availability
  - Product URL
- Prints a clean summary of all products to the console.
- Helps verify scraping behavior and tune match accuracy for existing products in the database (e.g., during scheduled re-checks).
- **Does not store anything in the database** — ideal for isolated testing and analysis.


💡 **Note:** This backend is designed to work with a separate Angular frontend and is intended to be deployed using Docker or Docker Compose as part of a multi-container setup.
