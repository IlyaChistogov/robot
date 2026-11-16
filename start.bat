@echo off
chcp 65001 > nul
echo ============================================================
echo   ЗАПУСК ПЛАТФОРМЫ МОБИЛЬНОГО РОБОТА (MOCK + ВЕБ-ПУЛЬТ)
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Запуск сервера телеметрии и видеопотока (порт 5000)...
start "Robot Backend Server" cmd /k "cd backend && python server.py"

timeout /t 2 /nobreak > nul

echo [2/3] Запуск веб-пульта оператора на React (порт 5173)...
start "Robot Web UI" cmd /k "cd frontend && npm run dev"

timeout /t 3 /nobreak > nul

echo [3/3] Открытие пульта управления в браузере...
start http://localhost:5173

echo.
echo Система успешно запущена!
echo Нажмите любую клавишу для закрытия этого окна...
pause > nul
