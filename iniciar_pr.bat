@echo off
chcp 65001 >nul
title PR-System - Sistema de Conocimiento Vivo
color 0B

cd /d "%~dp0"

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║         PR-SYSTEM - Sistema de Conocimiento Vivo          ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [!] Entorno virtual no encontrado.
    echo [!] Ejecuta primero: instalador_windows.bat
    pause
    exit /b 1
)

:: Iniciar Ollama en segundo plano
echo [*] Iniciando servicio de IA...
start /min ollama serve 2>nul

:: Esperar a que Ollama inicie
timeout /t 3 /nobreak >nul

echo [*] Iniciando servidor PR-System...
echo.
echo  ════════════════════════════════════════════════════════════
echo.
echo    URL:      http://localhost:8000
echo    Usuario:  admin
echo    Password: admin123
echo.
echo  ════════════════════════════════════════════════════════════
echo.
echo    Presiona Ctrl+C para detener el servidor
echo.

:: Abrir navegador
start http://localhost:8000

:: Iniciar servidor
python -m uvicorn main:app --host 0.0.0.0 --port 8000
