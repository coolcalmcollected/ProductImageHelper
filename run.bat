@echo off
title Product Image Helper - 600x600 Formatter
cd /d "%~dp0"

echo ========================================================
echo  Product Image Helper - Background & Shadow Cleaner
echo  Target: 600x600 Pure White Background (5%% Margin)
echo ========================================================
echo.
echo Starting local web server...
start "" http://127.0.0.1:5055
.\venv\Scripts\python.exe app.py 5055
pause
