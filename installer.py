#!/usr/bin/env python3
"""
PR-System Installer for Windows
================================
Este script instala y configura PR-System automáticamente.

Para crear el .exe:
    pip install pyinstaller
    pyinstaller --onefile --name "PR-System-Installer" --icon=icon.ico installer.py
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
import ctypes
import time

# Colores para consola Windows
os.system('color 0A')

def is_admin():
    """Verificar si se ejecuta como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def print_banner():
    print("""
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   PR-SYSTEM - Sistema de Conocimiento Vivo                ║
  ║   Instalador Automático para Windows                      ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
    """)

def print_step(num, total, msg):
    print(f"\n[{num}/{total}] {msg}")

def print_ok(msg):
    print(f"  [OK] {msg}")

def print_error(msg):
    print(f"  [ERROR] {msg}")

def print_info(msg):
    print(f"  [*] {msg}")

def run_command(cmd, shell=True, check=True):
    """Ejecutar comando y retornar resultado"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python():
    """Verificar instalación de Python"""
    success, stdout, _ = run_command("python --version")
    return success

def check_git():
    """Verificar instalación de Git"""
    success, _, _ = run_command("git --version")
    return success

def check_ollama():
    """Verificar instalación de Ollama"""
    success, _, _ = run_command("ollama --version")
    return success

def download_file(url, filename):
    """Descargar archivo con barra de progreso"""
    print_info(f"Descargando {filename}...")
    try:
        urllib.request.urlretrieve(url, filename)
        return True
    except Exception as e:
        print_error(f"Error descargando: {e}")
        return False

def install_python():
    """Instalar Python"""
    url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
    installer = "python_installer.exe"

    if download_file(url, installer):
        print_info("Instalando Python (esto puede tardar)...")
        subprocess.run([installer, "/quiet", "InstallAllUsers=1", "PrependPath=1"], check=True)
        os.remove(installer)
        print_ok("Python instalado")
        return True
    return False

def install_git():
    """Instalar Git"""
    url = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
    installer = "git_installer.exe"

    if download_file(url, installer):
        print_info("Instalando Git...")
        subprocess.run([installer, "/VERYSILENT", "/NORESTART"], check=True)
        os.remove(installer)
        print_ok("Git instalado")
        return True
    return False

def install_ollama():
    """Instalar Ollama"""
    url = "https://ollama.com/download/OllamaSetup.exe"
    installer = "ollama_installer.exe"

    if download_file(url, installer):
        print_info("Instalando Ollama...")
        subprocess.run([installer, "/VERYSILENT", "/NORESTART"], check=True)
        os.remove(installer)
        print_ok("Ollama instalado")
        return True
    return False

def clone_repository():
    """Clonar repositorio de GitHub"""
    repo_url = "https://github.com/srexcel/PR.git"
    target_dir = "PR-System"

    if os.path.exists(target_dir):
        print_info("Actualizando repositorio existente...")
        os.chdir(target_dir)
        run_command("git pull")
    else:
        print_info("Clonando repositorio...")
        run_command(f"git clone {repo_url} {target_dir}")
        os.chdir(target_dir)

    print_ok("Código descargado")
    return True

def setup_venv():
    """Configurar entorno virtual"""
    if not os.path.exists("venv"):
        print_info("Creando entorno virtual...")
        run_command("python -m venv venv")

    print_info("Instalando dependencias...")

    # Activar venv y ejecutar pip
    if sys.platform == "win32":
        pip_path = os.path.join("venv", "Scripts", "pip.exe")
    else:
        pip_path = os.path.join("venv", "bin", "pip")

    run_command(f'"{pip_path}" install --upgrade pip -q')
    run_command(f'"{pip_path}" install -r requirements.txt -q')

    print_ok("Dependencias instaladas")
    return True

def download_llm_model():
    """Descargar modelo de IA"""
    print_info("Descargando modelo de IA (1.3 GB)...")
    print_info("Esto puede tardar varios minutos...")

    # Iniciar Ollama primero
    subprocess.Popen(["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    time.sleep(3)

    run_command("ollama pull llama3.2:1b")
    print_ok("Modelo descargado")
    return True

def create_shortcuts():
    """Crear accesos directos"""
    # Crear script de inicio
    start_script = """@echo off
chcp 65001 >nul
title PR-System
cd /d "%~dp0"
call venv\\Scripts\\activate.bat
start /min ollama serve
timeout /t 3 /nobreak >nul
echo.
echo  PR-System iniciando...
echo  URL: http://localhost:8000
echo  Usuario: admin / Password: admin123
echo.
start http://localhost:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000
"""

    with open("Iniciar PR-System.bat", "w", encoding="utf-8") as f:
        f.write(start_script)

    print_ok("Acceso directo creado: Iniciar PR-System.bat")
    return True

def main():
    print_banner()

    if sys.platform != "win32":
        print_error("Este instalador es solo para Windows")
        print_info("En Linux/Mac, usa: python start.py")
        input("\nPresiona Enter para salir...")
        return

    if not is_admin():
        print_error("Este instalador requiere permisos de administrador")
        print_info("Click derecho -> Ejecutar como administrador")
        input("\nPresiona Enter para salir...")
        return

    total_steps = 6

    # Paso 1: Python
    print_step(1, total_steps, "Verificando Python...")
    if check_python():
        print_ok("Python ya está instalado")
    else:
        install_python()

    # Paso 2: Git
    print_step(2, total_steps, "Verificando Git...")
    if check_git():
        print_ok("Git ya está instalado")
    else:
        install_git()

    # Paso 3: Clonar repo
    print_step(3, total_steps, "Descargando PR-System...")
    clone_repository()

    # Paso 4: Entorno virtual
    print_step(4, total_steps, "Configurando entorno Python...")
    setup_venv()

    # Paso 5: Ollama
    print_step(5, total_steps, "Instalando Ollama (LLM local)...")
    if check_ollama():
        print_ok("Ollama ya está instalado")
    else:
        install_ollama()

    # Paso 6: Modelo
    print_step(6, total_steps, "Descargando modelo de IA...")
    download_llm_model()

    # Crear accesos directos
    create_shortcuts()

    print("""
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ¡INSTALACIÓN COMPLETADA!                                ║
  ║                                                           ║
  ║   Para iniciar: doble click en "Iniciar PR-System.bat"    ║
  ║                                                           ║
  ║   URL:      http://localhost:8000                         ║
  ║   Usuario:  admin                                         ║
  ║   Password: admin123                                      ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
    """)

    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()
