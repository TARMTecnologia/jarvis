@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          JARVIS ASSISTANT — INSTALACAO AUTOMATIZADA
echo =======================================================
echo.

:: 1. Verificacao do Python
echo [*] Verificando instalacao do Python...
set PYTHON_CMD=

py -3.13 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.13
    goto :found_python
)

py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.12
    goto :found_python
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :found_python
)

echo [ERRO] Python 3.12 ou 3.13 nao foi encontrado no sistema.
echo Por favor, instale o Python em https://www.python.org/downloads/
pause
exit /b 1

:found_python
echo [OK] Python detectado: !PYTHON_CMD!

:: 2. Criacao do Ambiente Virtual
if not exist ".venv" (
    echo [*] Criando ambiente virtual em .venv...
    !PYTHON_CMD! -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
)
echo [OK] Ambiente virtual pronto.

:: 3. Atualizacao de Pip e Instalacao de Dependencias
echo [*] Instalando dependencias do JARVIS...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar algumas dependencias.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas com sucesso.

:: 4. Criacao de Diretorios Necessarios
if not exist "data" mkdir data
if not exist "data\cache" mkdir data\cache
if not exist "logs" mkdir logs

:: 5. Execucao do Diagnostico
echo.
echo [*] Executando diagnostico do sistema...
.venv\Scripts\python.exe -m app.doctor

echo.
echo =======================================================
echo         INSTALACAO DO JARVIS CONCLUIDA COM SUCESSO!
echo =======================================================
echo.
echo Para iniciar o assistente, execute:
echo    run.bat
echo.
pause
