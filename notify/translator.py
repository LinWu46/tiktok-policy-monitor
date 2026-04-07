import time
from groq import Groq
from config import GROQ_API_KEY

SYSTEM_PROMPT = """Bạn là chuyên gia dịch chính sách TikTok sang tiếng Việt. Dịch ngắn gọn, giữ nguyên số liệu và tên chương trình. Đánh dấu [THÊM MỚI] cho nội dung mới, [ĐÃ XÓA] cho nội dung bị xóa. Tối đa 300 từ."""

client = Groq(api_key=GROQ_API_KEY)

def translate(diff_summary):
    if not diff_summary or diff_summary.strip() == "":
        return "Không có nội dung để dịch."

    # Truncate very long diffs to avoid token limits
    if len(diff_summary) > 3000:
        diff_summary = diff_summary[:3000] + "\n... (đã cắt bớt)"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": diff_summary}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                wait = 15 * (attempt + 1)
                print(f"⏳ Groq rate limit hit, waiting {wait}s (attempt {attempt+1}/3)...")
                time.sleep(wait)
            else:
                print(f"Translation error: {e}")
                return "Lỗi dịch thuật: " + str(e)

    return "⚠️ Groq API đang quá tải, vui lòng thử lại sau."
