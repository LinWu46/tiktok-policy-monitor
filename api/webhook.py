"""
Vercel Serverless Function — Telegram Webhook Handler.
Handles incoming Telegram messages via webhook (no polling needed).
Reads policy data from GitHub raw URL, answers Q&A via Groq API.
"""
import json
import os
from http.server import BaseHTTPRequestHandler

import httpx
from groq import Groq

# ─── Config ──────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GITHUB_STATE_URL = os.environ.get(
    "GITHUB_STATE_URL",
    "https://raw.githubusercontent.com/LinWu46/tiktok-policy-monitor/main/core/state.json"
)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

COUNTRY_NAMES = {"DE": "🇩🇪 Đức", "FR": "🇫🇷 Pháp", "US": "🇺🇸 Mỹ"}

QA_SYSTEM_PROMPT = """Bạn là trợ lý chuyên gia về chính sách TikTok Creator Rewards Program.
Trả lời câu hỏi dựa trên nội dung chính sách được cung cấp bên dưới.
Trả lời bằng tiếng Việt, ngắn gọn, chính xác.
Nếu thông tin không có trong chính sách, nói rõ "Không tìm thấy trong chính sách hiện tại".
Luôn ghi rõ nguồn (quốc gia nào: 🇩🇪 Đức, 🇫🇷 Pháp, 🇺🇸 Mỹ).
Dùng emoji phù hợp để dễ đọc."""


# ─── Telegram API helpers ────────────────────────────────────

def send_message(chat_id, text, parse_mode=None):
    """Send a message via Telegram Bot API."""
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        httpx.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")


# ─── State & Q&A ─────────────────────────────────────────────

def load_state_from_github():
    """Fetch state.json from GitHub raw content."""
    try:
        resp = httpx.get(GITHUB_STATE_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Failed to load state from GitHub: {e}")
    return {}


def build_policy_context(state):
    """Build policy context string from state data."""
    if not state:
        return None
    parts = []
    for country, data in state.items():
        name = COUNTRY_NAMES.get(country, country)
        content = data.get("content", "")
        if len(content) > 6000:
            content = content[:6000] + "..."
        parts.append(f"=== Chính sách {name} ===\n{content}")
    return "\n\n".join(parts)


def answer_question(question, state):
    """Answer a question using Groq + policy data."""
    context = build_policy_context(state)
    if not context:
        return ("⚠️ Chưa có dữ liệu chính sách nào được thu thập.\n"
                "Dữ liệu sẽ được GitHub Actions tự động cập nhật mỗi 6 giờ.")

    prompt = f"""Dựa trên nội dung chính sách TikTok sau đây:

{context}

Câu hỏi của người dùng: {question}"""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return f"❌ Lỗi khi trả lời: {e}"


# ─── Command handlers ────────────────────────────────────────

def handle_start(chat_id):
    text = """🤖 <b>TikTok Policy Monitor Bot</b>

Xin chào! Tôi theo dõi chính sách TikTok Creator Rewards Program tại 3 quốc gia: 🇩🇪 Đức, 🇫🇷 Pháp, 🇺🇸 Mỹ.

<b>📋 Lệnh có sẵn:</b>
/start — Hiện bảng hướng dẫn này
/status — Xem trạng thái hiện tại

<b>💬 Hỏi đáp:</b>
Gửi bất kỳ câu hỏi nào về chính sách TikTok, tôi sẽ trả lời!

<i>Ví dụ: "Điều kiện tham gia Creator Rewards ở Đức là gì?"</i>

─────────────────
<i>🔄 Tự động kiểm tra thay đổi mỗi 6 giờ via GitHub Actions</i>"""
    send_message(chat_id, text, parse_mode="HTML")


def handle_status(chat_id):
    state = load_state_from_github()
    if not state:
        send_message(chat_id, "⚠️ Chưa có dữ liệu. GitHub Actions sẽ cập nhật mỗi 6 giờ.")
        return

    lines = ["📊 <b>Trạng thái hiện tại:</b>\n"]
    for country, data in state.items():
        name = COUNTRY_NAMES.get(country, country)
        content_len = len(data.get("content", ""))
        hash_short = data.get("hash", "N/A")[:12]
        lines.append(f"• {name}: {content_len:,} ký tự | hash: <code>{hash_short}...</code>")

    lines.append(f"\n📁 Theo dõi: <b>{len(state)} quốc gia</b>")
    lines.append("🔄 Tự động kiểm tra mỗi 6 giờ via GitHub Actions")
    send_message(chat_id, "\n".join(lines), parse_mode="HTML")


def handle_question(chat_id, question):
    send_message(chat_id, "🤔 Đang tìm câu trả lời...")
    state = load_state_from_github()
    answer = answer_question(question, state)
    # Telegram max message length is 4096
    if len(answer) > 4000:
        for i in range(0, len(answer), 4000):
            send_message(chat_id, answer[i:i+4000])
    else:
        send_message(chat_id, answer)


# ─── Main update handler ─────────────────────────────────────

def process_update(update):
    """Process a single Telegram update."""
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    if not chat_id or not text:
        return

    if text == "/start":
        handle_start(chat_id)
    elif text == "/status":
        handle_status(chat_id)
    else:
        handle_question(chat_id, text)


# ─── Vercel Serverless Handler ────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle webhook POST from Telegram."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            process_update(body)
        except Exception as e:
            print(f"Webhook error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>TikTok Policy Monitor Bot is running!</h1>")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
