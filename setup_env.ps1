# MFDE Environment Setup Script
# Version Lock: Python 3.12 (Stable)

if (-not (Test-Path "venv")) {
    Write-Host "Creating stable Virtual Environment (Python 3.12)..." -ForegroundColor Cyan
    & py -3.12 -m venv venv
}

Write-Host "Updating dependencies in venv..." -ForegroundColor Green
& .\venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "`nEnvironment Ready!" -ForegroundColor Yellow
Write-Host "To run inference: .\venv\Scripts\python.exe inference.py"
Write-Host "To run server:    .\venv\Scripts\python.exe -m server.app"
