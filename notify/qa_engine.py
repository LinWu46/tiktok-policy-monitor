from groq import Groq
from config import GROQ_API_KEY
from core.diff_engine import DiffEngine

QA_SYSTEM_PROMPT = """Bạn là trợ lý chuyên gia về chính sách TikTok Creator Rewards Program.
Trả lời câu hỏi dựa trên nội dung chính sách được cung cấp bên dưới.
Trả lời bằng tiếng Việt, ngắn gọn, chính xác.
Nếu thông tin không có trong chính sách, nói rõ "Không tìm thấy trong chính sách hiện tại".
Luôn ghi rõ nguồn (quốc gia nào: 🇩🇪 Đức, 🇫🇷 Pháp, 🇺🇸 Mỹ).
Dùng emoji phù hợp để dễ đọc."""

COUNTRY_NAMES = {
    "DE": "🇩🇪 Đức",
    "FR": "🇫🇷 Pháp",
    "US": "🇺🇸 Mỹ"
}

client = Groq(api_key=GROQ_API_KEY)

def build_policy_context():
    """Load policy content from state.json and build context string."""
    engine = DiffEngine()
    state = engine.load_state()

    if not state:
        return None

    context_parts = []
    for country, data in state.items():
        name = COUNTRY_NAMES.get(country, country)
        content = data.get("content", "")
        # Truncate to 8000 chars per country to stay within token limits
        if len(content) > 8000:
            content = content[:8000] + "..."
        context_parts.append(f"=== Chính sách {name} ===\n{content}")

    return "\n\n".join(context_parts)

def answer_question(user_question):
    """Answer a user question about TikTok policies using Groq + scraped data."""
    policy_context = build_policy_context()

    if not policy_context:
        return ("⚠️ Chưa có dữ liệu chính sách nào được thu thập.\n"
                "Hãy dùng /check để scrape chính sách trước, "
                "sau đó hỏi lại nhé!")

    prompt = f"""Dựa trên nội dung chính sách TikTok sau đây:

{policy_context}

Câu hỏi của người dùng: {user_question}"""

    try:
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
        print(f"QA error: {e}")
        return f"❌ Lỗi khi trả lời: {e}"
