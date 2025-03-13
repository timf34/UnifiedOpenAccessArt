#!/usr/bin/env python3
"""
Test script for fetching MoMA images with different methods.
"""

import requests
from PIL import Image
from io import BytesIO
import time
import re
import json
import base64
import os
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_selenium():
    """Setup Selenium WebDriver with Chrome"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Create a new Chrome driver instance
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_artwork_id(url):
    """Extract artwork ID from MoMA image URL."""
    try:
        # Extract the base64 encoded part (before the .jpg)
        encoded_part = url.split('/')[-1].split('.')[0]
        # Decode and parse
        decoded = base64.b64decode(encoded_part + '=' * (-len(encoded_part) % 4)).decode('utf-8')
        # Extract the ID using regex
        match = re.search(r'"(\d+)"', decoded)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error extracting ID from base64: {e}")
    return None

def save_image(image_data, artwork_id, cache_dir='image_cache'):
    """Save image to cache directory"""
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    file_path = os.path.join(cache_dir, f"{artwork_id}.jpg")
    with open(file_path, 'wb') as f:
        f.write(image_data)
    return file_path

def test_fetch_methods(url):
    """Try different methods to fetch the image."""
    print(f"\nTesting URL: {url}")
    
    artwork_id = extract_artwork_id(url)
    print(f"Extracted artwork ID: {artwork_id}")
    
    if not artwork_id:
        print("Could not extract artwork ID")
        return
    
    # Check cache first
    cache_dir = 'image_cache'
    cache_path = os.path.join(cache_dir, f"{artwork_id}.jpg")
    if os.path.exists(cache_path):
        print(f"Found cached image at {cache_path}")
        return
    
    # Method 1: Try using Selenium
    print("\nMethod 1: Using Selenium to bypass Cloudflare")
    try:
        driver = setup_selenium()
        
        # First visit the artwork page
        artwork_url = f'https://www.moma.org/collection/works/{artwork_id}'
        print(f"Visiting artwork page: {artwork_url}")
        driver.get(artwork_url)
        
        # Wait for the page to load and Cloudflare challenge to complete
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.picture__img"))
        )
        
        # Get cookies from selenium
        cookies = driver.get_cookies()
        
        # Create a new session with selenium cookies
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        
        # Try to fetch the image with the cookies
        headers = {
            'User-Agent': driver.execute_script("return navigator.userAgent"),
            'Accept': 'image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': artwork_url,
        }
        
        print("Fetching image with Selenium cookies...")
        response = session.get(url, headers=headers)
        response.raise_for_status()
        
        # Save the image to cache
        saved_path = save_image(response.content, artwork_id)
        print(f"Successfully downloaded and cached image to {saved_path}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Length: {len(response.content)} bytes")
        
    except Exception as e:
        print(f"Failed: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()

def main():
    # Test URL
    test_url = "https://www.moma.org/media/W1siZiIsIjUyNzUyMCJdLFsicCIsImNvbnZlcnQiLCItcmVzaXplIDEwMjR4MTAyNFx1MDAzZSJdXQ.jpg?sha=d172aa966e03ed80"
    test_fetch_methods(test_url)

if __name__ == "__main__":
    main() 