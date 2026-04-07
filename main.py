import asyncio
import logging
import sys
from datetime import datetime

import config
from scraper.scraper import scrape_all
from core.diff_engine import DiffEngine
from notify.translator import translate
from notify.formatter import format_message
from notify.telegram_bot import send_notifications, build_bot_app

from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def _monitor_async():
    """Async implementation of the monitor job."""
    try:
        logger.info("🔍 Scraping URLs...")
        scraped_data = await scrape_all()

        diff_engine = DiffEngine()
        logger.info("🔎 Detecting changes...")
        changes = diff_engine.detect_changes(scraped_data)

        if not changes:
            logger.info("✅ No changes detected")
            return

        logger.info(f"🔔 Changes in {len(changes)} countries: {[c['country'] for c in changes]}")

        for i, change in enumerate(changes):
            country = change['country']
            logger.info(f"Processing {country}...")

            # Delay between countries to avoid Gemini rate limits
            if i > 0:
                logger.info("⏳ Waiting 10s to avoid API rate limits...")
                await asyncio.sleep(10)

            diff_summary = diff_engine.get_diff_summary(change['old_content'], change['new_content'])
            translation = translate(diff_summary)
            msgs = format_message(
                country=country,
                url=change['url'],
                scraped_at=change['scraped_at'],
                diff_summary=diff_summary,
                vi_translation=translation
            )
            await send_notifications(msgs)

        # Save new state
        state = diff_engine.load_state()
        for change in changes:
            state[change['country']] = {
                "hash": change['new_hash'],
                "content": change['new_content']
            }
        diff_engine.save_state(state)
        logger.info("💾 State saved")

    except Exception as e:
        logger.error(f"Monitor job error: {e}")


def monitor_job():
    """Scheduled job wrapper for BackgroundScheduler."""
    asyncio.get_event_loop().run_until_complete(_monitor_async())


def run_once():
    """Run monitor once and exit (for GitHub Actions)."""
    logger.info("🚀 Running one-time monitor...")
    asyncio.run(_monitor_async())
    logger.info("✅ Done!")


def run_bot():
    """Start the always-on bot + scheduler (for local/server)."""
    logger.info("🚀 Starting TikTok Policy Monitor Bot...")

    # Build the Telegram bot application
    app = build_bot_app()

    # Setup BackgroundScheduler — run monitor every 6 hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_job, 'interval', hours=6)
    scheduler.start()
    logger.info("📅 Scheduler started — monitoring every 6 hours")

    # Run initial scrape via post_init
    async def post_init(application):
        logger.info("🔍 Running initial scrape...")
        asyncio.create_task(_monitor_async())

    app.post_init = post_init

    # Start polling (this blocks and runs forever)
    logger.info("🤖 Bot is listening for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        run_bot()
