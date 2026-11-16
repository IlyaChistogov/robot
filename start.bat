@echo off
echo ============================================================
echo   STARTING ROBOT PLATFORM (BACKEND + WEB UI)
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Starting Telemetry Backend (port 5000)...
start "Robot Backend Server" cmd /k "cd /d ""%~dp0backend"" && python server.py"

timeout /t 3 /nobreak > nul

echo [2/3] Starting React Operator Web UI (port 5173)...
start "Robot Web UI" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

timeout /t 3 /nobreak > nul

echo [3/3] Opening Web UI in default browser...
start http://localhost:5173

echo.
echo Platform successfully launched!
echo You can close this launcher window at any time.
pause
