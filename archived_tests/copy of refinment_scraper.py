import os
import random
import tempfile
from playwright.async_api import async_playwright
from amazoncaptcha import AmazonCaptcha
from rapidfuzz import fuzz
import asyncio


async def scrape_hardcoded_product():
    """Scrape Amazon for a hardcoded product query."""
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

            # Set custom timeouts
            context.set_default_navigation_timeout(60000)
            context.set_default_timeout(60000)

            # Create a new page
            page = await context.new_page()

            # Navigate to Amazon homepage
            print("Navigating to Amazon homepage...")
            await page.goto("https://www.amazon.com", timeout=60000)
            await page.wait_for_timeout(random.uniform(3000, 7000))

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
                            await page.wait_for_timeout(2000)
                    finally:
                        os.remove(captcha_image_path)
                else:
                    print("No CAPTCHA detected.")
                    break
            else:
                print("Manual CAPTCHA solving required. Please solve it in the browser.")
                while await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                    await page.wait_for_timeout(1000)

           # Perform a hardcoded search
            search_query = "LUDOS Clamor 2 PRO Wired Earbuds"
            print(f"Searching for: {search_query}")

            search_bar_selector = 'input#twotabsearchtextbox'
            await page.fill(search_bar_selector, search_query)
            await page.press(search_bar_selector, "Enter")

            # Wait for results to load
            print("Waiting after search...")
            await page.wait_for_timeout(5000)
            await page.wait_for_selector('div.s-main-slot')

            # Scrape product data
            products = await page.query_selector_all('div.s-main-slot div[data-component-type="s-search-result"]')
            print(f"Number of products found: {len(products)}")

            best_match = None
            best_score = 0
            product_links = []  # Store product URLs for later navigation

            for product in products:
                try:
                    # Extract title
                    title_element = await product.query_selector("h2[aria-label]") or await product.query_selector("h2 > a > span")
                    title = await title_element.get_attribute("aria-label") if title_element else None
                    if not title and title_element:
                        title = await title_element.text_content()

                    # Remove "Sponsored Ad -" prefix
                    if title and title.startswith("Sponsored Ad -"):
                        title = title.replace("Sponsored Ad -", "").strip()

                    # Extract price
                    price_element = await product.query_selector("span.a-price > span.a-offscreen")
                    price = await price_element.text_content() if price_element else "Price not available"

                    # Extract numeric price
                    price_numeric = None
                    if price != "Price not available":
                        try:
                            price_numeric = float(price.replace("$", "").replace(",", ""))
                        except ValueError:
                            price_numeric = None

                    # Extract rating
                    rating_element = await product.query_selector("span.a-icon-alt")
                    rating = (await rating_element.text_content()).strip() if rating_element else None

                    print("Checking for reviews block...")

                    # Wait for the reviews block to load
                    reviews_block = await product.query_selector('[data-cy="reviews-block"]')

                    if reviews_block:
                        print("✅ Reviews block found.")

                        # Search for the <a aria-label> element inside the reviews block
                        reviews_a_element = await reviews_block.query_selector("a[aria-label]")

                        if reviews_a_element:
                            print("✅ Reviews <a aria-label> element found.")

                        # Search for the <span> that contains the review count
                        reviews_span = await reviews_block.query_selector("span.a-size-base.s-underline-text")

                        if reviews_span:
                            print("✅ Reviews <span> element found.")
                            reviews_text = await reviews_span.text_content()
                            reviews = int(reviews_text.replace(",", "").strip())  # Convert to integer and remove commas
                            print(f"✅ Reviews extracted: {reviews}")
                        else:
                            reviews = "Reviews <span> element not found"
                            print("❌ Reviews <span> element not found inside the block.")

                    else:
                        reviews = "Reviews block not found"
                        print("❌ Reviews block not found.")

                    # Extract product URL correctly
                    url_element = await product.query_selector("a.a-link-normal.s-line-clamp-2.s-link-style.a-text-normal")
                    product_url = await url_element.get_attribute("href") if url_element else None

                    if product_url:
                        product_url = f"https://www.amazon.com{product_url}"
                        product_links.append(product_url)  # Store for later navigation
                        print(f"Extracted Product URL: {product_url}")
                    else:
                        print("❌ Failed to extract product URL")
                        product_url = None

                    # Log the extracted values
                    print(f"Title: {title or 'No title found'}")
                    print(f"Price: {price} - Numeric Price: {price_numeric}")
                    print(f"Rating: {rating}")
                    print(f"Reviews: {reviews}")
                    print(f"Product URL: {product_url}")

                    # Calculate similarity score
                    similarity_score = fuzz.partial_ratio(search_query.lower(), title.lower()) if title else 0
                    print(f"Similarity Score: {similarity_score}")

                    # Update the best match if the score is higher
                    if similarity_score > best_score:
                        best_score = similarity_score
                        best_match = {
                            "title": title,
                            "price": price,
                            "price_numeric": price_numeric,
                            "rating": rating,
                            "reviews": reviews,
                            "availability": "Pending...",
                            "similarity_score": similarity_score,
                            "url": product_url
                        }

                except Exception as e:
                    print(f"Error extracting product data: {e}")

            # Now visit each product page to get availability
            for idx, product_url in enumerate(product_links):
                print(f"\nNavigating to product page {idx + 1}/{len(product_links)}: {product_url}")
                availability = await get_availability(page, product_url)
                print(f"✅ Extracted availability: {availability}")

            # Display the best match
            if best_match:
                print(f"\nBest Match: {best_match}")
            else:
                print("\nNo suitable match found.")

    except Exception as e:
        print(f"Error during scraping process: {e}")
    finally:
        if browser:
            print("Closing the browser...")
            await browser.close()


async def get_availability(page, product_url):
    """
    Extracts the availability status from the individual product page.
    """
    try:
        print(f"Navigating to product page: {product_url}")
        await page.goto(product_url, timeout=15000)

        # Wait for the availability section to load
        await page.wait_for_selector("div#availabilityInsideBuyBox_feature_div, div#availability", timeout=5000)

        # Extract availability text from multiple potential elements
        availability_selectors = [
            "div#availabilityInsideBuyBox_feature_div span.a-size-medium.a-color-success",
            "div#availability span.a-size-medium.a-color-success"
        ]

        availability = None
        for selector in availability_selectors:
            availability_element = await page.query_selector(selector)
            if availability_element:
                availability = await availability_element.text_content()
                availability = availability.strip()
                break  # Stop searching once we find the availability text

        if not availability:
            availability = "Availability not found"

        return availability

    except Exception as e:
        print(f"❌ Error extracting availability: {e}")
        return "Availability not available"


if __name__ == "__main__":
    asyncio.run(scrape_hardcoded_product())