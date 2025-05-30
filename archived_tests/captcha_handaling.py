import time
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from PIL import Image
import pytesseract
from io import BytesIO

def preprocess_image(image):
    """Convert the image to grayscale and apply thresholding."""
    return image.convert('L').point(lambda x: 0 if x < 200 else 255)

def solve_captcha(captcha_url):
    try:
        # Download the CAPTCHA image
        response = requests.get(captcha_url)
        response.raise_for_status()  # Raise an error for bad responses
        image = Image.open(BytesIO(response.content))

        # Preprocess the image before using Tesseract
        processed_image = preprocess_image(image)

        # Use Tesseract to extract text from the processed image
        captcha_text = pytesseract.image_to_string(processed_image).strip()
        return captcha_text
    except Exception as e:
        print(f"Error solving CAPTCHA: {e}")
        return None

def scrape_amazon():
    # Initialize the WebDriver with undetected-chromedriver
    driver = uc.Chrome()

    # Navigate to Amazon's CAPTCHA page
    driver.get("https://www.amazon.com/errors/validateCaptcha")

    # Wait for a few seconds to allow any CAPTCHA to load
    time.sleep(random.uniform(10, 20))

    # Take a screenshot for debugging
    driver.save_screenshot('amazon_debug.png')

    # Look for the CAPTCHA image directly
    try:
        captcha_image = driver.find_element(By.XPATH, "//div[@class='a-row a-text-center']//img")
        captcha_url = captcha_image.get_attribute('src')  # Get the CAPTCHA image URL

        if captcha_url:
            print(f"CAPTCHA URL: {captcha_url}")
            # Solve the CAPTCHA
            captcha_value = solve_captcha(captcha_url)

            if captcha_value:
                # Print the recognized CAPTCHA value
                print(f"Recognized CAPTCHA text: {captcha_value}")

                # Fill in the CAPTCHA input and submit
                driver.find_element(By.ID, "captchacharacters").send_keys(captcha_value)
                driver.find_element(By.CLASS_NAME, "a-button-primary").click()  # Submit button
            else:
                print("Failed to recognize CAPTCHA text.")
        else:
            print("CAPTCHA URL is not available.")

    except Exception as e:
        print("Error locating CAPTCHA image:", e)

    # Wait to see the result (optional)
    time.sleep(30)

    # Close the driver
    driver.quit()

if __name__ == "__main__":
    scrape_amazon()
