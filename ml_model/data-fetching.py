# This file will contain data fetching and preprocessing before passing on to the model.

# Imports
import re
import winreg
import time
import pprint
import pandas as pd
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Get the latest chrome version using the Windows Registry
def get_chrome_version():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"
        )
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    # If file was not found, return None
    except FileNotFoundError:
        return None


# Check the title if it has the necessary details: CPU, GPU, RAM, Storage
def evaluate_title(product_title):
    title = product_title.lower()

    # CPU patterns
    cpu_patterns = [
        r"i[3579]-?\d{3,5}[kKFf]?",  # i7-14700KF, i5-9600k
        r"i[3579]\s?\d?(?:th)?\s?gen",  # i7 8th gen, i5 7th gen
        r"ryzen\s?\d{1,2}\s?\d{3,4}?",  # ryzen 5, ryzen 9, ryzen 7 8700f
        r"\b(m[1234])\b",  # Apple M1, M2, M3, M4
        r"ultra\s?\d",  # Intel Ultra 7, Ultra 9
        r"\b\d{4,5}x3d\b",  # e.g. 9800x3d, 9950x3d
    ]

    # GPU patterns
    gpu_patterns = [
        r"rtx\s?\d{3,4}",  # RTX 3060, RTX4070
        r"gtx\s?\d{3,4}",  # GTX 1660, GTX1080
        r"geforce\s?(rtx|gtx)?\s?\d{3,4}",  # Geforce GTX 1080
        r"radeon\s?(rx)?\s?\d{3,5}",  # Radeon RX 6800
        r"rx\s?\d{3,5}",  # RX 570, RX 7900
        r"arc\s?\w+",  # Intel Arc A770
        r"iris\s?(pro|plus|xe)?\s?\d*",  # Iris Pro/Plus/Xe
    ]

    # RAM patterns
    ram_patterns = [
        r"\b\d{1,3}\s?gb\s?ram\b",  # 16gb ram, 32 gb ram
        r"\b\d{1,3}\s?gb\b",  # 64gb, 32 gb
    ]

    # Storage patterns
    storage_patterns = [
        r"\b\d{3,4}\s?gb\s?(ssd|hdd|nvme)\b",  # 512gb ssd, 500gb hdd
        r"\b\d+\s?t\b\s?(ssd|hdd|nvme)\b",  # 1t ssd, 2t hdd
        r"\b(\d+x)?\d+\s?tb\s?(ssd|hdd|nvme)\b",  # 2tb ssd, 5tb hdd, 2x2tb hdd
    ]

    # For each regex pattern in the patterns list given, check if the pattern is within the text.
    def match_any(patterns, text):
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    results = {
        "cpu": match_any(cpu_patterns, title),
        "gpu": match_any(gpu_patterns, title),
        "ram": match_any(ram_patterns, title),
        "storage": match_any(storage_patterns, title),
    }

    # A "valid" title must have a CPU, GPU, Ram, and Storage
    results["is_valid"] = all(
        [results["cpu"], results["gpu"], results["ram"], results["storage"]]
    )

    return results


# Handles products that have a price range.
def extract_prices(data, details, product_title):
    min_price = float(data[0].replace("$", "").replace(",", ""))
    max_price = float(data[-1].replace("$", "").replace(",", ""))

    details[product_title] = {
        "min_price": min_price,
        "max_price": max_price,
    }

    return details


# Extract the product title and price
def parse_data(data):
    product_details = {}

    for product in data:
        # Find the element holding the product title
        product_title = product.find_element(
            By.CSS_SELECTOR, "div.s-card__title, div.s-item__title"
        )
        # Find the element holding the price(s).
        product_prices = product.find_elements(
            By.CSS_SELECTOR, "span.s-card__price, span.s-item__price"
        )

        # If title or price was not found, continue to the next product.
        if not product_title or not product_prices:
            continue

        product_title = product_title.text.strip()
        if product_title in product_details:
            continue
        # Evaluate title
        title_result = evaluate_title(product_title=product_title)

        # If the title is not valid, move on to the next product
        if not title_result["is_valid"]:
            continue

        product_prices = [price.text.strip() for price in product_prices]

        # Handle products that have a price range.
        if len(product_prices) > 1:
            product_details = extract_prices(
                product_prices, product_details, product_title
            )

        # Handle products that have a price range.
        elif "to" in product_prices[0]:
            product_price_range = [
                price for price in product_prices[0].split() if price != "to"
            ]
            product_details = extract_prices(
                product_price_range, product_details, product_title
            )
        else:
            product_price = float(product_prices[0].replace("$", "").replace(",", ""))
            product_details[product_title] = {"price": product_price}

    return product_details


def fetch_data(driver, max_retries=3, wait_time=15):

    products = list()

    for attempt in range(1, max_retries + 1):
        try:  # Grab the elements containing the products information

            # Find the list of products. Wait until the element is fully loaded and save it
            # Wait for results container
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul.srp-results.srp-list")
                )
            )
            # Wait for at least 1 item to be visible
            WebDriverWait(driver, wait_time).until(
                EC.visibility_of_any_elements_located(
                    (By.CSS_SELECTOR, "li[data-viewport]")
                )
            )

            # Fetch all items
            products = driver.find_elements(By.CSS_SELECTOR, "li[data-viewport]")

            break

        except (
            TimeoutException
        ):  # If the code times out, rerun unless max attempts exceeded.
            print(f"Attempt {attempt} timed out. Retrying...")
            if attempt == max_retries:
                raise
            time.sleep(2)

    return products


def main():
    search_queries = [
        "gaming pc",
        "gaming computer",
        "custom pc",
        "gaming desktop",
        "gaming tower",
    ]
    page_number = 200

    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    chrome_version = get_chrome_version()

    # Launch Chrome
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_version).install()),
        options=options,
    )

    # Load page

    MAX_RETRIES = 5
    WAIT_TIME = 30

    product_details = {}
    for query in search_queries:
        for page in range(1, page_number + 1):
            print(f"Scraping page {page}...")
            base_url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}&_pgn={page}"
            driver.get(base_url)
            products = fetch_data(
                driver=driver,
                max_retries=MAX_RETRIES,
                wait_time=WAIT_TIME,
            )
            product_details.update(parse_data(data=products))
            print(f"Total items found and added: {len(product_details)}")

    driver.quit()

    with open("ml_model/data/products.txt", "w", encoding="utf-8") as f:
        json.dump(product_details, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
