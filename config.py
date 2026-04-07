import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

missing = []
if not TELEGRAM_BOT_TOKEN:
    missing.append("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_CHAT_ID:
    missing.append("TELEGRAM_CHAT_ID")
if not GEMINI_API_KEY:
    missing.append("GEMINI_API_KEY")

if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
