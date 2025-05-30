import os
import random
import tempfile
from playwright.async_api import async_playwright
from amazoncaptcha import AmazonCaptcha
import asyncio


async def scrape_amazon(search_query, persist_browser=False):
    """Scrape Amazon using a dynamic search query, extract product URLs, and extract data from all product pages."""
    browser = None
    try:
        print("Starting hard-coded scraping process...")

        # Launch the browser
        print("Launching the browser...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible browser
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                },
                locale="en-US",
                geolocation={"latitude": 37.7749, "longitude": -122.4194},
                timezone_id="America/Los_Angeles",
            )

            # Add cookies for session persistence
            print("Adding cookies...")
            await context.add_cookies([
                {"name": "session-id", "value": "133-1234567-1234567", "domain": ".amazon.com", "path": "/"},
                {"name": "session-id-time", "value": "2082787201l", "domain": ".amazon.com", "path": "/"},
                {"name": "ubid-main", "value": "133-1234567-1234567", "domain": ".amazon.com", "path": "/"},
                {"name": "x-main", "value": "x-main-cookie-value", "domain": ".amazon.com", "path": "/"},
            ])

            # Set timeouts
            context.set_default_navigation_timeout(60000)
            context.set_default_timeout(60000)

            # Create a new page
            page = await context.new_page()

            # Navigate to Amazon homepage
            print("Navigating to Amazon homepage...")
            await page.goto("https://www.amazon.com", timeout=100000)
            await page.wait_for_timeout(random.uniform(5000, 10000))

            # Check for and handle CAPTCHA
            for attempt in range(10):
                if await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                    print(f"CAPTCHA detected, attempting to solve... (Attempt {attempt + 1}/10)")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
                        captcha_image_path = temp_img.name
                        await page.locator("div.a-row.a-text-center img").screenshot(path=captcha_image_path)
                    try:
                        solver = AmazonCaptcha(captcha_image_path)
                        captcha_solution = solver.solve()
                        if len(captcha_solution) == 6:
                            await page.fill("input#captchacharacters", captcha_solution.strip())
                            await page.click("button[type='submit']")
                            await page.wait_for_load_state('networkidle')
                            if not await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                                print("CAPTCHA solved.")
                                break
                        else:
                            print("Failed CAPTCHA solution attempt, trying a new image.")
                            await page.locator("a:has-text('Try different image')").click()
                            await page.wait_for_timeout(4000)
                    finally:
                        os.remove(captcha_image_path)
                else:
                    print("No CAPTCHA detected.")
                    break
            else:
                print("Manual CAPTCHA solving required. Please solve it in the browser.")
                while await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                    await page.wait_for_timeout(2000)

            # Perform the search
            print(f"Searching for: {search_query}")
            search_bar_selector = 'input#twotabsearchtextbox'
            await page.fill(search_bar_selector, search_query)
            await page.press(search_bar_selector, "Enter")

            # Wait for results
            print("Waiting for search results...")
            await page.wait_for_timeout(10000)
            await page.wait_for_selector('div.s-main-slot', timeout=180000)

            # Extract product URLs
            products = await page.query_selector_all('div.s-main-slot div[data-component-type="s-search-result"]')
            print(f"Found {len(products)} products.")
            product_urls = []
            for product in products:
                url_element = await product.query_selector("a.a-link-normal.s-line-clamp-2.s-link-style.a-text-normal")
                product_url = await url_element.get_attribute("href") if url_element else None
                if product_url:
                    product_urls.append(f"https://www.amazon.com{product_url}")

            print("\nExtracted Product URLs:")
            for idx, url in enumerate(product_urls, start=1):
                print(f"{idx}. {url}")

            # Step 2: Extract product data
            products_data = []
            for idx, product_url in enumerate(product_urls):
                print(f"\nNavigating to product page {idx + 1}/{len(product_urls)}: {product_url}")
                product_page = await context.new_page()
                try:
                    await product_page.goto(product_url, timeout=60000)

                    title_element = await product_page.query_selector("span#productTitle")
                    title = await title_element.text_content() if title_element else "No title found"

                    price_element = await product_page.query_selector("span.a-price > span.a-offscreen")
                    price = await price_element.text_content() if price_element else "Price not available"

                    price_numeric = None
                    if price != "Price not available":
                        try:
                            price_numeric = float(price.replace("$", "").replace(",", ""))
                        except ValueError:
                            price_numeric = None

                    rating_element = await product_page.query_selector("span.a-icon-alt")
                    rating = await rating_element.text_content() if rating_element else "No rating found"

                    reviews_element = await product_page.query_selector("span#acrCustomerReviewText")
                    reviews = await reviews_element.text_content() if reviews_element else "No reviews found"

                    availability_element = await product_page.query_selector("div#availability span.a-size-medium.a-color-success")
                    availability = await availability_element.text_content() if availability_element else "Availability not found"

                    product_data = {
                        "title": title.strip(),
                        "price": price.strip(),
                        "price_numeric": price_numeric,
                        "rating": rating.strip(),
                        "reviews": reviews.strip(),
                        "availability": availability.strip(),
                        "url": product_url,
                    }
                    products_data.append(product_data)

                    print("\nExtracted Data:")
                    for key, value in product_data.items():
                        print(f"  {key.capitalize()}: {value}")

                except Exception as e:
                    print(f"⚠️ Error extracting product {idx + 1}: {e}")
                finally:
                    await product_page.close()

            print("\n✅ Final Scraped Data:")
            for idx, product in enumerate(products_data, start=1):
                print(f"\nProduct {idx}/{len(products_data)}:")
                for key, value in product.items():
                    print(f"  {key.capitalize()}: {value}")

            return products_data

    except Exception as e:
        print(f"❌ Error during scraping process: {e}")

    finally:
        if browser:
            print("Closing the browser...")
            await browser.close()


# ✅ If executed as a script
if __name__ == "__main__":
    asyncio.run(scrape_amazon("LUDOS Clamor 2 PRO Wired Earbuds"))
