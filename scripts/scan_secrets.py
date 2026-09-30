import os
import re

SUSPECT_PATTERNS = [
    ("Google AI API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Generic API Key/Token", re.compile(r"(?i)(?:api[_-]?key|secret|token|password|auth)\s*[:=]\s*['\"][0-9a-zA-Z\-_]{16,}['\"]")),
    ("GitHub Personal Access Token", re.compile(r"ghp_[0-9a-zA-Z]{36}")),
    ("Private Key Header", re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----")),
]

found = []
for root, dirs, files in os.walk("."):
    # Skip directories that should never be tracked
    if any(skip in root.replace("\\", "/").split("/") for skip in ["node_modules", ".git", ".pytest_cache", "__pycache__", "cache", "dist"]):
        continue
    for f in files:
        if f.endswith((".pkl", ".png", ".jpg", ".ico", ".svg", ".gpkg", ".pyc")):
            continue
        filepath = os.path.join(root, f)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
                for line_num, line in enumerate(lines, 1):
                    for pat_name, pat in SUSPECT_PATTERNS:
                        matches = pat.findall(line)
                        if matches:
                            # Filter out placeholder lines like 'your_api_key_here'
                            for m in matches:
                                if "your_api_key" in str(m).lower() or "example" in str(m).lower():
                                    continue
                                found.append((filepath, line_num, pat_name))
        except Exception as e:
            pass

print(f"Secret scan completed. Found: {len(found)}")
for item in found:
    print(f"  {item[0]}:{item[1]} -> {item[2]}")
