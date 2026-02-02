# PR-System - Instalación en Windows

## Opción 1: Instalador Automático (.bat)

1. Descarga el repositorio: https://github.com/srexcel/PR/archive/refs/heads/main.zip
2. Extrae el ZIP
3. Click derecho en `instalador_windows.bat` → **Ejecutar como administrador**
4. Espera a que termine la instalación
5. Ejecuta `iniciar_pr.bat` para iniciar el sistema

## Opción 2: Instalación Manual

### Requisitos
- Windows 10/11 (64-bit)
- 4GB RAM mínimo
- 3GB espacio en disco

### Pasos

```powershell
# 1. Instalar Python (si no está instalado)
# Descargar de: https://www.python.org/downloads/

# 2. Instalar Git (si no está instalado)
# Descargar de: https://git-scm.com/download/win

# 3. Abrir PowerShell y ejecutar:
git clone https://github.com/srexcel/PR.git
cd PR

# 4. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate

# 5. Instalar dependencias
pip install -r requirements.txt

# 6. Instalar Ollama
# Descargar de: https://ollama.com/download/windows

# 7. Descargar modelo de IA
ollama pull llama3.2:1b

# 8. Iniciar servidor
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Opción 3: Crear Ejecutable (.exe)

Si quieres distribuir un instalador .exe:

```powershell
# Instalar PyInstaller
pip install pyinstaller

# Crear ejecutable
pyinstaller --onefile --name "PR-System-Installer" installer.py
```

El ejecutable estará en: `dist/PR-System-Installer.exe`

## Uso del Sistema

### Iniciar
- Ejecuta `iniciar_pr.bat` o `Iniciar PR-System.bat`
- Abre el navegador en: http://localhost:8000

### Credenciales
| Usuario | Contraseña |
|---------|------------|
| admin   | admin123   |

### Detener
- Presiona `Ctrl+C` en la ventana de comandos
- O cierra la ventana

## Solución de Problemas

### "Python no encontrado"
- Instala Python desde https://www.python.org/downloads/
- Asegúrate de marcar "Add Python to PATH" durante la instalación

### "Ollama no responde"
- Ejecuta `ollama serve` en otra terminal
- Verifica que el puerto 11434 no esté ocupado

### "Error de permisos"
- Ejecuta como administrador (click derecho → Ejecutar como administrador)

### "Puerto 8000 ocupado"
- Cambia el puerto: `python -m uvicorn main:app --port 8001`

## Soporte

- GitHub Issues: https://github.com/srexcel/PR/issues
