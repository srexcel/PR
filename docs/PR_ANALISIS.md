# PR-System: Análisis de Objetivo vs Opciones Tecnológicas

**Versión:** 1.0
**Fecha:** Febrero 2026
**Autor:** César Castro López

---

## 1. OBJETIVO DEL PROYECTO PR

### 1.1 Definición Central

> **PR = DEBUG-FIRST DESIGN**
> El proceso natural bajo el cual las cosas sobreviven.

PR no es un software. Es una **metodología** que reconoce que los LLM ya implementan inherentemente un proceso de aprendizaje iterativo. El software es solo el vehículo.

### 1.2 Problema que Resuelve

| Problema | Manifestación | Costo |
|----------|---------------|-------|
| Amnesia organizacional | Mismos errores se repiten | Tiempo, dinero, frustración |
| ISO como "basurero sellado" | Documentos que nadie consulta | Burocracia sin valor |
| Conocimiento en cabezas | Se va cuando la gente se va | Pérdida de expertise |
| No hay conexión de casos | Cada problema es "nuevo" | Reinventar la rueda |

### 1.3 Solución Propuesta

Convertir **memoria en papel** → **memoria en RAM**:

```
ANTES (ISO):
  Problema → Documento → Carpeta → Olvido → Problema de nuevo

DESPUÉS (PR + LLM):
  Problema → Buscar similares → Solución sugerida → Resolver → Heredar → Siguiente versión
```

### 1.4 Los 4 Axiomas

| Axioma | Significado | Implicación Técnica |
|--------|-------------|---------------------|
| **0: Asume fracaso** | Diseña desde el error | Sistema debe ser resiliente |
| **1: No hay meta** | Solo hay siguiente iteración | Versionado continuo (v1.0→v1.1) |
| **2: Todo colapsa** | Prepárate para fallos | Backups, rollback, degradación |
| **3: Error = dato** | Fallos son información | Guardar TODO, incluso errores |

### 1.5 El Ciclo PR (3 Preguntas)

```
┌─────────────────┬─────────────────┬─────────────────┐
│     ANTES       │    DURANTE      │    DESPUÉS      │
│  ¿Dónde estoy?  │  ¿Cómo falla?   │  ¿Qué aprendí?  │
├─────────────────┼─────────────────┼─────────────────┤
│ 1. Checkpoint   │ 4. Degradar     │ 7. Trazar       │
│ 2. Rollback     │ 5. Continuar    │ 8. Depurar      │
│ 3. Declarar     │ 6. Iterar       │ 9. Siguiente    │
└─────────────────┴─────────────────┴─────────────────┘
```

### 1.6 Usuario Objetivo

**Empresas industriales** con:
- Procesos de calidad (8D, APQP, PPAP)
- Equipos de mantenimiento
- Operaciones de producción
- Necesidad de cumplimiento (ISO, IATF)
- Conocimiento crítico en personas

---

## 2. REQUISITOS DERIVADOS DEL OBJETIVO

### 2.1 Requisitos Funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF01 | Buscar casos similares automáticamente | CRÍTICA |
| RF02 | Guardar soluciones en base de conocimiento | CRÍTICA |
| RF03 | Versionar cada aprendizaje (v1.x) | ALTA |
| RF04 | Consultar en lenguaje natural | ALTA |
| RF05 | Acceso desde donde trabaja la gente | ALTA |
| RF06 | Generar documentos formales (8D, etc.) | MEDIA |
| RF07 | Trazabilidad completa | MEDIA |
| RF08 | Backups automáticos | MEDIA |

### 2.2 Requisitos No Funcionales

| ID | Requisito | Prioridad | Razón |
|----|-----------|-----------|-------|
| RNF01 | **Privacidad total** | CRÍTICA | Empresas NO envían datos afuera |
| RNF02 | **Costo operativo mínimo** | CRÍTICA | Debe ser accesible para PyMEs |
| RNF03 | **Instalación simple** | ALTA | IT limitado en muchas empresas |
| RNF04 | **Sin dependencia de internet** | ALTA | Plantas sin conexión estable |
| RNF05 | **Mantenimiento mínimo** | ALTA | No hay equipo dedicado |
| RNF06 | **Escalable** | MEDIA | De 5 a 500 usuarios |

---

## 3. ANÁLISIS DE OPCIONES TECNOLÓGICAS

### 3.1 Opción A: OpenClaw (Fork Completo)

#### Descripción
Tomar el código de OpenClaw, hacer fork, y especializarlo para PR.

#### Mapeo contra Requisitos

| Requisito | Cumple | Notas |
|-----------|--------|-------|
| RF01 Buscar similares | ⚠️ Parcial | Requiere crear skill + RAG externo |
| RF02 Guardar soluciones | ⚠️ Parcial | Requiere integración custom |
| RF03 Versionar | ❌ No | No tiene concepto de versiones |
| RF04 Lenguaje natural | ✅ Sí | Core del sistema |
| RF05 Acceso multicanal | ✅ Sí | WhatsApp, Telegram incluidos |
| RF06 Documentos formales | ⚠️ Parcial | Requiere skill custom |
| RF07 Trazabilidad | ❌ No | No diseñado para esto |
| RF08 Backups | ❌ No | No incluido |
| RNF01 Privacidad | ⚠️ Depende | Si usa Ollama sí, si usa Claude no |
| RNF02 Costo mínimo | ⚠️ Depende | Ollama gratis, Claude $$$ |
| RNF03 Instalación simple | ❌ No | Node.js + npm + configuración |
| RNF04 Sin internet | ⚠️ Parcial | Solo con Ollama |
| RNF05 Mantenimiento mínimo | ❌ No | Actualizaciones frecuentes |
| RNF06 Escalable | ✅ Sí | Arquitectura distribuida |

#### Puntuación: 6/14 requisitos cumplidos

#### Veredicto
```
OpenClaw es OVERKILL para PR-System.

Pros:
+ Canales ya integrados
+ Comunidad activa
+ Extensible

Contras:
- 90% del código no se usa (browser control, filesystem, etc.)
- Complejidad de mantenimiento alta
- Dependencia de proyecto externo
- No alineado con filosofía PR (debug-first)
```

---

### 3.2 Opción B: Ollama Puro (Estado Actual)

#### Descripción
Mantener arquitectura actual: FastAPI + ChromaDB + Ollama

#### Mapeo contra Requisitos

| Requisito | Cumple | Notas |
|-----------|--------|-------|
| RF01 Buscar similares | ✅ Sí | ChromaDB implementado |
| RF02 Guardar soluciones | ✅ Sí | SQLite + ChromaDB |
| RF03 Versionar | ⚠️ Parcial | Básico, mejorable |
| RF04 Lenguaje natural | ✅ Sí | Ollama funciona |
| RF05 Acceso multicanal | ❌ No | Solo web |
| RF06 Documentos formales | ✅ Sí | Endpoint existe |
| RF07 Trazabilidad | ⚠️ Parcial | Básica |
| RF08 Backups | ✅ Sí | Implementado |
| RNF01 Privacidad | ✅ Sí | 100% local |
| RNF02 Costo mínimo | ✅ Sí | Solo hardware |
| RNF03 Instalación simple | ✅ Sí | python start.py |
| RNF04 Sin internet | ✅ Sí | Todo local |
| RNF05 Mantenimiento mínimo | ✅ Sí | Código propio, estable |
| RNF06 Escalable | ⚠️ Parcial | Requiere trabajo |

#### Puntuación: 10/14 requisitos cumplidos

#### Veredicto
```
Ollama Puro es una BASE SÓLIDA.

Pros:
+ Ya funciona
+ Privacidad total
+ Costo cero
+ Simple

Contras:
- Sin canales (WhatsApp, etc.)
- Versionado básico
- Falta lógica PR explícita
```

---

### 3.3 Opción C: Híbrido (Recomendada)

#### Descripción
Ollama como base + módulos propios + canales selectivos

#### Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                    PR-System v2.0                        │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              CAPA DE PRESENTACIÓN                   │ │
│  │   ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐         │ │
│  │   │  Web  │ │WhatsApp│ │Telegram│ │ API  │         │ │
│  │   └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘         │ │
│  └───────┼─────────┼─────────┼─────────┼─────────────┘ │
│          └─────────┴────┬────┴─────────┘               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              PR-AGENT (Lógica de Negocio)          │ │
│  │                                                     │ │
│  │   ┌──────────┐ ┌──────────┐ ┌──────────┐          │ │
│  │   │ Ciclo PR │ │ Versiones│ │ Trazas   │          │ │
│  │   │3 Preguntas│ │  v1.x   │ │ Completas│          │ │
│  │   └──────────┘ └──────────┘ └──────────┘          │ │
│  └───────────────────────┬─────────────────────────────┘ │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              CAPA DE DATOS                          │ │
│  │   ┌──────────┐ ┌──────────┐ ┌──────────┐          │ │
│  │   │  SQLite  │ │ ChromaDB │ │ Backups  │          │ │
│  │   │ Incidenc.│ │   RAG    │ │Automáticos│          │ │
│  │   └──────────┘ └──────────┘ └──────────┘          │ │
│  └───────────────────────┬─────────────────────────────┘ │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                    OLLAMA                           │ │
│  │            llama3.2 / mistral / qwen               │ │
│  │               100% LOCAL Y PRIVADO                  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

#### Mapeo contra Requisitos

| Requisito | Cumple | Implementación |
|-----------|--------|----------------|
| RF01 Buscar similares | ✅ Sí | PR-Agent + ChromaDB |
| RF02 Guardar soluciones | ✅ Sí | PR-Agent + SQLite |
| RF03 Versionar | ✅ Sí | PR-Agent (nuevo) |
| RF04 Lenguaje natural | ✅ Sí | Ollama |
| RF05 Acceso multicanal | ✅ Sí | Baileys + Telegram Bot |
| RF06 Documentos formales | ✅ Sí | PR-Agent + Templates |
| RF07 Trazabilidad | ✅ Sí | PR-Agent (nuevo) |
| RF08 Backups | ✅ Sí | Ya existe |
| RNF01 Privacidad | ✅ Sí | 100% local |
| RNF02 Costo mínimo | ✅ Sí | Solo hardware |
| RNF03 Instalación simple | ✅ Sí | Docker Compose |
| RNF04 Sin internet | ✅ Sí | Todo local |
| RNF05 Mantenimiento mínimo | ✅ Sí | Código propio |
| RNF06 Escalable | ✅ Sí | Docker + opcional k8s |

#### Puntuación: 14/14 requisitos cumplidos

#### Veredicto
```
Híbrido es la OPCIÓN ÓPTIMA.

Razón: Toma lo mejor de cada mundo
+ Base sólida actual (Ollama + FastAPI)
+ Agrega solo lo necesario (canales específicos)
+ Mantiene privacidad y simplicidad
+ Código 100% propio y controlado
+ Alineado con filosofía PR
```

---

## 4. MATRIZ DE DECISIÓN FINAL

| Criterio | Peso | OpenClaw | Ollama Puro | Híbrido |
|----------|------|----------|-------------|---------|
| Cumple requisitos funcionales | 25% | 4/8 (50%) | 6/8 (75%) | 8/8 (100%) |
| Cumple requisitos no funcionales | 25% | 2/6 (33%) | 5/6 (83%) | 6/6 (100%) |
| Privacidad empresarial | 20% | 50% | 100% | 100% |
| Costo total de propiedad | 15% | Alto | Bajo | Bajo |
| Complejidad de mantenimiento | 15% | Alta | Baja | Media |
| **TOTAL PONDERADO** | 100% | **48%** | **83%** | **97%** |

---

## 5. DECISIÓN

### Opción Seleccionada: HÍBRIDO

### Componentes a Desarrollar

| Documento | Descripción | Prioridad |
|-----------|-------------|-----------|
| PR_CODIGO.md | Módulo PR-Agent (lógica core) | P1 - Crítica |
| PR_BAILEYS.md | Integración WhatsApp | P2 - Alta |
| PR_TELEGRAM.md | Integración Telegram | P2 - Alta |
| PR_DOCKER.md | Containerización | P2 - Alta |
| PR_OLLAMA.md | Configuración modelos | P3 - Media |
| PR_ENTERPRISE.md | Deployment empresarial | P3 - Media |

### Roadmap

```
Fase 1 (Core):     PR_CODIGO → PR_OLLAMA
Fase 2 (Canales):  PR_BAILEYS → PR_TELEGRAM
Fase 3 (Deploy):   PR_DOCKER → PR_ENTERPRISE
```

---

## 6. CONCLUSIÓN

> **No reinventamos la rueda. Especializamos las herramientas existentes
> para el propósito específico de PR.**

OpenClaw es un framework genérico para agentes. PR necesita un sistema
especializado en **conocimiento vivo empresarial**.

La opción híbrida permite:
1. Mantener el código actual que ya funciona
2. Agregar la lógica PR que falta
3. Conectar canales donde trabaja la gente
4. Empaquetar para empresas con Docker
5. Crecer según necesidad

---

*Este documento es checkpoint v1.0 del análisis.*
*v1.1 viene después del siguiente aprendizaje.*
