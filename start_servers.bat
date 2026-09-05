@echo off
start "Backend" cmd /k "cd /d E:\IFMS\vendor_mgmt\backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8002"
start "Frontend" cmd /k "cd /d E:\IFMS\vendor_mgmt\frontend && npm run dev"
