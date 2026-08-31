@echo off
if not exist ".venv\Scripts\python.exe" (
    echo [AVISO] Ambiente virtual nao encontrado. Executando instalacao primeiro...
    call setup.bat
)

echo Iniciando JARVIS...
.venv\Scripts\python.exe -m app.main
