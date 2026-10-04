# Optional: run the mock data sources as their own service on :8100
# then set MOCK_SOURCES_URL=http://127.0.0.1:8100 in .env
if (Test-Path .\venv\Scripts\Activate.ps1) { . .\venv\Scripts\Activate.ps1 }
uvicorn mock_sources.app:app --port 8100
