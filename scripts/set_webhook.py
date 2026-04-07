"""
One-time script to register Telegram webhook URL.
Usage: python scripts/set_webhook.py <VERCEL_URL>
Example: python scripts/set_webhook.py https://tiktok-policy-monitor.vercel.app
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python scripts/set_webhook.py <VERCEL_URL>")
    print("Example: python scripts/set_webhook.py https://tiktok-policy-monitor.vercel.app")
    sys.exit(1)

vercel_url = sys.argv[1].rstrip("/")
webhook_url = f"{vercel_url}/api/webhook"

print(f"🔗 Setting webhook to: {webhook_url}")

# Delete any existing webhook first
resp = httpx.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
    timeout=10
)
print(f"Delete old webhook: {resp.json()}")

# Set new webhook
resp = httpx.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    json={
        "url": webhook_url,
        "allowed_updates": ["message"],
        "drop_pending_updates": True
    },
    timeout=10
)
result = resp.json()
print(f"Set webhook: {result}")

if result.get("ok"):
    print(f"\n✅ Webhook registered successfully!")
    print(f"   URL: {webhook_url}")
    print(f"\n📱 Go to Telegram and send /start to test!")
else:
    print(f"\n❌ Failed to set webhook: {result}")
