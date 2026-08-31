@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          COMPILACAO DO EXECUTAVEL WINDOWS DO JARVIS    
echo =======================================================
echo.

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [AVISO] PyInstaller nao encontrado. Executando instalacao primeiro...
    call setup.bat
)

if not exist "data" mkdir data
if not exist "assets\icons" mkdir assets\icons

echo [*] Executando PyInstaller (One-Directory)...
.venv\Scripts\pyinstaller.exe ^
    --name "Jarvis" ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --add-data "data;data" ^
    --add-data "assets;assets" ^
    --hidden-import "app.ai.openai_provider" ^
    --hidden-import "app.ai.gemini_provider" ^
    --hidden-import "app.ai.anthropic_provider" ^
    --hidden-import "app.tools.system_tools" ^
    --hidden-import "app.tools.browser_tools" ^
    --hidden-import "app.tools.file_tools" ^
    --hidden-import "app.tools.clipboard_tools" ^
    --hidden-import "app.tools.screenshot_tools" ^
    --hidden-import "app.tools.note_tools" ^
    --hidden-import "app.tools.reminder_tools" ^
    --hidden-import "app.automation.screen_context" ^
    --hidden-import "app.automation.computer_controller" ^
    app/main.py

if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo          BUILD CONCLUIDO COM SUCESSO!
    echo =======================================================
    echo Executavel gerado em: dist\Jarvis\Jarvis.exe
) else (
    echo.
    echo [ERRO] Falha ao compilar com PyInstaller.
)
echo.
pause
