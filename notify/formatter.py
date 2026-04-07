def format_message(country, url, scraped_at, diff_summary, vi_translation):
    flags = {
        "DE": "🇩🇪 Đức",
        "FR": "🇫🇷 Pháp",
        "US": "🇺🇸 Mỹ"
    }
    flag_name = flags.get(country, country)
    
    diff_summary = diff_summary.replace("<", "&lt;").replace(">", "&gt;")
    vi_translation = vi_translation.replace("<", "&lt;").replace(">", "&gt;")

    template = f"""🔔 <b>TikTok Policy Update</b>

🌍 Quốc gia: <b>{flag_name}</b>
🕐 Thời gian: {scraped_at}
🔗 <a href="{url}">Xem chính sách gốc</a>

📋 <b>Thay đổi (nội dung gốc):</b>
<pre>{diff_summary}</pre>

🇻🇳 <b>Bản dịch tiếng Việt:</b>
{vi_translation}

─────────────────
<i>Tự động cập nhật mỗi 6 giờ</i>"""

    return split_message(template)

def split_message(message, max_len=4000):
    if len(message) <= max_len:
        return [message]
    
    parts = []
    while message:
        if len(message) <= max_len:
            parts.append(message)
            break
        split_at = message.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(message[:split_at])
        message = message[split_at:]
    return parts
