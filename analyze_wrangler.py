# analyze_wrangler.py - extract pages assets API calls from wrangler cli.js
import re

CLI = r'C:\Users\hongshunli\AppData\Local\Doubao\User Data\sandbox_runtime\bases\c98c5042338ed152c6f10ecd8591889f\node\node_modules\wrangler\wrangler-dist\cli.js'
data = open(CLI, encoding='utf-8', errors='ignore').read()

ms = list(re.finditer(r'/pages/assets/[a-z-]+', data))
seen = set()
for m in ms:
    seg = data[m.start():m.end()]
    if seg in seen:
        continue
    seen.add(seg)
    s = max(0, m.start()-300)
    e = min(len(data), m.end()+150)
    print('=====', seg, '=====')
    print(data[s:e].replace('\n', ' ')[:450])
    print()
