#!/bin/bash
set -e
cd /tmp
TOKEN=$(cat /home/doubao-gcp/.gh_keepalive_token)
echo "=== 1. clone远端 ==="
rm -rf mbw
git clone https://x-access-token:${TOKEN}@github.com/hongshunli-spec/hongshunli-spec.github.io.git mbw 2>&1 | tail -1
cd mbw
git config user.name "hongshunli"
git config user.email "hongshunli@users.noreply.github.com"
echo "=== 2. 覆盖增量文件 ==="
cp -r /tmp/push_inc/. .
git add -A
echo "=== 3. commit ==="
git commit -m "修复搜索按钮：search.json输出格式+模块setup独立try；新增海子文章" 2>&1 | tail -2
echo "=== 4. push ==="
git push origin main 2>&1 | tail -2
echo "=== 5. 验证 ==="
git ls-remote origin main
echo "PUSH_DONE"
