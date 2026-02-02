# PR_OLLAMA: Configuración de Modelos LLM

**Versión:** 1.0
**Prioridad:** P3 - MEDIA
**Dependencias:** PR_CODIGO (P1), PR_DOCKER (P2)

---

## 1. OBJETIVO

Configurar **Ollama** como el cerebro de PR-System, optimizando para:
- Español como idioma principal
- Tareas de análisis y comparación
- Hardware disponible (con/sin GPU)
- Balance costo/rendimiento

---

## 2. ¿POR QUÉ OLLAMA?

| Característica | Ollama | OpenAI | Anthropic |
|----------------|--------|--------|-----------|
| Costo | GRATIS | $$$$ | $$$$ |
| Privacidad | 100% local | Datos a servidor | Datos a servidor |
| Sin internet | ✓ Sí | ✗ No | ✗ No |
| Latencia | ~1-5s | ~2-10s | ~2-10s |
| Control | Total | Ninguno | Ninguno |

**Para empresas:** Los datos de producción, calidad y mantenimiento son **confidenciales**. Enviarlos a servidores externos es inaceptable para muchas organizaciones.

---

## 3. MODELOS RECOMENDADOS

### 3.1 Sin GPU (Solo CPU)

| Modelo | Tamaño | RAM Requerida | Caso de Uso |
|--------|--------|---------------|-------------|
| `llama3.2:1b` | 1.3 GB | 4 GB | Pruebas rápidas |
| `llama3.2:3b` | 2.0 GB | 6 GB | **Recomendado** |
| `phi3:mini` | 2.3 GB | 6 GB | Alternativa eficiente |
| `qwen2.5:3b` | 1.9 GB | 6 GB | Buen español |

**Recomendación sin GPU:** `llama3.2:3b`

### 3.2 Con GPU (NVIDIA)

| Modelo | VRAM | Calidad | Caso de Uso |
|--------|------|---------|-------------|
| `llama3.2:3b` | 3 GB | Buena | GPU básica |
| `mistral:7b` | 5 GB | Muy buena | **Recomendado** |
| `llama3.1:8b` | 6 GB | Excelente | GPU media |
| `qwen2.5:14b` | 10 GB | Superior | GPU alta |
| `mixtral:8x7b` | 26 GB | Óptima | GPU profesional |

**Recomendación con GPU:** `mistral:7b` o `llama3.1:8b`

### 3.3 Comparativa de Rendimiento

| Modelo | Tokens/s (CPU) | Tokens/s (GPU) | Calidad Español |
|--------|----------------|----------------|-----------------|
| llama3.2:1b | 15-25 | 40-60 | ⭐⭐⭐ |
| llama3.2:3b | 8-15 | 30-50 | ⭐⭐⭐⭐ |
| mistral:7b | 3-8 | 25-40 | ⭐⭐⭐⭐ |
| llama3.1:8b | 2-5 | 20-35 | ⭐⭐⭐⭐⭐ |

---

## 4. INSTALACIÓN DE OLLAMA

### 4.1 Linux

```bash
# Instalación
curl -fsSL https://ollama.com/install.sh | sh

# Verificar
ollama --version

# Iniciar servicio
sudo systemctl start ollama
sudo systemctl enable ollama
```

### 4.2 Windows

1. Descargar desde: https://ollama.com/download/windows
2. Ejecutar instalador
3. Ollama se inicia automáticamente

### 4.3 macOS

```bash
# Con Homebrew
brew install ollama

# O descargar desde: https://ollama.com/download/mac
```

### 4.4 Docker (Recomendado para PR-System)

```yaml
# Ya incluido en docker-compose.yml
ollama:
  image: ollama/ollama:latest
  volumes:
    - ollama-models:/root/.ollama
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

---

## 5. DESCARGA DE MODELOS

### 5.1 Comando Básico

```bash
# Descargar modelo
ollama pull llama3.2:3b

# Ver modelos instalados
ollama list

# Eliminar modelo
ollama rm nombre_modelo

# Información del modelo
ollama show llama3.2:3b
```

### 5.2 Modelos para PR-System

```bash
# Modelo principal (recomendado)
ollama pull llama3.2:3b

# Modelo alternativo (mejor calidad, más lento)
ollama pull mistral:7b

# Modelo para embeddings (opcional, mejora RAG)
ollama pull nomic-embed-text
```

### 5.3 Verificar Descarga

```bash
# Probar modelo
ollama run llama3.2:3b "Hola, ¿cómo estás?"

# Ver uso de recursos
ollama ps
```

---

## 6. CONFIGURACIÓN EN PR-SYSTEM

### 6.1 Variables de Entorno

```env
# .env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=120
```

### 6.2 Configuración en main.py

```python
# main.py - Sección de configuración

# Configuración por defecto para Ollama
cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('llm_provider', 'ollama')")
cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('llm_model', 'llama3.2:3b')")
cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('ollama_url', 'http://localhost:11434')")
```

### 6.3 Cambiar Modelo en Runtime

```bash
# Via API
curl -X POST http://localhost:8000/api/configuracion \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "mistral:7b"}'
```

---

## 7. OPTIMIZACIÓN DE PROMPTS

### 7.1 System Prompt Optimizado para PR

```python
# pr_agent/prompts.py

SYSTEM_PROMPT_PR = """Eres un experto en metodología PR (Debug-First Design) y gestión de conocimiento empresarial.

Tu rol es ayudar a resolver problemas industriales basándote en casos históricos.

REGLAS:
1. Siempre responde en ESPAÑOL
2. Sé CONCISO y DIRECTO
3. Si hay casos similares, menciónalos primero
4. Si no hay casos, ayuda a documentar el nuevo
5. Usa formato estructurado cuando sea apropiado

CONTEXTO PR:
- Axioma 0: Asume que todo puede fallar
- Axioma 3: Cada error es un dato valioso
- Pregunta clave: "¿Qué aprendimos la última vez?"

Cuando analices un problema:
1. Identifica palabras clave
2. Busca patrones con casos anteriores
3. Sugiere soluciones basadas en histórico
4. Si es nuevo, guía la documentación"""
```

### 7.2 Prompt para Análisis de Similitud

```python
PROMPT_ANALISIS_SIMILITUD = """Analiza si el siguiente problema nuevo es similar a los casos históricos.

PROBLEMA NUEVO:
{problema_nuevo}

CASOS HISTÓRICOS:
{casos_historicos}

Responde en formato estructurado:
1. CASO MÁS SIMILAR: [versión del caso]
2. PORCENTAJE DE SIMILITUD: [0-100%]
3. ELEMENTOS COMUNES: [lista]
4. DIFERENCIAS CLAVE: [lista]
5. RECOMENDACIÓN: [aplicar solución anterior / documentar como nuevo]

Sé específico y conciso."""
```

### 7.3 Prompt para Generación de Documento 8D

```python
PROMPT_DOCUMENTO_8D = """Genera un documento 8D basado en la siguiente información.

TÍTULO: {titulo}
ÁREA: {area}
DESCRIPCIÓN: {descripcion}
REPORTES: {reportes}
SOLUCIÓN: {solucion}

Formato 8D requerido:

D1 - EQUIPO:
[Personas involucradas en la resolución]

D2 - DESCRIPCIÓN DEL PROBLEMA:
[Resumen claro y específico]

D3 - ACCIONES DE CONTENCIÓN:
[Medidas inmediatas tomadas]

D4 - ANÁLISIS DE CAUSA RAÍZ:
[Identificación de la causa principal]

D5 - ACCIONES CORRECTIVAS:
[Soluciones implementadas]

D6 - IMPLEMENTACIÓN Y VALIDACIÓN:
[Cómo se verificó la efectividad]

D7 - ACCIONES PREVENTIVAS:
[Medidas para evitar recurrencia]

D8 - RECONOCIMIENTO DEL EQUIPO:
[Cierre y lecciones aprendidas]

Genera el documento completo y profesional."""
```

---

## 8. CONFIGURACIÓN AVANZADA

### 8.1 Modelfile Personalizado

Crear modelo optimizado para PR-System:

```dockerfile
# Modelfile.pr-system
FROM llama3.2:3b

# Parámetros optimizados
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096
PARAMETER repeat_penalty 1.1

# System prompt embebido
SYSTEM """Eres un experto en metodología PR (Debug-First Design).
Respondes siempre en español, de forma concisa y estructurada.
Tu objetivo es conectar problemas actuales con soluciones históricas."""
```

```bash
# Crear modelo personalizado
ollama create pr-expert -f Modelfile.pr-system

# Usar en PR-System
# Cambiar configuración a: llm_model = "pr-expert"
```

### 8.2 Parámetros de Generación

```python
# Configuración recomendada para PR-System
OLLAMA_PARAMS = {
    "temperature": 0.7,      # Balance creatividad/precisión
    "top_p": 0.9,            # Nucleus sampling
    "top_k": 40,             # Top-k sampling
    "num_ctx": 4096,         # Contexto (casos históricos)
    "repeat_penalty": 1.1,   # Evitar repetición
    "num_predict": 1024,     # Máximo tokens respuesta
}
```

### 8.3 Configuración de GPU

```bash
# Ver GPUs disponibles
nvidia-smi

# Configurar GPU específica
CUDA_VISIBLE_DEVICES=0 ollama serve

# Limitar VRAM (útil si compartes GPU)
OLLAMA_MAX_VRAM=6000000000 ollama serve  # 6GB
```

---

## 9. MONITOREO Y MÉTRICAS

### 9.1 Ver Uso de Recursos

```bash
# Modelos cargados y uso de memoria
ollama ps

# Logs de Ollama
journalctl -u ollama -f

# En Docker
docker compose logs ollama -f
```

### 9.2 Endpoint de Métricas

```python
# Agregar a main.py

@app.get("/api/llm/metrics")
async def metricas_llm(usuario: dict = Depends(obtener_usuario_actual)):
    """Métricas del LLM"""
    import httpx

    ollama_url = get_config("ollama_url") or "http://localhost:11434"

    async with httpx.AsyncClient() as client:
        try:
            # Modelos cargados
            ps_response = await client.get(f"{ollama_url}/api/ps")
            models_loaded = ps_response.json() if ps_response.status_code == 200 else {}

            # Lista de modelos
            tags_response = await client.get(f"{ollama_url}/api/tags")
            models_available = tags_response.json() if tags_response.status_code == 200 else {}

            return {
                "status": "ok",
                "provider": "ollama",
                "url": ollama_url,
                "modelo_configurado": get_config("llm_model"),
                "modelos_cargados": models_loaded,
                "modelos_disponibles": models_available
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

---

## 10. TROUBLESHOOTING

### Ollama no responde

```bash
# Verificar servicio
systemctl status ollama

# Reiniciar
sudo systemctl restart ollama

# Ver logs
journalctl -u ollama -n 50
```

### Modelo muy lento

```bash
# Verificar si está usando GPU
ollama ps
# Si "Processor" dice "CPU", la GPU no está activa

# Verificar CUDA
nvidia-smi

# Reinstalar con soporte GPU
curl -fsSL https://ollama.com/install.sh | sh
```

### Error de memoria

```bash
# Usar modelo más pequeño
ollama pull llama3.2:1b

# O aumentar swap (Linux)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Respuestas en inglés

```python
# Agregar instrucción explícita al prompt
prompt = f"""IMPORTANTE: Responde siempre en ESPAÑOL.

{tu_prompt_original}"""
```

---

## 11. CHECKLIST

- [ ] Instalar Ollama
- [ ] Descargar modelo recomendado
- [ ] Verificar funcionamiento básico
- [ ] Configurar en PR-System
- [ ] Optimizar prompts
- [ ] Probar análisis de similitud
- [ ] Probar generación de documentos
- [ ] Monitorear rendimiento

---

*Este documento es checkpoint v1.0 de PR_OLLAMA*
*v1.1 viene después del siguiente error*
