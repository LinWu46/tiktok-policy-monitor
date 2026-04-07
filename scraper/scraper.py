import asyncio
from datetime import datetime, timezone
from playwright.async_api import async_playwright
import re

URLS = [
    {"country": "DE", "url": "https://support.tiktok.com/de/business-and-creator/creator-rewards-program/creator-rewards-program"},
    {"country": "FR", "url": "https://support.tiktok.com/fr/business-and-creator/creator-rewards-program/creator-rewards-program"},
    {"country": "US", "url": "https://www.tiktok.com/creator-academy/article/creator-rewards-program"}
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def clean_text(text):
    """Remove CSS, JS, JSON artifacts and normalize whitespace."""
    # Remove CSS blocks
    text = re.sub(r'\{[^}]*\}', ' ', text)
    # Remove common CSS/JS patterns
    text = re.sub(r'[\w-]+\s*:\s*[\w#,.\-%()\s]+;', ' ', text)
    # Remove URLs in code context
    text = re.sub(r'https?://\S+\.tsx?\b', ' ', text)
    # Remove JSON-like patterns
    text = re.sub(r'"[\w]+":\s*"[^"]*"', ' ', text)
    # Remove lines that look like code
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that look like code/CSS/JSON
        if any(marker in stripped for marker in ['{', '}', ';', 'import ', 'export ', 'function ', 'const ', 'var ', '===', '=>']):
            continue
        if len(stripped) < 3:
            continue
        clean_lines.append(stripped)
    text = '\n'.join(clean_lines)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def scrape_url(pw, item):
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    try:
        await page.goto(item["url"], wait_until="networkidle", timeout=60000)
        # Extra wait for SPA content to render
        await page.wait_for_timeout(3000)

        # Use JS to extract only visible text, stripping scripts/styles
        content = await page.evaluate("""() => {
            // Remove script, style, noscript elements
            const remove = document.querySelectorAll('script, style, noscript, link, meta, svg, img');
            remove.forEach(el => el.remove());
            
            // Try specific content selectors first
            const selectors = ['article', 'main', '[class*="article"]', '[class*="content"]', '[class*="policy"]'];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText && el.innerText.trim().length > 100) {
                    return el.innerText.trim();
                }
            }
            
            // Fallback: body text (scripts already removed)
            return document.body.innerText.trim();
        }""")

        content = clean_text(content)

        return {
            "country": item["country"],
            "url": item["url"],
            "content": content,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        print(f"Error scraping {item['country']}: {e}")
        return {
            "country": item["country"],
            "url": item["url"],
            "content": "",
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }
    finally:
        await browser.close()

async def scrape_all():
    async with async_playwright() as pw:
        tasks = [scrape_url(pw, item) for item in URLS]
        results = await asyncio.gather(*tasks)
        return results
