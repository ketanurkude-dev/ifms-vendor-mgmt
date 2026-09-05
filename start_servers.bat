@echo off
start "Backend" cmd /k "cd /d E:\IFMS\vendor_mgmt\backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 9003"
start "Frontend" cmd /k "cd /d E:\IFMS\vendor_mgmt\frontend && npm run dev"
