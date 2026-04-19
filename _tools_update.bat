@echo off
chcp 949 > nul
set TOOLS=C:\Users\MMCCV\kimp_tools
set REPO=C:\Users\MMCCV\kimp_repo
set LOG="%TOOLS%\update.log"
echo [%date% %time%] START >> %LOG%
py -3 "%TOOLS%\parse_logs.py" >> %LOG% 2>&1
set PARSE_CODE=%ERRORLEVEL%
cd /d "%REPO%"
git add data.js >> %LOG% 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "update data" >> %LOG% 2>&1
    git push origin main >> %LOG% 2>&1
) else (
    echo [%date% %time%] no change >> %LOG%
)
echo [%date% %time%] END parse=%PARSE_CODE% >> %LOG%
