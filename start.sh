#!/usr/bin/env bash
echo "============================================================"
echo "  ЗАПУСК ПЛАТФОРМЫ МОБИЛЬНОГО РОБОТА (MOCK + ВЕБ-ПУЛЬТ)"
echo "============================================================"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "[1/2] Запуск сервера телеметрии (порт 5000)..."
python3 backend/server.py &
BACKEND_PID=$!

echo "[2/2] Запуск веб-пульта оператора на React (порт 5173)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM
echo "Платформа запущена! Перейдите на http://localhost:5173"
wait
