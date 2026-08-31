# Script de Execucao do JARVIS Assistant
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[AVISO] Ambiente virtual nao encontrado. Executando setup..." -ForegroundColor Yellow
    .\setup.ps1
}

Write-Host "Iniciando JARVIS Assistant..." -ForegroundColor Cyan
& .venv\Scripts\python.exe -m app.main
