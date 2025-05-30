# playwright_scraper.py

import os
import sys
import random
import tempfile
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import django
from asgiref.sync import sync_to_async
from amazoncaptcha import AmazonCaptcha
from django.utils import timezone
from django.contrib.auth.models import User
from playwright.async_api import async_playwright
from base.models import TrackedProduct, PriceHistory

# Django setup
sys.path.append("..")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproj.settings")
django.setup()

# -------------------------------
# Utility Functions
# -------------------------------

def clean_price(price_text):
    """Convert raw price text to Decimal."""
    if not price_text:
        return None
    try:
        return Decimal(price_text.replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None

def log_error(message, exception):
    """Print formatted error message."""
    print(f"{message}: {exception}")

# -------------------------------
# Main Scraper
# -------------------------------

# Temp in-memory store per user (for frontend to fetch scraped results)
TEMP_SCRAPE_RESULTS = {}

async def scrape_amazon(search_query, user_id=None, depth=3, single_page=False, scheduled_scraping=False):
    """
    Scrape Amazon search results for a given query.
    Stores the results temporarily per user for later selection.
    """
    if not user_id:
        raise ValueError("User ID is required for scraping.")

    user = await sync_to_async(User.objects.get)(id=user_id)
    print(f"Scraping Amazon for user: {user.username} (ID: {user.id}) — Depth: {depth}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1"
            },
            locale="en-US",
            geolocation={"latitude": 37.7749, "longitude": -122.4194},
            timezone_id="America/Los_Angeles"
        )

        await context.add_cookies([
            {"name": "session-id", "value": "133-1234567-1234567", "domain": ".amazon.com", "path": "/"},
            {"name": "session-id-time", "value": "2082787201l", "domain": ".amazon.com", "path": "/"},
            {"name": "ubid-main", "value": "133-1234567-1234567", "domain": ".amazon.com", "path": "/"},
            {"name": "x-main", "value": "x-main-cookie-value", "domain": ".amazon.com", "path": "/"}
        ])

        context.set_default_navigation_timeout(30000)
        context.set_default_timeout(30000)
        page = await context.new_page()

        await page.goto("https://www.amazon.com")
        await page.wait_for_timeout(random.uniform(2000, 5000))

        # --- CAPTCHA Handling (same logic) ---
        for attempt in range(10):
            if await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                print(f"CAPTCHA detected, attempting to solve... (Attempt {attempt + 1}/10)")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
                    captcha_path = temp_img.name
                    await page.locator("div.a-row.a-text-center img").screenshot(path=captcha_path)

                try:
                    solver = AmazonCaptcha(captcha_path)
                    captcha_solution = solver.solve()
                    if len(captcha_solution) == 6:
                        await page.fill("input#captchacharacters", captcha_solution.strip())
                        await page.click("button[type='submit']")
                        await page.wait_for_load_state('networkidle')
                        if not await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                            print("CAPTCHA solved.")
                            break
                    else:
                        print("Failed CAPTCHA solution attempt, retrying...")
                        await page.locator("a:has-text('Try different image')").click()
                        await page.wait_for_timeout(2000)
                finally:
                    os.remove(captcha_path)
            else:
                print("No CAPTCHA detected.")
                break
        else:
            print("Manual CAPTCHA solving required. Please solve it in the browser...")
            while await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                await page.wait_for_timeout(1000)

        # --- Perform search ---
        try:
            await page.fill('input[name="field-keywords"]', search_query)
            await page.press('input[name="field-keywords"]', "Enter")
            await page.wait_for_timeout(random.uniform(3000, 6000))
        except Exception as e:
            log_error("Error accessing search bar", e)
            await browser.close()
            return

        # --- Scrape product results ---
        scraped_products = []
        current_page = 1
        max_pages = depth  # ✅ use passed-in depth instead of fixed 3
        product_counter = 0

        while current_page <= max_pages:
            try:
                await page.wait_for_selector('div.s-main-slot', timeout=60000)
                await page.wait_for_timeout(random.uniform(2000, 5000))
                products = await page.query_selector_all('div.s-main-slot div[data-component-type="s-search-result"]')

                for product in products:
                    try:
                        title_element = await product.query_selector("h2")
                        title = await title_element.get_attribute("aria-label") if title_element else "No title found"
                        if not title and title_element:
                            span_elements = await title_element.query_selector_all("span")
                            title = await span_elements[1].text_content() if len(span_elements) > 1 else await span_elements[0].text_content()
                        if title and title.startswith("Sponsored Ad -"):
                            title = title.replace("Sponsored Ad -", "").strip()

                        price_element = await product.query_selector("span.a-price span.a-offscreen")
                        price_text = await price_element.text_content() if price_element else None
                        price_numeric = clean_price(price_text)

                        rating_element = await product.query_selector("span.a-icon-alt")
                        rating = float((await rating_element.text_content()).split()[0]) if rating_element else None

                        reviews_element = await product.query_selector("span.a-size-base.s-underline-text")
                        reviews = int((await reviews_element.text_content()).replace(",", "")) if reviews_element else None

                        link_element = await product.query_selector("a.a-link-normal")
                        product_link = f"https://www.amazon.com{await link_element.get_attribute('href')}" if link_element else None

                        # ✅ Fetch availability from product page
                        availability = "Unknown"
                        if product_link:
                            try:
                                detail_page = await context.new_page()
                                await detail_page.goto(product_link)
                                await detail_page.wait_for_timeout(1500)
                                availability_container = await detail_page.query_selector("#availability")
                                if availability_container:
                                    in_stock = await availability_container.query_selector("span.a-size-medium.a-color-success")
                                    warning = await availability_container.query_selector("span.a-size-base.a-color-price.a-text-bold")
                                    if in_stock:
                                        availability = await in_stock.text_content()
                                    elif warning:
                                        availability = await warning.text_content()
                                    else:
                                        availability = "Not available"
                                await detail_page.close()
                            except Exception as e:
                                log_error("Availability scrape failed", e)

                        scraped_products.append({
                            "title": title,
                            "price": price_numeric,
                            "rating": rating,
                            "reviews": reviews,
                            "link": product_link,
                            "availability": availability,
                        })
                        product_counter += 1

                    except Exception as e:
                        log_error("Error extracting product details", e)
                        continue

                # ✅ Handle next-page logic with depth limit
                next_button = await page.query_selector("a.s-pagination-item.s-pagination-next")
                if not next_button or single_page:
                    break
                next_page_url = await next_button.get_attribute("href")
                if not next_page_url:
                    break  # ⛔ stop if no valid href found
                await page.goto(f"https://www.amazon.com{next_page_url}")
                current_page += 1

            except Exception as e:
                log_error(f"Error scraping product data on page {current_page}", e)
                break

        await browser.close()

        if scheduled_scraping:
            return scraped_products

        # ✅ Store results for manual selection (frontend)
        TEMP_SCRAPE_RESULTS[user.id] = {
            "results": scraped_products,
            "timestamp": timezone.now()
        }
        print(f"✅ {len(scraped_products)} products scraped and stored for user {user.username}")

        # ✅ Print each product to terminal
        for i, p in enumerate(scraped_products, start=1):
            print(f"{i}. {p['title']} — ${p['price']} — {p['availability']}")



# -------------------------------
# Product Selection Flow (Manual backend-only usage)
# -------------------------------

async def select_product_for_tracking(tracked_products, context, user_id=None):
    """Allow user to select specific products from scraped results and add to tracking list via terminal."""

    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
    except Exception as e:
        log_error("Error fetching user", e)
        return

    selected_count = 0  # ✅ Track how many items were added or updated

    while True:
        selection = input("Enter product number to track (or 'done' to finish): ")
        if selection.lower() == 'done':
            print("Exiting product selection...")
            break

        try:
            selected_index = int(selection)
            if 0 <= selected_index < len(tracked_products):
                product_data = tracked_products[selected_index]
                product_link = product_data.get("link")

                # ✅ Try to reuse existing availability if present
                availability = product_data.get("availability", "Unknown")

                if availability == "Unknown" and product_link:
                    try:
                        product_page = await context.new_page()
                        await product_page.goto(product_link)
                        availability_container = await product_page.query_selector("#availability")

                        if availability_container:
                            in_stock = await availability_container.query_selector("span.a-size-medium.a-color-success")
                            warning = await availability_container.query_selector("span.a-size-base.a-color-price.a-text-bold")
                            if in_stock:
                                availability = await in_stock.text_content()
                            elif warning:
                                availability = await warning.text_content()
                            else:
                                availability = "Not available"
                        else:
                            availability = "No availability info"
                    except Exception as e:
                        log_error("Error fetching availability", e)
                    finally:
                        await product_page.close()

                # Save product to DB
                current_time = (timezone.now() + timedelta(hours=2)).replace(microsecond=0)

                existing_qs = await sync_to_async(TrackedProduct.objects.filter)(
                    title=product_data["title"], user=user
                )
                tracked_product = await sync_to_async(existing_qs.first)()

                if tracked_product:
                    tracked_product.price = product_data["price"]
                    tracked_product.rating = product_data["rating"]
                    tracked_product.reviews = product_data["reviews"]
                    tracked_product.availability = availability
                    tracked_product.date_scraped = current_time
                    await sync_to_async(tracked_product.save)()
                    print(f"🔄 Updated: {product_data['title']} — Availability: {availability}")
                else:
                    tracked_product = await sync_to_async(TrackedProduct.objects.create)(
                        title=product_data["title"],
                        price=product_data["price"],
                        rating=product_data["rating"],
                        reviews=product_data["reviews"],
                        availability=availability,
                        date_scraped=current_time,
                        user=user,
                    )
                    print(f"🆕 New tracked: {product_data['title']} — Availability: {availability}")

                await sync_to_async(PriceHistory.objects.create)(
                    product=tracked_product,
                    price=product_data["price"],
                    availability=availability,
                    date_recorded=current_time,
                )
                print(f"📈 Price history entry added for {product_data['title']}.")

                selected_count += 1  # ✅ Count this successful addition

            else:
                print("❌ Invalid selection. Please enter a valid number.")
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
        except Exception as e:
            log_error("Unexpected error", e)

    print(f"\n✅ {selected_count} product(s) added to your tracked products.")

# -------------------------------
# Standalone Runner (Backend-only manual test)
# -------------------------------

if __name__ == "__main__":
    import asyncio
    search_query = input("Enter your search query: ")
    asyncio.run(scrape_amazon(search_query))

