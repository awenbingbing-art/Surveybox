@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   北京蓝天感知调查 - 本地统计工具
echo ============================================
echo.
echo   问卷页    http://127.0.0.1:8791/
echo   统计看板  http://127.0.0.1:8791/dashboard
echo.
python server.py --port 8791
pause
