import os
import sys
import random
import tempfile
from datetime import timedelta  # Retained because it's used
from django.utils import timezone  # Used for time handling
from playwright.async_api import async_playwright
from amazoncaptcha import AmazonCaptcha
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from base.models import TrackedProduct, PriceHistory
from decimal import Decimal, InvalidOperation


# Set up Django environment
import django
sys.path.append("..")  # Adjust to your project's base directory
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproj.settings")  # Update with the correct path to your settings
django.setup()

# Import Django models and other modules after Django setup
from django.contrib.auth.models import User  # Import User model to retrieve superuser
from base.models import TrackedProduct, PriceHistory  # Import the models

# Dictionary to store tracked products by their full name
# tracked_products = {}

async def scrape_amazon(search_query, user_id=None, single_page=False, scheduled_scraping=False):
    """
    Scrape Amazon for the given search query.
    Save all products into the general TrackedProduct list associated with the user performing the scrape.
    """
    # Default to superuser if no user_id is provided
    user = await sync_to_async(User.objects.filter(is_superuser=True).first)()
    if user_id:
        user = await sync_to_async(User.objects.get)(id=user_id)

    print(f"Scraping Amazon for user: {user.username} (ID: {user.id})")
    async with async_playwright() as p:
        # Launch the browser in headful mode
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

        # Simulate cookies and session persistence to help evade CAPTCHA
        await context.add_cookies([
            {"name": "session-id", "value": "133-1234567-1234567", "domain": ".amazon.com", "path": "/"},
            {"name": "session-id-time", "value": "2082787201l", "domain": ".amazon.com", "path": "/"},
            {"name": "ubid-main", "value": "133-1234567-1234567", "domain": ".amazon.com", "path": "/"},
            {"name": "x-main", "value": "x-main-cookie-value", "domain": ".amazon.com", "path": "/"}
        ])

        # Set custom timeouts
        context.set_default_navigation_timeout(30000)
        context.set_default_timeout(30000)

        page = await context.new_page()
        await page.goto("https://www.amazon.com")
        await page.wait_for_timeout(random.uniform(2000, 5000))  # Delay for 2-5 seconds

        # Attempt CAPTCHA solving up to 10 times
        for attempt in range(10):
            if await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                print(f"CAPTCHA detected, attempting to solve... (Attempt {attempt + 1}/10)")
                # Capture the CAPTCHA image and save it to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
                    captcha_image_path = temp_img.name
                    await page.locator("div.a-row.a-text-center img").screenshot(path=captcha_image_path)
                try:
                    # Attempt to solve the CAPTCHA
                    solver = AmazonCaptcha(captcha_image_path)
                    captcha_solution = solver.solve()
                    # Verify CAPTCHA solution length before submission
                    if len(captcha_solution) == 6:
                        await page.fill("input#captchacharacters", captcha_solution.strip())
                        await page.click("button[type='submit']")
                        await page.wait_for_load_state('networkidle')
                        # Check if the CAPTCHA was resolved successfully
                        if not await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                            print("CAPTCHA solved.")
                            break
                    else:
                        print("Failed CAPTCHA solution attempt, trying a new image.")
                    # Retry with a new CAPTCHA image
                    await page.locator("a:has-text('Try different image')").click()
                    await page.wait_for_timeout(2000)
                finally:
                    # Clean up the temporary file
                    os.remove(captcha_image_path)
            else:
                print("No CAPTCHA detected.")
                break
        else:
            # If all attempts fail, wait for manual CAPTCHA solution
            print("Manual CAPTCHA solving required. Please solve the CAPTCHA in the browser to proceed.")
            while await page.is_visible("div.a-section > div.a-box > div.a-box-inner"):
                await page.wait_for_timeout(1000)  # Wait until CAPTCHA is solved manually

        try:
            # Perform the search
            search_bar_selector = 'input[name="field-keywords"]'
            await page.fill(search_bar_selector, search_query)
            await page.press(search_bar_selector, "Enter")
            await page.wait_for_timeout(random.uniform(3000, 6000))  # Delay for human-like behavior

            scraped_products = []  # Initialize list to store product data
        except Exception as e:
            print(f"Error accessing search bar: {e}")
            await browser.close()
            return 

        scraped_products = []  # List to store all scraped products
        current_page = 1
        max_pages = 3  # Scrape up to 3 pages
        product_counter = 0  # Initialize product counter

        while current_page <= max_pages:
            print(f"Scraping page {current_page}...")

            try:
                # Wait for the main slot to load
                await page.wait_for_selector('div.s-main-slot', timeout=60000)
                await page.wait_for_timeout(random.uniform(2000, 5000))  # Delay to simulate human behavior

                # Extract product information
                products = await page.query_selector_all('div.s-main-slot div[data-component-type="s-search-result"]')
                for product in products:
                    try:
                        # Extract title
                        title_element = await product.query_selector("h2")
                        title = None

                        if title_element:
                            # Check if the h2 element has an aria-label attribute (likely contains the full title)
                            aria_label = await title_element.get_attribute("aria-label")
                            if aria_label:
                                title = aria_label.strip()
                            else:
                                # If aria-label is not present, combine all span elements under h2
                                span_elements = await title_element.query_selector_all("span")
                                title = " ".join([await span.text_content() for span in span_elements if span]).strip()

                        # Handle "Sponsored Ad -" prefix
                        if title and title.startswith("Sponsored Ad -"):
                            title = title.replace("Sponsored Ad -", "").strip()

                        # Default fallback if no title is found
                        if not title:
                            title = "No title found"

                        # Extract and clean price
                        price_symbol = await product.query_selector("span.a-price-symbol")
                        price_whole = await product.query_selector("span.a-price-whole")
                        price_fraction = await product.query_selector("span.a-price-fraction")
                        symbol = await price_symbol.text_content() if price_symbol else ""
                        price = (
                            f"{symbol}{await price_whole.text_content()}.{await price_fraction.text_content()}"
                            if price_whole and price_fraction else "0.00"
                        )
                        price = price.replace('..', '.')
                        try:
                            price_numeric = Decimal(price.replace("$", "").replace(",", "").strip())
                        except (InvalidOperation, ValueError):
                            price_numeric = None

                        # Extract rating and reviews
                        rating_element = await product.query_selector("span.a-icon-alt")
                        rating = float((await rating_element.text_content()).split()[0]) if rating_element else None
                        reviews_element = await product.query_selector("span.a-size-base.s-underline-text")
                        reviews = int((await reviews_element.text_content()).replace(",", "")) if reviews_element else None

                        # Retrieve product link
                        link_element = await product.query_selector("a.a-link-normal")
                        product_link = f"https://www.amazon.com{await link_element.get_attribute('href')}" if link_element else None

                        # Debugging: Log product details
                        print(f"{product_counter}. Product: {title}\n   Price: {price_numeric}\n   Rating: {rating}\n   Reviews: {reviews}\n   Link: {product_link}\n")

                        # Append product to the scraped_products list
                        scraped_products.append({
                            "title": title,
                            "price": price_numeric,
                            "rating": rating,
                            "reviews": reviews,
                            "link": product_link,
                        })
                        product_counter += 1

                    except Exception as e:
                        print(f"Error extracting product details: {e}")
                        continue
                
                if single_page:
                    break

                # Navigate to the next page
                next_button = await page.query_selector("a.s-pagination-item.s-pagination-next")
                if next_button:
                    next_page_url = await next_button.get_attribute("href")
                    await page.goto(f"https://www.amazon.com{next_page_url}")
                    current_page += 1
                else:
                    print("No more pages found.")
                    break

            except Exception as e:
                print(f"Error scraping product data on page {current_page}: {e}")
                break
        
        if scheduled_scraping:
            await browser.close()
            return scraped_products

        await select_product_for_tracking(scraped_products, context, user.id)
        await browser.close()


async def select_product_for_tracking(tracked_products, context, user_id=None):
    """Allow users to select specific products from scraped results and add them to the tracking list."""
    
    # Ensure user association
    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
    except User.DoesNotExist:
        print(f"Error: User with ID {user_id} does not exist.")
        return
    except Exception as e:
        print(f"Unexpected error while fetching user: {e}")
        return

    while True:
        # Prompt user to select a product
        selection = input("Enter the product number to track (or 'done' to finish): ")
        if selection.lower() == 'done':
            print("Exiting product selection...")
            break

        try:
            selected_index = int(selection)

            if 0 <= selected_index < len(tracked_products):
                product_data = tracked_products[selected_index]
                product_link = product_data.get("link")

                # Initialize availability
                availability = "Unknown"

                # Fetch product availability if a link exists
                if product_link:
                    try:
                        product_page = await context.new_page()
                        await product_page.goto(product_link)
                        availability_container = await product_page.query_selector("#availability")

                        if availability_container:
                            in_stock_element = await availability_container.query_selector("span.a-size-medium.a-color-success")
                            warning_element = await availability_container.query_selector("span.a-size-base.a-color-price.a-text-bold")
                            
                            if in_stock_element:
                                availability = await in_stock_element.text_content()
                            elif warning_element:
                                availability = await warning_element.text_content()
                            else:
                                availability = "Not available"
                        else:
                            availability = "No availability info"
                    except Exception as e:
                        print(f"Error fetching availability: {e}")
                    finally:
                        await product_page.close()

                # Get the current local time (GMT+2) without microseconds
                current_time = (timezone.now() + timedelta(hours=2)).replace(microsecond=0)

                try:
                    # Check if product already exists
                    tracked_product = await sync_to_async(TrackedProduct.objects.filter)(
                        title=product_data["title"], user=user
                    )
                    tracked_product = await sync_to_async(tracked_product.first)()

                    if tracked_product:
                        # Update existing tracked product
                        tracked_product.price = product_data["price"]
                        tracked_product.rating = product_data["rating"]
                        tracked_product.reviews = product_data["reviews"]
                        tracked_product.availability = availability
                        tracked_product.date_scraped = current_time
                        await sync_to_async(tracked_product.save)()
                        print(f"Updated tracked product: {product_data['title']} - Availability: {availability}")
                    else:
                        # Create a new tracked product
                        tracked_product = await sync_to_async(TrackedProduct.objects.create)(
                            title=product_data["title"],
                            price=product_data["price"],
                            rating=product_data["rating"],
                            reviews=product_data["reviews"],
                            availability=availability,
                            date_scraped=current_time,
                            user=user,
                        )
                        print(f"Tracked product added: {product_data['title']} - Availability: {availability}")

                    # Add a price history entry for the product
                    await sync_to_async(PriceHistory.objects.create)(
                        product=tracked_product,
                        price=product_data["price"],
                        availability=availability,
                        date_recorded=current_time,
                    )
                    print(f"Price history entry added for: {product_data['title']} - Availability: {availability}")
                except Exception as e:
                    print(f"Error saving product data: {e}")
            else:
                print("Invalid selection. Please select a valid product number.")
        except ValueError:
            print("Please enter a valid number.")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    import asyncio
    search_query = input("Enter your search query: ")
    asyncio.run(scrape_amazon(search_query))  # Standalone run with no user association




    