# Windows PowerShell: start the v2 backend (API + in-process mock sources)
# Usage:  .\scripts\run_backend.ps1
if (Test-Path .\venv\Scripts\Activate.ps1) { . .\venv\Scripts\Activate.ps1 }
uvicorn app.api.main:app --port 8000 --reload
