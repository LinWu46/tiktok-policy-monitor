import time
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

SYSTEM_PROMPT = """Bạn là chuyên gia dịch chính sách TikTok sang tiếng Việt. Dịch ngắn gọn, giữ nguyên số liệu và tên chương trình. Đánh dấu [THÊM MỚI] cho nội dung mới, [ĐÃ XÓA] cho nội dung bị xóa. Tối đa 300 từ."""

client = genai.Client(api_key=GEMINI_API_KEY)

def translate(diff_summary):
    if not diff_summary or diff_summary.strip() == "":
        return "Không có nội dung để dịch."

    # Truncate very long diffs to avoid token limits
    if len(diff_summary) > 3000:
        diff_summary = diff_summary[:3000] + "\n... (đã cắt bớt)"

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=diff_summary,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=500,
                    temperature=0.3
                )
            )
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 15 * (attempt + 1)  # 15s, 30s, 45s
                print(f"⏳ Gemini rate limit hit, waiting {wait}s (attempt {attempt+1}/3)...")
                time.sleep(wait)
            else:
                print(f"Translation error: {e}")
                return "Lỗi dịch thuật: " + str(e)

    return "⚠️ Gemini API đang quá tải, vui lòng thử lại sau."
