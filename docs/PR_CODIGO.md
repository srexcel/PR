# PR_CODIGO: Módulo PR-Agent

**Versión:** 1.0
**Prioridad:** P1 - CRÍTICA
**Dependencias:** FastAPI (actual), ChromaDB (actual), SQLite (actual)

---

## 1. OBJETIVO

Implementar la **lógica del ciclo PR** como módulo Python que se integra con el backend actual.

Este módulo es el "cerebro" que convierte el sistema actual de gestión de incidencias en un **sistema de conocimiento vivo**.

---

## 2. ARQUITECTURA

```
main.py (actual)
     │
     ├── pr_agent/
     │   ├── __init__.py
     │   ├── agent.py          # Clase principal PRAgent
     │   ├── ciclo.py          # Lógica de 3 preguntas
     │   ├── versiones.py      # Sistema de versionado v1.x
     │   ├── memoria.py        # Wrapper inteligente para RAG
     │   └── prompts.py        # Templates de prompts PR
     │
     └── Integración via endpoints
```

---

## 3. COMPONENTES

### 3.1 PRAgent (Clase Principal)

```python
# pr_agent/agent.py

from typing import Optional, List, Dict
from datetime import datetime
from .ciclo import CicloPR
from .versiones import SistemaVersiones
from .memoria import MemoriaPR

class PRAgent:
    """
    Agente PR: Implementa Debug-First Design

    Axiomas:
    - 0: Asume fracaso
    - 1: No hay meta final
    - 2: Todo colapsa
    - 3: Error = dato
    """

    def __init__(self, rag_collection, db_connection, llm_client):
        self.ciclo = CicloPR()
        self.versiones = SistemaVersiones(db_connection)
        self.memoria = MemoriaPR(rag_collection)
        self.llm = llm_client
        self.db = db_connection

    async def recibir_problema(
        self,
        descripcion: str,
        area: str,
        usuario: str
    ) -> Dict:
        """
        Punto de entrada: Usuario reporta un problema
        Implementa ANTES: ¿Dónde estoy?
        """
        # Paso 1: Crear checkpoint
        checkpoint = self.ciclo.crear_checkpoint(
            descripcion=descripcion,
            area=area,
            usuario=usuario
        )

        # Paso 2: Buscar en memoria (RAG)
        casos_similares = await self.memoria.buscar_similares(
            query=descripcion,
            area=area,
            n_resultados=5
        )

        # Paso 3: Decidir flujo
        if casos_similares and self._hay_caso_relevante(casos_similares):
            return await self._flujo_caso_conocido(
                checkpoint, casos_similares, descripcion
            )
        else:
            return await self._flujo_caso_nuevo(
                checkpoint, descripcion, area, usuario
            )

    async def _flujo_caso_conocido(
        self,
        checkpoint: Dict,
        casos: List[Dict],
        descripcion: str
    ) -> Dict:
        """Flujo cuando hay casos similares en memoria"""

        # Formatear casos para mostrar
        casos_formateados = self._formatear_casos_para_usuario(casos)

        # Generar análisis con LLM
        analisis = await self._analizar_similitud(descripcion, casos)

        return {
            "fase": "ANTES",
            "pregunta": "¿Dónde estoy?",
            "estado": "casos_encontrados",
            "checkpoint_id": checkpoint["id"],
            "casos_similares": casos_formateados,
            "analisis": analisis,
            "siguiente_accion": "confirmar_si_aplica",
            "mensaje": f"Encontré {len(casos)} casos similares. ¿Alguno aplica?"
        }

    async def _flujo_caso_nuevo(
        self,
        checkpoint: Dict,
        descripcion: str,
        area: str,
        usuario: str
    ) -> Dict:
        """Flujo cuando es un caso nuevo"""

        # Crear incidencia
        incidencia_id = await self._crear_incidencia(
            descripcion, area, usuario, checkpoint["id"]
        )

        # Generar preguntas guía
        preguntas = await self._generar_preguntas_documentacion(descripcion)

        return {
            "fase": "DURANTE",
            "pregunta": "¿Cómo falla?",
            "estado": "documentando_nuevo",
            "checkpoint_id": checkpoint["id"],
            "incidencia_id": incidencia_id,
            "preguntas_guia": preguntas,
            "mensaje": "Es un caso nuevo. Vamos a documentarlo para que sirva en el futuro."
        }

    async def resolver_incidencia(
        self,
        incidencia_id: str,
        solucion: str,
        causa_raiz: str,
        acciones_preventivas: str,
        usuario: str
    ) -> Dict:
        """
        Implementa DESPUÉS: ¿Qué aprendí?
        Cierra el ciclo PR y hereda el conocimiento
        """
        # Obtener datos de incidencia
        incidencia = await self._get_incidencia(incidencia_id)
        reportes = await self._get_reportes(incidencia_id)

        # Crear versión
        version = self.versiones.crear_version(
            area=incidencia["area"],
            tipo="caso_resuelto"
        )

        # Construir documento de conocimiento
        documento = self._construir_documento_conocimiento(
            incidencia=incidencia,
            reportes=reportes,
            solucion=solucion,
            causa_raiz=causa_raiz,
            acciones_preventivas=acciones_preventivas,
            version=version
        )

        # Guardar en RAG (heredar)
        await self.memoria.guardar(
            documento=documento,
            metadata={
                "tipo": "caso_resuelto_pr",
                "version": version,
                "area": incidencia["area"],
                "titulo": incidencia["titulo"],
                "fecha": datetime.now().isoformat(),
                "incidencia_id": incidencia_id
            }
        )

        # Actualizar incidencia en BD
        await self._actualizar_incidencia_resuelta(
            incidencia_id, solucion, version
        )

        # Ciclo completado
        return {
            "fase": "DESPUÉS",
            "pregunta": "¿Qué aprendí?",
            "estado": "conocimiento_heredado",
            "version": version,
            "total_en_memoria": self.memoria.count(),
            "mensaje": f"Caso documentado como {version}. El sistema aprendió de este caso."
        }

    def _construir_documento_conocimiento(
        self,
        incidencia: Dict,
        reportes: List[Dict],
        solucion: str,
        causa_raiz: str,
        acciones_preventivas: str,
        version: str
    ) -> str:
        """Construye el documento estructurado para RAG"""

        reportes_texto = "\n".join([
            f"- {r['autor']} ({r['fecha']}): {r['contenido']}"
            for r in reportes
        ])

        return f"""
══════════════════════════════════════════════════════════
CASO RESUELTO: {version}
══════════════════════════════════════════════════════════

IDENTIFICACIÓN
─────────────────────────────────────────────────────────
Título: {incidencia['titulo']}
Área: {incidencia['area']}
Prioridad: {incidencia['prioridad']}
Fecha reporte: {incidencia['fecha_creacion']}
Fecha resolución: {datetime.now().isoformat()}

DESCRIPCIÓN DEL PROBLEMA
─────────────────────────────────────────────────────────
{incidencia['descripcion']}

REPORTES DE INVOLUCRADOS
─────────────────────────────────────────────────────────
{reportes_texto if reportes_texto else 'Sin reportes adicionales'}

ANÁLISIS DE CAUSA RAÍZ
─────────────────────────────────────────────────────────
{causa_raiz}

SOLUCIÓN APLICADA
─────────────────────────────────────────────────────────
{solucion}

ACCIONES PREVENTIVAS
─────────────────────────────────────────────────────────
{acciones_preventivas}

APRENDIZAJE PR
─────────────────────────────────────────────────────────
- Axioma aplicado: Error = dato
- Este caso incrementó el conocimiento del sistema
- Versión: {version}
- Keywords: {self._extraer_keywords(incidencia['descripcion'])}

══════════════════════════════════════════════════════════
"""

    def _hay_caso_relevante(self, casos: List[Dict]) -> bool:
        """Determina si hay al menos un caso con relevancia > 0.7"""
        return any(c.get("relevancia", 0) > 0.7 for c in casos)

    def _formatear_casos_para_usuario(self, casos: List[Dict]) -> List[Dict]:
        """Formatea casos para presentación amigable"""
        return [
            {
                "version": c["metadata"].get("version", "N/A"),
                "titulo": c["metadata"].get("titulo", "Sin título"),
                "area": c["metadata"].get("area", "N/A"),
                "fecha": c["metadata"].get("fecha", "N/A"),
                "relevancia": f"{c.get('relevancia', 0)*100:.0f}%",
                "resumen": c["contenido"][:500] + "..."
            }
            for c in casos[:5]
        ]

    async def _analizar_similitud(
        self,
        descripcion_nueva: str,
        casos: List[Dict]
    ) -> str:
        """Usa LLM para analizar similitud y dar recomendación"""

        prompt = f"""Analiza el siguiente problema nuevo contra los casos históricos.

PROBLEMA NUEVO:
{descripcion_nueva}

CASOS HISTÓRICOS:
{self._formatear_casos_para_prompt(casos)}

Responde:
1. ¿Cuál caso es más similar y por qué?
2. ¿La solución anterior podría aplicar?
3. ¿Qué información adicional se necesita?

Sé conciso y directo."""

        return await self.llm.generate(prompt)

    async def _generar_preguntas_documentacion(self, descripcion: str) -> List[str]:
        """Genera preguntas guía para documentar un caso nuevo"""

        prompt = f"""Basándote en este problema reportado, genera 5 preguntas
clave que ayuden a documentar el caso completamente.

PROBLEMA:
{descripcion}

Las preguntas deben cubrir:
- Cuándo comenzó
- Qué se ha intentado
- Quién está involucrado
- Qué impacto tiene
- Qué condiciones lo reproducen

Formato: Lista numerada, preguntas directas."""

        respuesta = await self.llm.generate(prompt)
        return self._parsear_lista(respuesta)
```

### 3.2 Ciclo PR

```python
# pr_agent/ciclo.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import uuid

@dataclass
class Checkpoint:
    id: str
    timestamp: str
    descripcion: str
    area: str
    usuario: str
    estado: str  # 'activo', 'resuelto', 'rollback'
    parent_id: Optional[str] = None

class CicloPR:
    """
    Implementa el ciclo PR de 3 preguntas:

    ANTES: ¿Dónde estoy?
      1. Checkpoint - Guardar estado actual
      2. Rollback - Poder volver atrás
      3. Declarar - Definir qué voy a intentar

    DURANTE: ¿Cómo falla?
      4. Degradar - Si falla, degradar gracefully
      5. Continuar - Mantener sistema vivo
      6. Iterar - Nuevo intento con ajuste

    DESPUÉS: ¿Qué aprendí?
      7. Trazar - Documentar qué pasó
      8. Depurar - Eliminar lo inválido
      9. Siguiente - Crear nueva versión
    """

    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}

    # === ANTES: ¿Dónde estoy? ===

    def crear_checkpoint(
        self,
        descripcion: str,
        area: str,
        usuario: str,
        parent_id: Optional[str] = None
    ) -> Dict:
        """Paso 1: Crear checkpoint del estado actual"""

        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            descripcion=descripcion,
            area=area,
            usuario=usuario,
            estado='activo',
            parent_id=parent_id
        )

        self.checkpoints[checkpoint.id] = checkpoint

        return {
            "id": checkpoint.id,
            "timestamp": checkpoint.timestamp,
            "puede_rollback": parent_id is not None,
            "mensaje": "Checkpoint creado. Podemos volver a este punto."
        }

    def rollback(self, checkpoint_id: str) -> Dict:
        """Paso 2: Volver a un checkpoint anterior"""

        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint.estado = 'rollback'

        return {
            "id": checkpoint_id,
            "estado": "rollback_ejecutado",
            "timestamp_original": checkpoint.timestamp,
            "mensaje": f"Rollback a checkpoint {checkpoint_id[:8]}..."
        }

    def declarar_intento(
        self,
        checkpoint_id: str,
        intento: str
    ) -> Dict:
        """Paso 3: Declarar qué vamos a intentar"""

        return {
            "checkpoint_id": checkpoint_id,
            "intento_declarado": intento,
            "timestamp": datetime.now().isoformat(),
            "axioma": "Axioma 0: Asumimos que puede fallar",
            "mensaje": f"Intento registrado: {intento}"
        }

    # === DURANTE: ¿Cómo falla? ===

    def registrar_fallo(
        self,
        checkpoint_id: str,
        tipo_fallo: str,
        detalle: str
    ) -> Dict:
        """Paso 4-6: Registrar cómo falló y decidir siguiente paso"""

        return {
            "checkpoint_id": checkpoint_id,
            "tipo_fallo": tipo_fallo,
            "detalle": detalle,
            "axioma": "Axioma 3: Error = dato",
            "opciones": [
                {"accion": "degradar", "desc": "Reducir alcance y continuar"},
                {"accion": "iterar", "desc": "Nuevo intento con ajuste"},
                {"accion": "rollback", "desc": "Volver al checkpoint"}
            ]
        }

    # === DESPUÉS: ¿Qué aprendí? ===

    def cerrar_ciclo(
        self,
        checkpoint_id: str,
        resultado: str,
        aprendizaje: str,
        depurar: list,
        heredar: list
    ) -> Dict:
        """Pasos 7-9: Cerrar ciclo y preparar siguiente versión"""

        if checkpoint_id in self.checkpoints:
            self.checkpoints[checkpoint_id].estado = 'resuelto'

        return {
            "checkpoint_id": checkpoint_id,
            "fase": "DESPUÉS",
            "resultado": resultado,
            "aprendizaje": aprendizaje,
            "depurado": depurar,  # Lo que no sirvió
            "heredado": heredar,  # Lo que sí sirvió
            "axioma": "Axioma 1: No hay meta, solo siguiente iteración",
            "mensaje": "Ciclo cerrado. Conocimiento listo para heredar."
        }
```

### 3.3 Sistema de Versiones

```python
# pr_agent/versiones.py

from datetime import datetime
from typing import Optional, Dict, List
import sqlite3
import re

class SistemaVersiones:
    """
    Sistema de versionado PR

    Formato: {AREA}_v{MAJOR}.{MINOR}
    Ejemplo: SOLDADURA_v1.0, SOLDADURA_v1.1, LINEA3_v2.0

    - MAJOR: Nuevo tipo de problema
    - MINOR: Nueva solución/variante del mismo problema
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_tabla()

    def _init_tabla(self):
        """Crea tabla de versiones si no existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pr_versiones (
                id TEXT PRIMARY KEY,
                area TEXT NOT NULL,
                major INTEGER NOT NULL,
                minor INTEGER NOT NULL,
                version_str TEXT NOT NULL,
                tipo TEXT NOT NULL,
                fecha TEXT NOT NULL,
                incidencia_id TEXT,
                descripcion TEXT,
                UNIQUE(area, major, minor)
            )
        """)
        conn.commit()
        conn.close()

    def crear_version(
        self,
        area: str,
        tipo: str,
        incidencia_id: Optional[str] = None,
        descripcion: Optional[str] = None
    ) -> str:
        """
        Crea una nueva versión para un área

        Returns: String de versión (ej: "SOLDADURA_v1.2")
        """
        area_normalizada = self._normalizar_area(area)

        # Obtener última versión del área
        ultima = self._get_ultima_version(area_normalizada)

        if ultima is None:
            # Primera versión del área
            major, minor = 1, 0
        else:
            # Incrementar minor
            major = ultima["major"]
            minor = ultima["minor"] + 1

        version_str = f"{area_normalizada}_v{major}.{minor}"

        # Guardar en BD
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pr_versiones
            (id, area, major, minor, version_str, tipo, fecha, incidencia_id, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{area_normalizada}_{major}_{minor}",
            area_normalizada,
            major,
            minor,
            version_str,
            tipo,
            datetime.now().isoformat(),
            incidencia_id,
            descripcion
        ))
        conn.commit()
        conn.close()

        return version_str

    def _get_ultima_version(self, area: str) -> Optional[Dict]:
        """Obtiene la última versión de un área"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT major, minor, version_str, fecha
            FROM pr_versiones
            WHERE area = ?
            ORDER BY major DESC, minor DESC
            LIMIT 1
        """, (area,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "major": row[0],
                "minor": row[1],
                "version_str": row[2],
                "fecha": row[3]
            }
        return None

    def listar_versiones(self, area: Optional[str] = None) -> List[Dict]:
        """Lista todas las versiones, opcionalmente filtradas por área"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if area:
            cursor.execute("""
                SELECT * FROM pr_versiones
                WHERE area = ?
                ORDER BY major DESC, minor DESC
            """, (self._normalizar_area(area),))
        else:
            cursor.execute("""
                SELECT * FROM pr_versiones
                ORDER BY fecha DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def obtener_historial_area(self, area: str) -> Dict:
        """Obtiene el historial completo de un área"""
        versiones = self.listar_versiones(area)

        return {
            "area": self._normalizar_area(area),
            "total_versiones": len(versiones),
            "version_actual": versiones[0]["version_str"] if versiones else None,
            "primera_version": versiones[-1]["version_str"] if versiones else None,
            "historial": versiones
        }

    def _normalizar_area(self, area: str) -> str:
        """Normaliza nombre de área: mayúsculas, sin espacios"""
        return re.sub(r'[^A-Z0-9]', '_', area.upper().strip())
```

### 3.4 Memoria PR (Wrapper RAG)

```python
# pr_agent/memoria.py

from typing import List, Dict, Optional
from datetime import datetime

class MemoriaPR:
    """
    Wrapper inteligente para ChromaDB
    Implementa la "memoria en RAM" del concepto PR

    A diferencia de ISO (memoria en papel):
    - Siempre accesible
    - Busca patrones automáticamente
    - Conecta casos por similitud
    - Hereda y depura
    """

    def __init__(self, collection):
        self.collection = collection

    async def buscar_similares(
        self,
        query: str,
        area: Optional[str] = None,
        n_resultados: int = 5,
        umbral_relevancia: float = 0.5
    ) -> List[Dict]:
        """
        Busca casos similares en la memoria

        Implementa: "¿Qué aprendimos la última vez que pasó esto?"
        """
        if self.collection.count() == 0:
            return []

        # Construir query enriquecida
        query_enriquecida = query
        if area:
            query_enriquecida = f"[{area}] {query}"

        try:
            resultados = self.collection.query(
                query_texts=[query_enriquecida],
                n_results=n_resultados,
                include=["documents", "metadatas", "distances"]
            )

            casos = []
            for i, (doc, meta, dist) in enumerate(zip(
                resultados['documents'][0],
                resultados['metadatas'][0],
                resultados['distances'][0]
            )):
                # Convertir distancia a relevancia (0-1)
                relevancia = 1 - (dist / 2)  # Normalizar

                if relevancia >= umbral_relevancia:
                    casos.append({
                        "contenido": doc,
                        "metadata": meta,
                        "relevancia": relevancia,
                        "posicion": i + 1
                    })

            return casos

        except Exception as e:
            print(f"Error buscando en memoria: {e}")
            return []

    async def guardar(
        self,
        documento: str,
        metadata: Dict,
        id_override: Optional[str] = None
    ) -> Dict:
        """
        Guarda un documento en la memoria (hereda conocimiento)

        Implementa: Axioma de herencia
        """
        doc_id = id_override or f"pr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            self.collection.add(
                documents=[documento],
                metadatas=[metadata],
                ids=[doc_id]
            )

            return {
                "id": doc_id,
                "guardado": True,
                "total_en_memoria": self.collection.count(),
                "mensaje": "Conocimiento heredado a la memoria"
            }

        except Exception as e:
            return {
                "id": doc_id,
                "guardado": False,
                "error": str(e)
            }

    async def depurar(self, ids_a_eliminar: List[str]) -> Dict:
        """
        Elimina documentos obsoletos o inválidos

        Implementa: Depurar lo inválido del ciclo PR
        """
        try:
            self.collection.delete(ids=ids_a_eliminar)

            return {
                "depurados": len(ids_a_eliminar),
                "total_en_memoria": self.collection.count(),
                "mensaje": f"Depurados {len(ids_a_eliminar)} documentos inválidos"
            }
        except Exception as e:
            return {"error": str(e)}

    def count(self) -> int:
        """Retorna total de documentos en memoria"""
        return self.collection.count() if self.collection else 0

    def estadisticas(self) -> Dict:
        """Estadísticas de la memoria"""
        return {
            "total_documentos": self.count(),
            "estado": "activo" if self.collection else "inactivo",
            "descripcion": "Memoria PR - Conocimiento vivo accesible"
        }
```

---

## 4. INTEGRACIÓN CON MAIN.PY

```python
# Agregar a main.py

from pr_agent import PRAgent

# Inicializar agente PR
pr_agent = PRAgent(
    rag_collection=collection,
    db_connection=DATA_DIR + "/pr_system.db",
    llm_client=consultar_llm
)

# Nuevo endpoint: Recibir problema con flujo PR
@app.post("/api/pr/problema")
async def recibir_problema_pr(
    descripcion: str = Form(...),
    area: str = Form(...),
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Endpoint principal PR: Recibe problema e inicia ciclo
    Implementa las 3 preguntas automáticamente
    """
    resultado = await pr_agent.recibir_problema(
        descripcion=descripcion,
        area=area,
        usuario=usuario["nombre_completo"]
    )
    return resultado

# Nuevo endpoint: Resolver con aprendizaje PR
@app.post("/api/pr/resolver/{incidencia_id}")
async def resolver_pr(
    incidencia_id: str,
    solucion: str = Form(...),
    causa_raiz: str = Form(...),
    acciones_preventivas: str = Form(...),
    usuario: dict = Depends(requiere_rol("supervisor", "admin"))
):
    """
    Cierra ciclo PR: Resuelve y hereda conocimiento
    """
    resultado = await pr_agent.resolver_incidencia(
        incidencia_id=incidencia_id,
        solucion=solucion,
        causa_raiz=causa_raiz,
        acciones_preventivas=acciones_preventivas,
        usuario=usuario["nombre_completo"]
    )
    return resultado

# Nuevo endpoint: Historial de versiones
@app.get("/api/pr/versiones")
async def listar_versiones_pr(
    area: Optional[str] = None,
    usuario: dict = Depends(obtener_usuario_actual)
):
    """Lista versiones de conocimiento por área"""
    return pr_agent.versiones.listar_versiones(area)
```

---

## 5. ARCHIVOS A CREAR

```
PR/
├── main.py                    # Modificar: agregar imports y endpoints
├── pr_agent/
│   ├── __init__.py           # Exports del módulo
│   ├── agent.py              # Clase PRAgent
│   ├── ciclo.py              # Lógica 3 preguntas
│   ├── versiones.py          # Sistema versionado
│   ├── memoria.py            # Wrapper RAG
│   └── prompts.py            # Templates (opcional)
└── requirements.txt          # Sin cambios (ya tiene todo)
```

---

## 6. PRUEBAS

```python
# tests/test_pr_agent.py

import pytest
from pr_agent import PRAgent, CicloPR, SistemaVersiones

def test_ciclo_crear_checkpoint():
    ciclo = CicloPR()
    checkpoint = ciclo.crear_checkpoint(
        descripcion="Problema de soldadura",
        area="PRODUCCION",
        usuario="Juan"
    )
    assert "id" in checkpoint
    assert checkpoint["puede_rollback"] == False

def test_versiones_crear():
    versiones = SistemaVersiones(":memory:")
    v1 = versiones.crear_version("Soldadura", "caso_resuelto")
    assert v1 == "SOLDADURA_v1.0"

    v2 = versiones.crear_version("Soldadura", "caso_resuelto")
    assert v2 == "SOLDADURA_v1.1"

def test_versiones_otra_area():
    versiones = SistemaVersiones(":memory:")
    v1 = versiones.crear_version("Pintura", "caso_resuelto")
    assert v1 == "PINTURA_v1.0"
```

---

## 7. CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear directorio `pr_agent/`
- [ ] Implementar `agent.py`
- [ ] Implementar `ciclo.py`
- [ ] Implementar `versiones.py`
- [ ] Implementar `memoria.py`
- [ ] Modificar `main.py` con nuevos endpoints
- [ ] Crear tests
- [ ] Probar flujo completo

---

*Este documento es checkpoint v1.0 de PR_CODIGO*
*v1.1 viene después del siguiente error*
