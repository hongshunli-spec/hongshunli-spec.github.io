@echo off
chcp 65001
cd /d D:\myblog
echo 拉取云端最新代码防止冲突
git pull origin main
echo.
echo 生成静态页面
hugo
echo.
echo 提交全部修改文件
git add .
set /p msg=输入更新备注(不能为空):
git commit -m "%msg%"
echo.
echo 推送至GitHub
git push origin main
echo.
echo.
echo Deploying to Cloudflare Pages...
npx --yes wrangler@3 pages deploy D:\myblog\public --project-name hongshunli-blog --branch main
echo.
echo ========== 发布完成 ==========
pause