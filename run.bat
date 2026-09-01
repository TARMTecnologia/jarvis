@echo off
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" (
    echo [AVISO] Ambiente virtual nao encontrado. Executando instalacao primeiro...
    call setup.bat
)
echo Iniciando JARVIS...
.venv\Scripts\python.exe -m app.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ocorreu uma falha na execucao do JARVIS.
    pause
)
