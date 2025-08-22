# This file will contain data fetching and preprocessing before passing on to the model.

# Imports
import winreg
import json
import time
import pprint

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


def extract_prices(data, details, product_title):
    min_price = float(data[0].replace("$", "").replace(",", ""))
    max_price = float(data[-1].replace("$", "").replace(",", ""))

    details[product_title] = {
        "min_price": min_price,
        "max_price": max_price,
    }

    return details


def parse_data(data):
    product_details = {}

    for product in data:
        product_title = product.find_element(
            By.CSS_SELECTOR, "div.s-card__title, div.s-item__title"
        )
        product_prices = product.find_elements(
            By.CSS_SELECTOR, "span.s-card__price, span.s-item__price"
        )

        if not product_title:
            continue
        product_title = product_title.text.strip()
        if not product_title:
            continue
        if not product_prices:
            continue

        product_prices = [price.text.strip() for price in product_prices]

        if len(product_prices) > 1:
            product_details = extract_prices(
                product_prices, product_details, product_title
            )

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


def wait_until_stable(driver, css_container, css_items, wait_time=20, stable_time=3):
    last_count = -1
    stable_for = 0
    end_time = time.time() + wait_time
    while time.time() < end_time:
        try:
            container = driver.find_element(By.CSS_SELECTOR, css_container)
            items = container.find_elements(By.CSS_SELECTOR, css_items)
            current_count = len(items)
        except Exception:
            current_count = 0  # if container not ready yet

        if current_count == last_count:
            stable_for += 1
            if stable_for >= stable_time:
                return items
        else:
            stable_for = 0
            last_count = current_count

        time.sleep(1)

    raise TimeoutException("Products did not stabilize in time")


def main():
    search_queries = ["gaming pc", "gaming computer", "custom_pc"]
    page_number = 1

    base_url = f"https://www.ebay.com/sch/i.html?_nkw={search_queries[0].replace(' ', '+')}&_pgn={page_number}"

    options = Options()
    options.add_argument("--headless")
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
    driver.get(base_url)

    MAX_RETRIES = 5
    WAIT_TIME = 20

    products = list()

    for attempt in range(1, MAX_RETRIES + 1):
        try:  # Grab the elements containing the products information

            # Find the list of products. Wait until the element is fully loaded and save it
            # Wait for results container
            WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul.srp-results.srp-list")
                )
            )
            # Wait for at least 1 item to be visible
            WebDriverWait(driver, WAIT_TIME).until(
                EC.visibility_of_any_elements_located(
                    (By.CSS_SELECTOR, "li[data-viewport]")
                )
            )

            # Fetch all items
            products = driver.find_elements(By.CSS_SELECTOR, "li[data-viewport]")
            # products = wait_until_stable(
            #     driver,
            #     "ul.srp-results.srp-list",
            #     "li[data-viewport]",
            #     wait_time=WAIT_TIME,
            # )

            break

        except (
            TimeoutException
        ):  # If the code times out, rerun unless max attempts exceeded.
            print(f"Attempt {attempt} timed out. Retrying...")
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2)

    product_details = parse_data(data=products)
    pprint.pprint(product_details)
    print(len(product_details))
    # print(len(product_details))

    # print(product_details)

    driver.quit()
    # key: value pair = product title: product price

    # for child in items.find_all(
    #     lambda tag: tag.name == "li" and tag.has_attr("data-viewport")
    # ):
    #     # print(child)
    #     item_title = child.find("div", {"class": "s-card__title"})

    #     if not item_title:
    #         # Skip this product
    #         continue

    #     item_title_text = item_title.text
    #     item_attribute = child.find("div", {"class": "s-card__attribute-row"})

    #     if not item_attribute:
    #         continue

    #     item_price = item_attribute.find_all("span", {"class": "s-card__price"})
    #     item_price_text = [item.text for item in item_price]
    #     max_price = item_price_text.pop()
    #     max_price_flt = float(max_price.replace("$", "").replace(",", ""))

    #     product_details[item_title_text] = max_price_flt
    #     # Each child should be the different items found from the search query.

    # print(product_details)


if __name__ == "__main__":
    main()
