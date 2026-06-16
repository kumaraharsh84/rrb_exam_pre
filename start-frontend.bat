@echo off
title RRB AI Practice Center - Frontend Starter
echo.
echo ==============================================
echo   RRB AI Practice Center - Frontend Starter
echo ==============================================
echo.
echo Local dev server is starting on:
echo http://localhost:5500/frontend/login.html
echo.
echo Note:
echo - This proxies /api/generate requests to the backend lambda_function.py.
echo - If an old python -m http.server is still running, stop it first.
echo - Do not close this window while the server is running.
echo.
cd /d "%~dp0"
python dev_server.py