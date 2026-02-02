"""
Prompts PR: Templates para Interacción con LLM
==============================================

Prompts optimizados para el sistema PR que guían al LLM
a comportarse según la metodología Debug-First Design.

Filosofía:
- Siempre buscar en el pasado primero
- Error = dato valioso
- Documentar para heredar
- Cada caso mejora el sistema
"""

# ============================================================
# SYSTEM PROMPT PRINCIPAL
# ============================================================

SYSTEM_PROMPT_PR = """Eres un experto en metodología PR (Debug-First Design) y gestión de conocimiento empresarial.

Tu rol es ayudar a resolver problemas industriales basándote en casos históricos de la empresa.

## AXIOMAS PR QUE SIGUES:
- Axioma 0: Asume fracaso - Siempre considera qué puede salir mal
- Axioma 1: No hay meta final - Solo hay siguiente iteración
- Axioma 2: Todo colapsa - Prepárate para fallos
- Axioma 3: Error = dato - Los fallos son información valiosa

## TU COMPORTAMIENTO:
1. SIEMPRE pregunta primero: "¿Qué aprendimos la última vez que pasó esto?"
2. Si hay casos similares en el contexto, MENCIÓNALOS primero
3. Si no hay casos similares, ayuda a DOCUMENTAR el nuevo caso
4. Sé CONCISO y DIRECTO
5. Usa ESPAÑOL siempre
6. Estructura tus respuestas cuando sea apropiado

## CUANDO ANALICES UN PROBLEMA:
1. Identifica palabras clave del problema
2. Relaciona con casos anteriores si los hay
3. Sugiere soluciones basadas en histórico
4. Si es nuevo, guía la documentación completa

## FORMATO DE RESPUESTA:
Cuando respondas sobre un problema, usa esta estructura si es apropiada:

**Análisis del Problema:**
[Tu análisis]

**Casos Relacionados:**
[Referencias a casos similares si existen]

**Recomendación:**
[Tu sugerencia de acción]

**Para Documentar:**
[Qué información adicional se necesita]
"""


# ============================================================
# PROMPTS DE ANÁLISIS
# ============================================================

PROMPT_ANALISIS_SIMILITUD = """Analiza si el siguiente problema nuevo es similar a los casos históricos proporcionados.

## PROBLEMA NUEVO:
{problema_nuevo}

## CASOS HISTÓRICOS:
{casos_historicos}

## RESPONDE EN ESTE FORMATO:

### 1. CASO MÁS SIMILAR
- Versión: [identificador del caso]
- Similitud: [porcentaje estimado]
- Razón: [por qué es similar]

### 2. ELEMENTOS COMUNES
- [elemento 1]
- [elemento 2]
- ...

### 3. DIFERENCIAS CLAVE
- [diferencia 1]
- [diferencia 2]
- ...

### 4. RECOMENDACIÓN
[Indica si se puede aplicar la solución anterior o si es un caso nuevo]

### 5. INFORMACIÓN ADICIONAL NECESARIA
[Qué preguntas hacer para confirmar]

Sé específico y conciso."""


PROMPT_PREGUNTAS_DOCUMENTACION = """Basándote en este problema reportado, genera preguntas clave para documentar el caso completamente.

## PROBLEMA REPORTADO:
{descripcion}

## ÁREA:
{area}

## GENERA 5 PREGUNTAS que cubran:
1. Temporalidad (cuándo empezó, frecuencia)
2. Acciones previas (qué se ha intentado)
3. Personas involucradas
4. Impacto (qué afecta, magnitud)
5. Condiciones (qué lo reproduce, variables)

Formato: Lista numerada, preguntas directas y específicas.
Evita preguntas genéricas. Adapta al contexto del problema."""


PROMPT_EXTRAER_KEYWORDS = """Extrae las palabras clave más relevantes del siguiente texto para búsqueda.

## TEXTO:
{texto}

## REGLAS:
- Máximo 10 keywords
- Incluye términos técnicos específicos
- Incluye área/equipo mencionado
- Incluye síntomas/problemas
- Excluye palabras comunes

## FORMATO DE RESPUESTA:
keyword1, keyword2, keyword3, ..."""


# ============================================================
# PROMPTS DE DOCUMENTACIÓN
# ============================================================

PROMPT_DOCUMENTO_8D = """Genera un documento 8D profesional basado en la siguiente información.

## INFORMACIÓN DEL CASO:

**Título:** {titulo}
**Área:** {area}
**Prioridad:** {prioridad}
**Fecha de Creación:** {fecha_creacion}

**Descripción del Problema:**
{descripcion}

**Reportes de Involucrados:**
{reportes}

**Solución Aplicada:**
{solucion}

**Causa Raíz Identificada:**
{causa_raiz}

**Acciones Preventivas:**
{acciones_preventivas}

## GENERA EL DOCUMENTO 8D:

### D1 - EQUIPO
[Lista las personas que participaron en la resolución]

### D2 - DESCRIPCIÓN DEL PROBLEMA
[Resumen claro: Qué, Dónde, Cuándo, Magnitud]

### D3 - ACCIONES DE CONTENCIÓN
[Medidas inmediatas tomadas para contener el problema]

### D4 - ANÁLISIS DE CAUSA RAÍZ
[Usa 5 Por Qués o Diagrama de Ishikawa si es apropiado]

### D5 - ACCIONES CORRECTIVAS PERMANENTES
[Soluciones implementadas para eliminar la causa raíz]

### D6 - IMPLEMENTACIÓN Y VALIDACIÓN
[Cómo se verificó que las acciones funcionan]

### D7 - ACCIONES PREVENTIVAS
[Medidas para evitar recurrencia en otros procesos/áreas]

### D8 - RECONOCIMIENTO Y CIERRE
[Lecciones aprendidas y reconocimiento al equipo]

---
Documento generado por PR-System
Fecha: {fecha_generacion}"""


PROMPT_RESUMEN_EJECUTIVO = """Genera un resumen ejecutivo del siguiente caso resuelto.

## CASO:
{caso_completo}

## GENERA UN RESUMEN DE MÁXIMO 200 PALABRAS QUE INCLUYA:
1. Problema en una oración
2. Causa raíz en una oración
3. Solución en una oración
4. Impacto/resultado
5. Lección clave para el futuro

El resumen debe ser útil para que alguien entienda rápidamente
qué pasó y qué se aprendió, sin leer el caso completo."""


# ============================================================
# PROMPTS DE CONSULTA RAG
# ============================================================

PROMPT_CONSULTA_CON_CONTEXTO = """Responde la siguiente consulta usando el conocimiento histórico proporcionado.

## CONTEXTO (Casos anteriores relevantes):
{contexto}

## CONSULTA DEL USUARIO:
{consulta}

## INSTRUCCIONES:
1. Basa tu respuesta en los casos del contexto cuando sea posible
2. Si un caso anterior aplica directamente, menciónalo con su versión
3. Si no hay casos relevantes, indícalo claramente
4. Sugiere documentar si es un caso nuevo
5. Sé práctico y orientado a la acción

## RESPUESTA:"""


PROMPT_CONSULTA_SIN_CONTEXTO = """El usuario hace la siguiente consulta, pero no hay casos similares en la base de conocimiento.

## CONSULTA:
{consulta}

## INSTRUCCIONES:
1. Proporciona orientación general basada en buenas prácticas
2. Indica que no hay casos históricos documentados
3. Sugiere que este podría ser un caso nuevo a documentar
4. Pregunta si quiere crear una incidencia para empezar a construir el conocimiento

## RESPUESTA:"""


# ============================================================
# PROMPTS DE VALIDACIÓN
# ============================================================

PROMPT_VALIDAR_SOLUCION = """Evalúa si la siguiente solución propuesta es adecuada para el problema descrito.

## PROBLEMA:
{problema}

## SOLUCIÓN PROPUESTA:
{solucion}

## EVALÚA:
1. ¿La solución aborda la causa raíz?
2. ¿Es implementable con los recursos típicos?
3. ¿Tiene efectos secundarios potenciales?
4. ¿Se puede verificar su efectividad?

## FORMATO DE RESPUESTA:
**Evaluación:** [Adecuada / Parcialmente adecuada / Inadecuada]
**Razón:** [Explicación breve]
**Mejoras sugeridas:** [Si aplica]
**Riesgos a considerar:** [Si aplica]"""


PROMPT_COMPLETITUD_DOCUMENTACION = """Evalúa si la siguiente documentación de caso está completa.

## DOCUMENTACIÓN:
{documentacion}

## VERIFICA QUE INCLUYA:
- [ ] Descripción clara del problema
- [ ] Cuándo y dónde ocurrió
- [ ] Quién reportó / está involucrado
- [ ] Qué acciones se tomaron
- [ ] Resultado de las acciones
- [ ] Causa raíz identificada
- [ ] Solución final
- [ ] Acciones preventivas

## RESPUESTA:
**Completitud:** [X/8 elementos]
**Faltantes:** [Lista de lo que falta]
**Preguntas para completar:** [Preguntas específicas]"""


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def formatear_casos_para_prompt(casos: list) -> str:
    """
    Formatea una lista de casos para incluir en un prompt.

    Args:
        casos: Lista de casos con contenido y metadata

    Returns:
        String formateado para incluir en prompt
    """
    if not casos:
        return "No hay casos históricos disponibles."

    resultado = []
    for i, caso in enumerate(casos, 1):
        texto = f"### Caso {i}"

        if caso.get('metadata'):
            meta = caso['metadata']
            if meta.get('version'):
                texto += f" ({meta['version']})"
            if meta.get('area'):
                texto += f"\n**Área:** {meta['area']}"
            if meta.get('fecha'):
                texto += f"\n**Fecha:** {meta['fecha']}"

        if caso.get('relevancia_pct'):
            texto += f"\n**Relevancia:** {caso['relevancia_pct']}"

        texto += f"\n\n{caso.get('contenido', 'Sin contenido')}\n"

        resultado.append(texto)

    return "\n---\n".join(resultado)


def construir_prompt(template: str, **kwargs) -> str:
    """
    Construye un prompt a partir de un template y variables.

    Args:
        template: Template con placeholders {variable}
        **kwargs: Variables a sustituir

    Returns:
        Prompt construido
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Falta variable en prompt: {e}")


# ============================================================
# MENSAJES DE RESPUESTA
# ============================================================

MENSAJES = {
    "casos_encontrados": "Encontré {n} caso(s) similar(es) en la base de conocimiento.",
    "sin_casos": "No encontré casos similares. Este parece ser un caso nuevo.",
    "documentar_nuevo": "Vamos a documentar este caso para que sirva en el futuro.",
    "solucion_heredada": "Este caso se documentó como {version}. El sistema aprendió de él.",
    "error_busqueda": "Hubo un error buscando en la base de conocimiento.",
    "ciclo_cerrado": "Ciclo PR cerrado. Conocimiento heredado como {version}.",
}


def obtener_mensaje(clave: str, **kwargs) -> str:
    """Obtiene un mensaje formateado"""
    template = MENSAJES.get(clave, clave)
    return template.format(**kwargs)
