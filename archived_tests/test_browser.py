from playwright.async_api import async_playwright
import asyncio

async def test_playwright_navigation():
    """Test Playwright browser initialization and navigation to Amazon."""
    print("Launching the browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Make sure it's visible
        page = await browser.new_page()
        try:
            print("Navigating to Amazon homepage...")
            await page.goto("https://www.amazon.com", timeout=60000)
            await page.wait_for_timeout(5000)  # Wait for 5 seconds to observe
            print("Amazon navigation successful!")
        except Exception as e:
            print(f"Navigation error: {e}")
        finally:
            print("Closing the browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_playwright_navigation())
