#!/usr/bin/env bash
# Dev helper: restart the FastAPI backend (kills the running uvicorn on port 8000 first).
cd "$(dirname "$0")/.." || exit 1
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { \$_.CommandLine -match 'uvicorn app.main' } | % { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
sleep 1
exec .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
