@echo off
title RRB AI Practice Center - Frontend Starter
echo.
echo ==============================================
echo   RRB AI Practice Center - Frontend Starter
echo ==============================================
echo.
echo Local dev server is starting on:
echo http://localhost:5500/rrb-exam-prep/frontend/login.html
echo.
echo Note:
echo - Ye localhost se /api/generate ko backend lambda_function.py tak bhejega.
echo - Agar purana python -m http.server chal raha ho to use pehle band karo.
echo - Is window ko band mat karna.
echo.
cd /d "%~dp0"
python dev_server.py