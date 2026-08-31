# Script de Build do JARVIS executavel Windows standalone (PyInstaller one-dir)

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         COMPILACAO DO EXECUTAVEL WINDOWS DO JARVIS    " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Garante que os diretorios necessarios existam
New-Item -ItemType Directory -Force -Path "data", "assets\icons" | Out-Null

Write-Host "[*] Executando PyInstaller..." -ForegroundColor Yellow

& .venv\Scripts\pyinstaller.exe `
    --name "Jarvis" `
    --windowed `
    --noconfirm `
    --clean `
    --onedir `
    --add-data "data;data" `
    --add-data "assets;assets" `
    --hidden-import "app.ai.openai_provider" `
    --hidden-import "app.ai.gemini_provider" `
    --hidden-import "app.ai.anthropic_provider" `
    --hidden-import "app.tools.system_tools" `
    --hidden-import "app.tools.browser_tools" `
    --hidden-import "app.tools.file_tools" `
    --hidden-import "app.tools.clipboard_tools" `
    --hidden-import "app.tools.screenshot_tools" `
    --hidden-import "app.tools.note_tools" `
    --hidden-import "app.tools.reminder_tools" `
    --hidden-import "app.automation.screen_context" `
    --hidden-import "app.automation.computer_controller" `
    app/main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Compilacao concluida com sucesso!" -ForegroundColor Green
    Write-Host "Executavel gerado em: dist\Jarvis\Jarvis.exe" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERRO] Falha na compilacao com PyInstaller." -ForegroundColor Red
}
