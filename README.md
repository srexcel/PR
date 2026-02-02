# 🧠 PR-System: Sistema de Conocimiento Vivo

> **El conocimiento de tu empresa ya no se pierde. El conocimiento vive.**

[![Demo](https://img.shields.io/badge/🎮_DEMO-Probar_Ahora-orange?style=for-the-badge)](https://srexcel.github.io/PR/demo.html)
[![GitHub](https://img.shields.io/badge/GitHub-Repositorio-blue?style=for-the-badge&logo=github)](https://github.com/srexcel/PR)

---

## 🎮 Demo Interactiva (Sin Instalar Nada)

### 👉 [https://srexcel.github.io/PR/demo.html](https://srexcel.github.io/PR/demo.html)

Prueba el ciclo PR completo:
1. Reporta un problema
2. El sistema busca casos similares
3. Documenta la solución
4. El conocimiento se hereda como versión

---

## 📊 Estado del Proyecto

### ✅ Fase 1: PR-Agent (COMPLETADA)

| Componente | Estado | Descripción |
|------------|--------|-------------|
| `pr_agent/ciclo.py` | ✅ | Ciclo de 3 preguntas (ANTES/DURANTE/DESPUÉS) |
| `pr_agent/versiones.py` | ✅ | Versionado semántico (AREA_v1.0, v1.1...) |
| `pr_agent/memoria.py` | ✅ | Wrapper RAG para ChromaDB |
| `pr_agent/prompts.py` | ✅ | Templates LLM para metodología PR |
| `pr_agent/agent.py` | ✅ | Orquestador principal |
| `tests/test_pr_agent.py` | ✅ | 18 tests unitarios |

### ✅ Infraestructura (COMPLETADA)

| Componente | Estado | Descripción |
|------------|--------|-------------|
| FastAPI Backend | ✅ | API REST completa |
| ChromaDB RAG | ✅ | Búsqueda semántica |
| Ollama Integration | ✅ | LLM local (llama3.2:1b) |
| JWT Authentication | ✅ | Autenticación segura |
| Demo Web | ✅ | GitHub Pages |
| Windows Installer | ✅ | instalador_windows.bat |

### 🔄 Próximas Fases

| Fase | Componente | Estado | Descripción |
|------|------------|--------|-------------|
| 2 | WhatsApp Bot | 📋 Pendiente | Integración con Baileys |
| 2 | Telegram Bot | 📋 Pendiente | Bot para reportes |
| 3 | Docker | 📋 Pendiente | Containerización |
| 3 | Enterprise | 📋 Pendiente | Multi-tenant, LDAP |

---

## 🚀 Instalación

### Opción 1: Windows (Automático)

```batch
# 1. Descargar
git clone https://github.com/srexcel/PR.git
cd PR

# 2. Ejecutar instalador (como administrador)
instalador_windows.bat

# 3. Iniciar sistema
iniciar_pr.bat
```

### Opción 2: Linux/Mac (Manual)

```bash
# 1. Clonar
git clone https://github.com/srexcel/PR.git
cd PR

# 2. Entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Ollama (LLM local)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b

# 5. Iniciar
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Acceso
- **URL:** http://localhost:8000
- **Usuario:** admin
- **Contraseña:** admin123

---

## 📖 ¿Qué es PR-System?

Sistema que **aprende** de cada problema resuelto en tu empresa. A diferencia de ISO, ERPs o SharePoint que solo guardan documentos muertos, PR-System:

- ✅ **Aconseja** cuando reportas un problema nuevo ("Encontré 3 casos similares...")
- ✅ **Aprende** de cada incidencia resuelta
- ✅ **Hereda** el conocimiento para futuros casos
- ✅ **Conversa** en lenguaje natural (no formularios)

### Metodología Debug-First Design

```
┌─────────────────────────────────────────────────────────┐
│                    CICLO PR                             │
│                                                         │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│   │ ANTES   │───▶│ DURANTE │───▶│ DESPUÉS │           │
│   │¿Dónde   │    │¿Cómo    │    │¿Qué     │           │
│   │ estoy?  │    │ falla?  │    │ aprendí?│           │
│   └─────────┘    └─────────┘    └─────────┘           │
│        │                              │                │
│        │      CONOCIMIENTO            │                │
│        └──────── HEREDADO ◀───────────┘                │
│                                                         │
│   Axiomas:                                              │
│   • Axioma 0: Asume fracaso                            │
│   • Axioma 1: No hay meta final                        │
│   • Axioma 2: Todo colapsa                             │
│   • Axioma 3: Error = dato valioso                     │
└─────────────────────────────────────────────────────────┘
```

### Versionado de Conocimiento

```
SOLDADURA_v1.0  →  Problema: electrodos desgastados
SOLDADURA_v1.1  →  Problema: humedad en gas CO2
SOLDADURA_v2.0  →  Nuevo proceso implementado

MANTENIMIENTO_v1.0  →  Problema: rodamientos sin lubricar
```

---

## 🔌 API Endpoints

### PR-Agent

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/pr/problema` | Reportar problema (inicia ciclo) |
| POST | `/api/pr/resolver/{id}` | Cerrar ciclo (heredar conocimiento) |
| POST | `/api/pr/consultar` | Consultar RAG + LLM |
| GET | `/api/pr/estadisticas` | Estadísticas del sistema |
| GET | `/api/pr/versiones` | Listar versiones de conocimiento |
| GET | `/api/pr/versiones/{area}/historial` | Historial de un área |

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/login` | Obtener token JWT |
| GET | `/api/auth/me` | Usuario actual |

---

## 📁 Estructura del Proyecto

```
PR/
├── main.py                 # API FastAPI principal
├── start.py                # Script de inicio
├── requirements.txt        # Dependencias Python
├── index.html              # Frontend principal
├── demo.html               # Demo interactiva (GitHub Pages)
│
├── pr_agent/               # 🧠 Módulo PR-Agent
│   ├── __init__.py
│   ├── agent.py            # Orquestador principal
│   ├── ciclo.py            # Ciclo de 3 preguntas
│   ├── versiones.py        # Sistema de versionado
│   ├── memoria.py          # Wrapper RAG (ChromaDB)
│   └── prompts.py          # Templates LLM
│
├── tests/                  # Tests unitarios
│   └── test_pr_agent.py    # 18 tests
│
├── docs/                   # Documentación técnica
│   ├── PR_ANALISIS.md
│   ├── PR_CODIGO.md
│   ├── PR_OLLAMA.md
│   ├── PR_BAILEYS.md
│   ├── PR_TELEGRAM.md
│   ├── PR_DOCKER.md
│   ├── PR_ENTERPRISE.md
│   └── PR_ROADMAP.md
│
├── instalador_windows.bat  # Instalador automático Windows
├── iniciar_pr.bat          # Script de inicio Windows
├── installer.py            # Instalador Python (→ .exe)
├── INSTALL_WINDOWS.md      # Guía instalación Windows
│
└── .github/
    └── workflows/
        └── pages.yml       # Deploy GitHub Pages
```

---

## 🧪 Tests

```bash
# Ejecutar tests
source venv/bin/activate
pytest tests/test_pr_agent.py -v

# Resultado esperado: 18 passed
```

---

## ⚙️ Configuración LLM

### Ollama (Recomendado - 100% Privado)

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo
ollama pull llama3.2:1b    # Ligero (1.3GB)
ollama pull llama3         # Completo (4.7GB)
ollama pull mistral        # Alternativa (4.4GB)
```

### Configurar en PR-System

1. Iniciar servidor: `python -m uvicorn main:app --port 8000`
2. Login: admin / admin123
3. Ir a Configuración
4. Seleccionar modelo Ollama

---

## 🎯 Casos de Uso

| Área | Ejemplo de Consulta |
|------|---------------------|
| **Calidad** | "¿Cómo resolvimos el problema de dimensiones fuera de especificación?" |
| **Mantenimiento** | "¿Qué fallas ha tenido la máquina CNC-05?" |
| **Producción** | "¿Qué ajustes funcionaron para el material X?" |
| **Ingeniería** | "¿Por qué se eligió el proveedor Y sobre Z?" |

---

## 🤝 Contribuir

```bash
# Fork del repositorio
# Crear rama feature
git checkout -b feature/nueva-funcionalidad

# Commits
git commit -m "feat: descripción del cambio"

# Push y crear PR
git push origin feature/nueva-funcionalidad
```

---

## 📞 Soporte

- **Issues:** [github.com/srexcel/PR/issues](https://github.com/srexcel/PR/issues)
- **Demo:** [srexcel.github.io/PR/demo.html](https://srexcel.github.io/PR/demo.html)

---

## 📜 Licencia

MIT License - César Castro López - 2024

---

> *"El ingeniero con 20 años de experiencia puede renunciar. Su conocimiento ya está en el sistema."*
