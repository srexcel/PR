# 🧠 PR-System: Sistema de Conocimiento Vivo

> **El conocimiento de tu empresa ya no se pierde. El conocimiento vive.**

## ¿Qué es PR-System?

Es un sistema que **aprende** de cada problema resuelto en tu empresa. A diferencia de ISO, ERPs o SharePoint que solo guardan documentos muertos, PR-System:

- ✅ **Aconseja** cuando reportas un problema nuevo ("Encontré 3 casos similares...")
- ✅ **Aprende** de cada incidencia resuelta
- ✅ **Hereda** el conocimiento para futuros casos
- ✅ **Conversa** en lenguaje natural (no formularios)

---

## 🚀 PROBAR EL SISTEMA (5 minutos)

### Requisitos
- Computadora con Windows, Mac o Linux
- Python 3.10 o superior ([Descargar Python](https://www.python.org/downloads/))

### Instalación Rápida

**1. Descargar el proyecto**
```
Haz clic en el botón verde "Code" → "Download ZIP"
Descomprime el archivo en tu computadora
```

**2. Abrir Terminal/CMD en la carpeta del proyecto**
- **Windows**: Abre la carpeta, clic derecho → "Abrir en Terminal"
- **Mac/Linux**: Abre Terminal, escribe `cd ` y arrastra la carpeta

**3. Ejecutar estos comandos (uno por uno)**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**4. Abrir en el navegador**
```
http://localhost:8000
```

¡Listo! Ya puedes usar PR-System.

---

## 📖 Cómo Usar el Sistema

### Paso 1: Crear una Incidencia
1. Clic en **"+ Nueva Incidencia"**
2. Describe el problema (ejemplo: "Punto frío en soldadura, línea 3")
3. El sistema buscará casos similares automáticamente

### Paso 2: Agregar Reportes
- Cada persona involucrada puede agregar su versión de los hechos
- Clic en la incidencia → "Agregar Reporte"

### Paso 3: Resolver
- Cuando se resuelva, clic en **"Marcar Resuelto"**
- Describe la solución aplicada
- El caso se agrega automáticamente a la base de conocimiento

### Paso 4: Consultar el Sistema
- Ve a **"Consultar Sistema"**
- Pregunta: "¿Qué casos de soldadura hemos tenido?"
- El sistema responderá basándose en casos anteriores

### Paso 5: Subir Documentos (ISO, manuales, etc.)
- Ve a **"Documentos"**
- Arrastra archivos .txt o .md
- Quedan disponibles para consultas futuras

---

## ⚙️ Configurar el Cerebro (LLM)

El sistema necesita un "cerebro" para responder preguntas. Tienes 3 opciones:

### Opción A: Ollama (GRATIS, 100% Privado)
Requiere descargar e instalar Ollama:
1. Descarga: https://ollama.ai/download
2. Abre terminal y ejecuta: `ollama pull llama3`
3. En PR-System → Configuración → Selecciona "Ollama"

### Opción B: OpenAI (Pago, muy rápido)
1. Obtén API Key: https://platform.openai.com/api-keys
2. En PR-System → Configuración → Selecciona "OpenAI"
3. Pega tu API Key

### Opción C: Sin LLM (Solo búsqueda)
Si no configuras ningún LLM, el sistema aún puede:
- Guardar incidencias
- Buscar casos similares
- Subir documentos

Solo no podrá generar respuestas en lenguaje natural.

---

## 🎯 Casos de Uso

| Área | Ejemplo |
|------|---------|
| **Calidad** | "¿Cómo resolvimos el problema de dimensiones fuera de especificación?" |
| **Mantenimiento** | "¿Qué fallas ha tenido la máquina CNC-05?" |
| **Producción** | "¿Qué ajustes funcionaron para el material X?" |
| **Ingeniería** | "¿Por qué se eligió el proveedor Y sobre Z?" |

---

## ❓ Problemas Comunes

### "No puedo instalar las dependencias"
```bash
# Intenta con:
python3 -m pip install -r requirements.txt

# O en Windows:
py -m pip install -r requirements.txt
```

### "El puerto 8000 está ocupado"
```bash
# Usa otro puerto:
python -m uvicorn main:app --port 8080
# Y abre http://localhost:8080
```

### "Error de conexión con LLM"
- Verifica que Ollama esté corriendo (`ollama list`)
- O que tu API Key sea correcta
- Prueba en Configuración → "Probar Conexión"

---

## 📁 Estructura del Proyecto

```
PR/
├── backend/
│   ├── main.py          ← Servidor (no tocar)
│   └── requirements.txt ← Dependencias
├── frontend/
│   └── index.html       ← Interfaz web
└── README.md            ← Este archivo
```

---

## 💡 La Idea Detrás de PR-System

```
SISTEMA TRADICIONAL          PR-SYSTEM
─────────────────────        ─────────────────────
Tú buscas información   →    El sistema te aconseja
Cada caso empieza de 0  →    Cada caso hereda todo
Llenas formatos         →    Conversas naturalmente  
El conocimiento se va   →    El conocimiento queda
con la gente                 en el sistema
```

---

**PR-System v1.0** | César Castro López | 2024

*"El ingeniero con 20 años de experiencia puede renunciar. Su conocimiento ya está en el sistema."*
