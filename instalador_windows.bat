@echo off
chcp 65001 >nul
title PR-System - Instalador Automatico
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║   PR-SYSTEM - Sistema de Conocimiento Vivo                ║
echo  ║   Instalador Automatico para Windows                      ║
echo  ║                                                           ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Este instalador requiere permisos de administrador.
    echo [!] Click derecho -^> Ejecutar como administrador
    pause
    exit /b 1
)

echo [1/6] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python no encontrado. Instalando Python...
    echo [*] Descargando Python 3.12...
    curl -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    echo [*] Instalando Python (esto puede tardar unos minutos)...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    echo [OK] Python instalado correctamente
) else (
    echo [OK] Python ya esta instalado
)

echo.
echo [2/6] Verificando Git...
git --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Git no encontrado. Instalando Git...
    curl -o git_installer.exe -L https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe
    git_installer.exe /VERYSILENT /NORESTART
    del git_installer.exe
    set "PATH=%PATH%;C:\Program Files\Git\bin"
    echo [OK] Git instalado correctamente
) else (
    echo [OK] Git ya esta instalado
)

echo.
echo [3/6] Descargando PR-System...
if exist "PR-System" (
    echo [*] Actualizando repositorio existente...
    cd PR-System
    git pull
) else (
    git clone https://github.com/srexcel/PR.git PR-System
    cd PR-System
)
echo [OK] Codigo descargado

echo.
echo [4/6] Configurando entorno Python...
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo [OK] Dependencias instaladas

echo.
echo [5/6] Instalando Ollama (LLM local)...
where ollama >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Descargando Ollama...
    curl -o ollama_installer.exe -L https://ollama.com/download/OllamaSetup.exe
    echo [*] Instalando Ollama...
    ollama_installer.exe /VERYSILENT /NORESTART
    del ollama_installer.exe
    set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Ollama"
    echo [OK] Ollama instalado
) else (
    echo [OK] Ollama ya esta instalado
)

echo.
echo [6/6] Descargando modelo de IA...
echo [*] Esto puede tardar varios minutos (1.3 GB)...
start /wait ollama pull llama3.2:1b
echo [OK] Modelo descargado

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║   INSTALACION COMPLETADA!                                 ║
echo  ║                                                           ║
echo  ║   Para iniciar el sistema, ejecuta: iniciar_pr.bat        ║
echo  ║                                                           ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: Crear script de inicio
echo @echo off > iniciar_pr.bat
echo title PR-System >> iniciar_pr.bat
echo cd /d "%%~dp0" >> iniciar_pr.bat
echo call venv\Scripts\activate.bat >> iniciar_pr.bat
echo start ollama serve >> iniciar_pr.bat
echo timeout /t 3 /nobreak ^>nul >> iniciar_pr.bat
echo echo. >> iniciar_pr.bat
echo echo  PR-System iniciando... >> iniciar_pr.bat
echo echo  Abre tu navegador en: http://localhost:8000 >> iniciar_pr.bat
echo echo. >> iniciar_pr.bat
echo echo  Usuario: admin >> iniciar_pr.bat
echo echo  Password: admin123 >> iniciar_pr.bat
echo echo. >> iniciar_pr.bat
echo start http://localhost:8000 >> iniciar_pr.bat
echo python -m uvicorn main:app --host 0.0.0.0 --port 8000 >> iniciar_pr.bat

echo [*] Creado acceso directo: iniciar_pr.bat

pause
