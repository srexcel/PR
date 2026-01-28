#!/usr/bin/env python3
"""
PR-System - Script de Inicio Rápido
Ejecuta: python start.py
"""

import subprocess
import sys
import os

def main():
    print("=" * 50)
    print("  PR-System - Sistema de Conocimiento Vivo")
    print("=" * 50)
    print()
    
    # Cambiar al directorio del proyecto
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Verificar/instalar dependencias
    print("[1/2] Verificando dependencias...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"
        ])
        print("      ✓ Dependencias instaladas")
    except Exception as e:
        print(f"      ✗ Error instalando dependencias: {e}")
        return
    
    # Iniciar servidor
    print("[2/2] Iniciando servidor...")
    print()
    print("=" * 50)
    print("  ✓ Sistema listo!")
    print("  Abre tu navegador en: http://localhost:8000")
    print()
    print("  Usuario: admin  |  Contraseña: admin123")
    print("=" * 50)
    print()
    print("Presiona Ctrl+C para detener")
    print()
    
    try:
        subprocess.call([
            sys.executable, "-m", "uvicorn", "main:app", 
            "--host", "0.0.0.0", "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\nServidor detenido.")

if __name__ == "__main__":
    main()
