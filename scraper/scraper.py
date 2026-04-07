import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
import re

URLS = [
    {"country": "DE", "url": "https://support.tiktok.com/de/business-and-creator/creator-rewards-program/creator-rewards-program"},
    {"country": "FR", "url": "https://support.tiktok.com/fr/business-and-creator/creator-rewards-program/creator-rewards-program"},
    {"country": "US", "url": "https://www.tiktok.com/creator-academy/article/creator-rewards-program"}
]

async def scrape_url(pw, item):
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    page = await context.new_page()
    try:
        await page.goto(item["url"], wait_until="load", timeout=60000)
        
        content = ""
        selectors = ["article", "main", "[class*='content']", "body"]
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    text = await elem.inner_text()
                    if text and text.strip():
                        content = text
                        break
            except Exception:
                continue
                
        content = re.sub(r'\s+', ' ', content).strip()
        
        return {
            "country": item["country"],
            "url": item["url"],
            "content": content,
            "scraped_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error scraping {item['country']}: {e}")
        return {
            "country": item["country"],
            "url": item["url"],
            "content": "",
            "scraped_at": datetime.utcnow().isoformat()
        }
    finally:
        await browser.close()

async def scrape_all():
    async with async_playwright() as pw:
        tasks = [scrape_url(pw, item) for item in URLS]
        results = await asyncio.gather(*tasks)
        return results
