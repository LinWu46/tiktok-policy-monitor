import asyncio
import logging
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from notify.qa_engine import answer_question
from core.diff_engine import DiffEngine

logger = logging.getLogger(__name__)

# ─── Command Handlers ───────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = """🤖 <b>TikTok Policy Monitor Bot</b>

Xin chào! Tôi theo dõi chính sách TikTok Creator Rewards Program tại 3 quốc gia: 🇩🇪 Đức, 🇫🇷 Pháp, 🇺🇸 Mỹ.

<b>📋 Lệnh có sẵn:</b>
/start — Hiện bảng hướng dẫn này
/status — Xem trạng thái hiện tại
/check — Scrape chính sách ngay lập tức

<b>💬 Hỏi đáp:</b>
Gửi bất kỳ câu hỏi nào về chính sách TikTok, tôi sẽ trả lời dựa trên dữ liệu đã thu thập!

<i>Ví dụ: "Điều kiện tham gia Creator Rewards ở Đức là gì?"</i>

─────────────────
<i>🔄 Tự động kiểm tra thay đổi mỗi 6 giờ</i>"""

    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command — show current state."""
    engine = DiffEngine()
    state = engine.load_state()

    if not state:
        await update.message.reply_text(
            "⚠️ Chưa có dữ liệu. Dùng /check để scrape lần đầu."
        )
        return

    country_names = {"DE": "🇩🇪 Đức", "FR": "🇫🇷 Pháp", "US": "🇺🇸 Mỹ"}
    lines = ["📊 <b>Trạng thái hiện tại:</b>\n"]
    for country, data in state.items():
        name = country_names.get(country, country)
        content_len = len(data.get("content", ""))
        hash_short = data.get("hash", "N/A")[:12]
        lines.append(f"• {name}: {content_len:,} ký tự | hash: <code>{hash_short}...</code>")

    lines.append(f"\n📁 Theo dõi: <b>{len(state)} quốc gia</b>")
    lines.append("🔄 Tự động kiểm tra mỗi 6 giờ")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command — run scrape immediately."""
    await update.message.reply_text("🔍 Đang scrape chính sách... Vui lòng chờ ~30 giây.")

    try:
        from scraper.scraper import scrape_all
        from notify.translator import translate
        from notify.formatter import format_message

        scraped_data = await scrape_all()
        engine = DiffEngine()
        changes = engine.detect_changes(scraped_data)

        if not changes:
            await update.message.reply_text("✅ Không có thay đổi nào!")
            return

        await update.message.reply_text(
            f"🔔 Phát hiện thay đổi tại {len(changes)} quốc gia! Đang xử lý..."
        )

        for change in changes:
            diff_summary = engine.get_diff_summary(change['old_content'], change['new_content'])
            translation = translate(diff_summary)
            msgs = format_message(
                country=change['country'],
                url=change['url'],
                scraped_at=change['scraped_at'],
                diff_summary=diff_summary,
                vi_translation=translation
            )
            for msg in msgs:
                await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

        # Save new state
        state = engine.load_state()
        for change in changes:
            state[change['country']] = {
                "hash": change['new_hash'],
                "content": change['new_content']
            }
        engine.save_state(state)
        await update.message.reply_text("💾 Đã lưu trạng thái mới!")

    except Exception as e:
        logger.error(f"Check command error: {e}")
        await update.message.reply_text(f"❌ Lỗi: {e}")


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-text messages as policy questions."""
    question = update.message.text.strip()
    if not question:
        return

    await update.message.reply_text("🤔 Đang tìm câu trả lời...")

    try:
        answer = answer_question(question)
        # Telegram max message length is 4096
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await update.message.reply_text(answer[i:i+4000])
        else:
            await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"QA error: {e}")
        await update.message.reply_text(f"❌ Lỗi: {e}")


# ─── Notification Function (for scheduled jobs) ─────────────

async def send_notification(text):
    """Send a notification message to the configured chat (for scheduled monitoring)."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            return True
        except Exception as e:
            logger.error(f"Telegram send failed (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(5)
    return False


async def send_notifications(messages):
    """Send multiple notification messages."""
    for msg in messages:
        await send_notification(msg)


# ─── Bot Application Builder ────────────────────────────────

def build_bot_app():
    """Build and return the Telegram bot application with all handlers."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    return app
