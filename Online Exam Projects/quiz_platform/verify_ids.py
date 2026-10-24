import re

with open("quiz_platform/app/static/app.js", "r", encoding="utf-8") as f:
    js_content = f.read()

with open("quiz_platform/app/static/index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

js_ids = set(re.findall(r'document\.getElementById\(["\']([^"\']+)["\']\)', js_content))
html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))

missing = js_ids - html_ids
print("Referenced IDs in JS:", len(js_ids))
print("HTML defined IDs:", len(html_ids))
print("Missing IDs in HTML:", missing)
