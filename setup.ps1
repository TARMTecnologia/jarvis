# Script de Instalacao e Configuracao Automatizada do JARVIS para PowerShell

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         JARVIS ASSISTANT — INSTALACAO AUTOMATIZADA    " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica Python
Write-Host "[*] Verificando instalacao do Python..." -ForegroundColor Yellow

$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3.13"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
}

if (-not $pythonCmd) {
    Write-Host "[ERRO] Python nao encontrado. Instale o Python 3.12+ em python.org" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Usando: $pythonCmd" -ForegroundColor Green

# 2. Cria venv
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Criando ambiente virtual em .venv..." -ForegroundColor Yellow
    Invoke-Expression "$pythonCmd -m venv .venv"
}
Write-Host "[OK] Ambiente virtual pronto." -ForegroundColor Green

# 3. Instala dependencias
Write-Host "[*] Instalando dependencias do requirements.txt..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
& .venv\Scripts\pip.exe install -r requirements.txt

# 4. Cria pastas
New-Item -ItemType Directory -Force -Path "data", "data\cache", "logs", "assets\icons" | Out-Null

# 5. Executa doctor
Write-Host "`n[*] Executando auto-diagnostico do sistema..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m app.doctor

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host "        INSTALACAO CONCLUIDA COM SUCESSO!              " -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "Para iniciar o JARVIS, execute: .\run.ps1 ou run.bat`n" -ForegroundColor Cyan
