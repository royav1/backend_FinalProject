import requests
from bs4 import BeautifulSoup

# Define API key and base URL for ScraperAPI
API_KEY = '255e14a44271ef5610a6c0856d72b11b'
BASE_URL = 'https://api.scraperapi.com/'

def get_amazon_product_name(url, session_number="1231233"):
    # Set up request payload
    payload = {
        'api_key': API_KEY,
        'url': url,
        'country_code': 'us',
        'device_type': 'desktop',
        'session_number': session_number
    }

    # Send GET request to ScraperAPI
    response = requests.get(BASE_URL, params=payload)

    # Check if request was successful
    if response.status_code == 200:
        print("Request successful!")
        
        # Parse the HTML response using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the product title by its unique ID
        product_title = soup.find("span", {"id": "productTitle"})
        if product_title:
            product_name = product_title.get_text(strip=True)
            return product_name
        else:
            print("Product title element not found.")
            return None
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None

# Example usage with specific Amazon product URL
if __name__ == "__main__":
    amazon_product_url = "https://www.amazon.com/ACEMAGIC-15-6In-Windows-Quad-12th-%D7%9E%D7%99%D7%A7%D7%A8%D7%95%D7%A4%D7%95%D7%9F/dp/B0DFG63QNT/ref=sr_1_1_sspa?crid=3IRID06MZOC3P&dib=eyJ2IjoiMSJ9.Wj_BG9siK3wyPk51VSexRe-k0__0ALWwezBoPyugPX-7JaP6qGWw-v1unLXa3AkthBJHSdHuzMRtisnuffQD__8Dm_-bMBeD8s1BGr92ssf7vM39F19H5hNvjrrJTtAuh_uZhj5oN25wS9_efxcdRpH0Rnyo87FMdOHMNB28T4iyP_qnnt4a0Cc-XfumuPW5tWDBQ3u4mgvrMXwbNbdc1f4WdjXGiI3qZRQAPO9hed4.0VkPOkwMRvMAYf26uw8wkI2cYoIYM1PxfDWNUDdoDDI&dib_tag=se&keywords=laptop&qid=1729954926&sprefix=%2Caps%2C178&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1"
    session_number = "1231233"  # Choose a session number to simulate session consistency
    
    # Get product name and print it
    product_name = get_amazon_product_name(amazon_product_url, session_number)
    print(f"Product Name: {product_name}")
