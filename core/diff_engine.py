import json
import hashlib
import os
from difflib import ndiff

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

class DiffEngine:
    def load_state(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
            return {}
        except Exception:
            return {}

    def save_state(self, data):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def compute_hash(self, content):
        if not content:
            return ""
        return hashlib.sha256(content[:3000].encode("utf-8")).hexdigest()

    def detect_changes(self, new_data):
        state = self.load_state()
        changes = []
        is_first_run = len(state) == 0

        for item in new_data:
            country = item["country"]
            content = item["content"]
            new_hash = self.compute_hash(content)
            
            if is_first_run or country not in state or state[country]["hash"] != new_hash:
                old_content = state.get(country, {}).get("content", "") if not is_first_run else ""
                changes.append({
                    "country": country,
                    "url": item["url"],
                    "old_content": old_content,
                    "new_content": content,
                    "scraped_at": item["scraped_at"],
                    "new_hash": new_hash
                })
        return changes

    def get_diff_summary(self, old_content, new_content):
        if not old_content:
            return "+ [New Policy Added]"
        
        old_lines = old_content.split('. ')
        new_lines = new_content.split('. ')
        
        diff = ndiff(old_lines, new_lines)
        changed = []
        for line in diff:
            if line.startswith('+ ') or line.startswith('- '):
                changed.append(line.strip())
        
        summary = "\n".join(changed)
        if len(summary) > 1500:
            summary = summary[:1497] + "..."
        if not summary.strip():
            summary = "No detailed diff available (hash changed but diff empty)."
        return summary
