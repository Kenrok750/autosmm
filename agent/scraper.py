import logging
import time
from playwright.sync_api import Page, TimeoutError

logger = logging.getLogger(__name__)

def scrape_wb_products(page: Page, seller_url: str, max_items: int = 10) -> list[dict]:
    """
    Navigates to a Wildberries seller page and extracts product links and titles.
    """
    logger.info(f"Начинаем парсинг товаров продавца: {seller_url}")
    products = []

    try:
        page.goto(seller_url, timeout=60000)

        # Wait for the product cards to load. Wildberries uses various classes,
        # usually 'product-card' or similar. We will wait for article elements or links containing '/catalog/'.
        logger.info("Ожидание загрузки карточек товаров...")

        # We give it some time to load, handle possible captchas manually if visible.
        # Streamlit users will see the browser if headless=False.
        time.sleep(5)

        try:
            # Try to wait for at least one product card link
            page.wait_for_selector("a[href*='/catalog/']", timeout=15000)
        except TimeoutError:
            logger.warning("Товары не найдены за 15 секунд. Возможно, на странице капча или изменился дизайн.")

        # Extract links
        # Find all anchor tags that point to a catalog detail page
        link_elements = page.locator("a[href*='/catalog/']").all()

        seen_urls = set()

        for el in link_elements:
            if len(products) >= max_items:
                break

            try:
                href = el.get_attribute("href")
                if not href:
                    continue

                # Clean up URL
                if href.startswith("/"):
                    full_url = f"https://www.wildberries.ru{href}"
                else:
                    full_url = href

                # Remove query parameters for cleaner comparison
                base_url = full_url.split("?")[0]

                if base_url in seen_urls:
                    continue

                # Try to get the title from aria-label or inner text
                title = el.get_attribute("aria-label")
                if not title:
                     # Fallback to looking for a text element inside the card
                     # WB usually puts the brand and name in spans
                     text = el.inner_text().strip()
                     title = text.replace('\n', ' ')[:50] + "..." if text else "Товар без названия"

                seen_urls.add(base_url)
                products.append({
                    "title": title,
                    "url": full_url
                })

            except Exception as e:
                logger.debug(f"Ошибка при парсинге одного из товаров: {e}")

    except Exception as e:
        logger.error(f"Критическая ошибка при парсинге страницы продавца: {e}")

    logger.info(f"Спарсено {len(products)} уникальных товаров.")
    return products
