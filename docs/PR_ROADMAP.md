# PR-System: Roadmap de Implementación

**Versión:** 1.0
**Fecha:** Febrero 2026
**Autor:** César Castro López

---

## VISIÓN

> Convertir **PR-System** de un prototipo funcional a una **plataforma empresarial**
> de conocimiento vivo, accesible desde cualquier canal donde trabaje la gente.

---

## DOCUMENTOS CREADOS

| Documento | Descripción | Prioridad | Estado |
|-----------|-------------|-----------|--------|
| [PR_ANALISIS.md](./PR_ANALISIS.md) | Análisis de objetivo vs opciones tecnológicas | - | ✅ Completo |
| [PR_CODIGO.md](./PR_CODIGO.md) | Módulo PR-Agent (lógica core) | P1 | ✅ Especificado |
| [PR_BAILEYS.md](./PR_BAILEYS.md) | Integración WhatsApp | P2 | ✅ Especificado |
| [PR_TELEGRAM.md](./PR_TELEGRAM.md) | Integración Telegram | P2 | ✅ Especificado |
| [PR_DOCKER.md](./PR_DOCKER.md) | Containerización y deployment | P2 | ✅ Especificado |
| [PR_OLLAMA.md](./PR_OLLAMA.md) | Configuración de modelos LLM | P3 | ✅ Especificado |
| [PR_ENTERPRISE.md](./PR_ENTERPRISE.md) | Deployment empresarial | P3 | ✅ Especificado |

---

## FASES DE IMPLEMENTACIÓN

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   FASE 1: CORE                FASE 2: CANALES        FASE 3: DEPLOY│
│   ─────────────               ───────────────        ──────────────│
│                                                                     │
│   ┌─────────────┐            ┌─────────────┐        ┌─────────────┐│
│   │ PR_CODIGO   │ ────────▶  │ PR_BAILEYS  │ ─────▶ │ PR_DOCKER   ││
│   │             │            │ PR_TELEGRAM │        │             ││
│   └─────────────┘            └─────────────┘        └─────────────┘│
│         │                          │                      │        │
│         ▼                          ▼                      ▼        │
│   ┌─────────────┐            ┌─────────────┐        ┌─────────────┐│
│   │ PR_OLLAMA   │            │   Testing   │        │PR_ENTERPRISE││
│   │             │            │   & QA      │        │             ││
│   └─────────────┘            └─────────────┘        └─────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## FASE 1: CORE (Fundamentos)

### Objetivo
Implementar la **lógica PR** que diferencia este sistema de cualquier otro.

### Entregables

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| PRAgent | `pr_agent/agent.py` | Clase principal, orquesta el ciclo PR |
| CicloPR | `pr_agent/ciclo.py` | 3 preguntas: Antes, Durante, Después |
| SistemaVersiones | `pr_agent/versiones.py` | Versionado v1.0 → v1.1 → v1.2 |
| MemoriaPR | `pr_agent/memoria.py` | Wrapper inteligente para ChromaDB |
| Endpoints | `main.py` | Nuevos endpoints `/api/pr/*` |

### Criterios de Éxito
- [ ] Crear incidencia busca automáticamente casos similares
- [ ] Resolver incidencia crea nueva versión en RAG
- [ ] Sistema responde: "¿Qué aprendimos la última vez?"

### Dependencias
- Backend actual funcionando ✅
- ChromaDB configurado ✅
- Ollama disponible ✅

---

## FASE 2: CANALES (Accesibilidad)

### Objetivo
Llevar PR-System **donde trabaja la gente**: WhatsApp y Telegram.

### Entregables

| Canal | Tecnología | Costo | Complejidad |
|-------|------------|-------|-------------|
| WhatsApp | Baileys (Node.js) | Gratis | Media |
| Telegram | Bot API (Python) | Gratis | Baja |

### Criterios de Éxito
- [ ] Reportar problema desde WhatsApp
- [ ] Recibir casos similares en respuesta
- [ ] Documentar solución conversacionalmente

### Dependencias
- Fase 1 completa
- Cuenta WhatsApp para bot
- Bot creado en @BotFather

---

## FASE 3: DEPLOYMENT (Producción)

### Objetivo
Empaquetar para **instalación empresarial** con un comando.

### Entregables

| Componente | Descripción |
|------------|-------------|
| docker-compose.yml | Orquestación completa |
| Dockerfiles | Imágenes optimizadas |
| nginx.conf | Proxy reverso con SSL |
| install.sh | Script de instalación |
| Makefile | Comandos de administración |

### Criterios de Éxito
- [ ] `docker compose up -d` levanta todo el sistema
- [ ] Backups automáticos funcionando
- [ ] Health checks pasando

### Dependencias
- Fases 1 y 2 completas
- Hardware disponible
- Dominio/SSL (producción)

---

## TIMELINE SUGERIDO

```
Semana 1-2: FASE 1 (Core)
├── Día 1-3: Implementar pr_agent/
├── Día 4-5: Integrar con main.py
├── Día 6-7: Testing y ajustes
└── Día 8-10: Optimizar prompts

Semana 3-4: FASE 2 (Canales)
├── Día 1-3: WhatsApp (Baileys)
├── Día 4-5: Telegram Bot
└── Día 6-7: Testing multicanal

Semana 5-6: FASE 3 (Deployment)
├── Día 1-3: Docker Compose
├── Día 4-5: Testing de instalación
└── Día 6-7: Documentación final
```

---

## STACK TECNOLÓGICO FINAL

```
┌─────────────────────────────────────────────────────────────┐
│                    PR-SYSTEM v2.0                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FRONTEND           CANALES            BACKEND              │
│  ─────────          ───────            ───────              │
│  HTML/CSS/JS        WhatsApp           FastAPI              │
│  (existente)        (Baileys)          Python 3.11          │
│                     Telegram           PR-Agent             │
│                     (Bot API)          ChromaDB             │
│                                        SQLite               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LLM                INFRA              EXTRAS               │
│  ───                ─────              ──────               │
│  Ollama             Docker             Prometheus           │
│  llama3.2:3b        Nginx              Backups              │
│  (local)            Volumes            SSL/TLS              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## DECISIONES CLAVE

### ¿Por qué NO OpenClaw?

| Razón | Detalle |
|-------|---------|
| Overkill | 90% de funcionalidad no se usa |
| Dependencia | Proyecto externo con updates frecuentes |
| Complejidad | Node.js + configuración extensa |
| No alineado | No diseñado para "conocimiento vivo" |

### ¿Por qué SÍ Ollama + Código propio?

| Razón | Detalle |
|-------|---------|
| Privacidad | 100% local, datos nunca salen |
| Costo | Gratis, solo hardware |
| Control | Código propio, sin dependencias externas |
| Simplicidad | Python + FastAPI, stack conocido |
| Alineado | Diseñado específicamente para PR |

---

## PRÓXIMOS PASOS

1. **Revisar** este documento y los 6 documentos de especificación
2. **Decidir** si el alcance es correcto
3. **Priorizar** qué implementar primero
4. **Comenzar** con Fase 1 (PR_CODIGO)

---

## ESTRUCTURA FINAL DEL PROYECTO

```
PR/
├── main.py                    # Backend principal
├── pr_agent/                  # NUEVO: Lógica PR
│   ├── __init__.py
│   ├── agent.py
│   ├── ciclo.py
│   ├── versiones.py
│   ├── memoria.py
│   └── prompts.py
├── channels/                  # NUEVO: Canales de comunicación
│   ├── whatsapp/
│   │   ├── package.json
│   │   └── src/
│   └── telegram/
│       ├── requirements.txt
│       └── bot.py
├── docker/                    # NUEVO: Infraestructura
│   ├── backend/
│   ├── nginx/
│   └── ollama/
├── docs/                      # NUEVO: Documentación
│   ├── PR_ANALISIS.md
│   ├── PR_CODIGO.md
│   ├── PR_BAILEYS.md
│   ├── PR_TELEGRAM.md
│   ├── PR_DOCKER.md
│   ├── PR_OLLAMA.md
│   ├── PR_ENTERPRISE.md
│   └── PR_ROADMAP.md
├── docker-compose.yml         # NUEVO: Orquestación
├── Makefile                   # NUEVO: Comandos
├── install.sh                 # NUEVO: Instalación
├── index.html                 # Frontend existente
├── requirements.txt           # Dependencias existentes
├── start.py                   # Script inicio existente
└── README.md                  # Actualizar
```

---

## CONTACTO

**Autor:** César Castro López
**Proyecto:** PR-System (Debug-First Design)
**Repositorio:** https://github.com/srexcel/PR

---

*Este documento es checkpoint v1.0 del Roadmap*
*v1.1 viene después del siguiente error*

---

> "Los LLM ya hacen PR. Nadie se había dado cuenta.
> PR simplemente le da propósito."
