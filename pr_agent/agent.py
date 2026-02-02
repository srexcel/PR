"""
PRAgent: Agente Principal de Conocimiento Vivo
==============================================

Orquesta el ciclo PR completo:
1. Recibe problema → Busca casos similares
2. Si hay similares → Sugiere soluciones
3. Si es nuevo → Guía documentación
4. Al resolver → Hereda conocimiento

"Los LLM ya hacen PR. Nadie se había dado cuenta.
PR simplemente le da propósito."
"""

from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import sqlite3
import uuid
import re

from .ciclo import CicloPR, EstadoCheckpoint
from .versiones import SistemaVersiones
from .memoria import MemoriaPR
from .prompts import (
    SYSTEM_PROMPT_PR,
    PROMPT_ANALISIS_SIMILITUD,
    PROMPT_PREGUNTAS_DOCUMENTACION,
    PROMPT_DOCUMENTO_8D,
    PROMPT_CONSULTA_CON_CONTEXTO,
    PROMPT_CONSULTA_SIN_CONTEXTO,
    formatear_casos_para_prompt,
    construir_prompt,
    obtener_mensaje
)


class PRAgent:
    """
    Agente PR: Implementa Debug-First Design.

    Axiomas:
    - 0: Asume fracaso
    - 1: No hay meta final
    - 2: Todo colapsa
    - 3: Error = dato

    Uso:
        agent = PRAgent(
            rag_collection=collection,
            db_path="/path/to/db",
            llm_func=consultar_llm
        )

        # Recibir un problema
        resultado = await agent.recibir_problema(
            descripcion="La soldadura tiene porosidad",
            area="Producción",
            usuario="Juan Pérez"
        )

        # Resolver y aprender
        resultado = await agent.resolver_incidencia(
            incidencia_id="xxx",
            solucion="Se ajustó el flujo de gas",
            causa_raiz="Gas de protección insuficiente",
            acciones_preventivas="Verificar flujo cada turno"
        )
    """

    def __init__(
        self,
        rag_collection: Any,
        db_path: str,
        llm_func: Callable
    ):
        """
        Inicializa el agente PR.

        Args:
            rag_collection: Colección de ChromaDB
            db_path: Ruta a la base de datos SQLite
            llm_func: Función async para consultar LLM
        """
        self.ciclo = CicloPR()
        self.versiones = SistemaVersiones(db_path)
        self.memoria = MemoriaPR(rag_collection)
        self.llm = llm_func
        self.db_path = db_path

    # =========================================================
    # FLUJO PRINCIPAL: Recibir Problema
    # =========================================================

    async def recibir_problema(
        self,
        descripcion: str,
        area: str,
        usuario: str,
        prioridad: str = "media",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Punto de entrada: Usuario reporta un problema.

        Implementa ANTES: ¿Dónde estoy?
        - Crea checkpoint
        - Busca casos similares
        - Decide flujo (conocido vs nuevo)

        Returns:
            Dict con información de casos similares o guía para nuevo caso
        """
        # Paso 1: Crear checkpoint
        checkpoint = self.ciclo.crear_checkpoint(
            descripcion=descripcion,
            area=area,
            usuario=usuario,
            metadata=metadata
        )

        # Paso 2: Buscar en memoria (RAG)
        casos_similares = await self.memoria.buscar_similares(
            query=descripcion,
            area=area,
            n_resultados=5,
            umbral_relevancia=0.4
        )

        # Paso 3: Decidir flujo
        if casos_similares and self._hay_caso_relevante(casos_similares):
            return await self._flujo_caso_conocido(
                checkpoint=checkpoint,
                casos=casos_similares,
                descripcion=descripcion,
                area=area,
                usuario=usuario,
                prioridad=prioridad
            )
        else:
            return await self._flujo_caso_nuevo(
                checkpoint=checkpoint,
                descripcion=descripcion,
                area=area,
                usuario=usuario,
                prioridad=prioridad
            )

    async def _flujo_caso_conocido(
        self,
        checkpoint: Dict,
        casos: List[Dict],
        descripcion: str,
        area: str,
        usuario: str,
        prioridad: str
    ) -> Dict:
        """Flujo cuando hay casos similares en memoria"""

        # Formatear casos para mostrar
        casos_formateados = self._formatear_casos_para_usuario(casos)

        # Generar análisis con LLM
        analisis = await self._analizar_similitud(descripcion, casos)

        # Crear incidencia de todas formas (para tracking)
        incidencia_id = await self._crear_incidencia(
            titulo=self._generar_titulo(descripcion),
            descripcion=descripcion,
            area=area,
            usuario=usuario,
            prioridad=prioridad,
            checkpoint_id=checkpoint["id"]
        )

        return {
            "fase": "ANTES",
            "pregunta": "¿Dónde estoy?",
            "estado": "casos_encontrados",
            "checkpoint_id": checkpoint["id"],
            "incidencia_id": incidencia_id,
            "casos_similares": casos_formateados,
            "total_casos": len(casos),
            "analisis": analisis,
            "siguiente_accion": "confirmar_si_aplica",
            "mensaje": obtener_mensaje("casos_encontrados", n=len(casos)),
            "opciones": [
                {"accion": "aplicar_solucion", "desc": "La solución anterior aplica"},
                {"accion": "caso_diferente", "desc": "Mi caso es diferente"},
                {"accion": "ver_mas", "desc": "Ver más detalles"}
            ]
        }

    async def _flujo_caso_nuevo(
        self,
        checkpoint: Dict,
        descripcion: str,
        area: str,
        usuario: str,
        prioridad: str
    ) -> Dict:
        """Flujo cuando es un caso nuevo"""

        # Crear incidencia
        incidencia_id = await self._crear_incidencia(
            titulo=self._generar_titulo(descripcion),
            descripcion=descripcion,
            area=area,
            usuario=usuario,
            prioridad=prioridad,
            checkpoint_id=checkpoint["id"]
        )

        # Generar preguntas guía
        preguntas = await self._generar_preguntas_documentacion(descripcion, area)

        return {
            "fase": "DURANTE",
            "pregunta": "¿Cómo falla?",
            "estado": "documentando_nuevo",
            "checkpoint_id": checkpoint["id"],
            "incidencia_id": incidencia_id,
            "es_caso_nuevo": True,
            "preguntas_guia": preguntas,
            "mensaje": obtener_mensaje("sin_casos"),
            "instrucciones": obtener_mensaje("documentar_nuevo")
        }

    # =========================================================
    # FLUJO: Resolver Incidencia
    # =========================================================

    async def resolver_incidencia(
        self,
        incidencia_id: str,
        solucion: str,
        causa_raiz: str,
        acciones_preventivas: str,
        usuario: str,
        agregar_a_rag: bool = True
    ) -> Dict:
        """
        Implementa DESPUÉS: ¿Qué aprendí?

        Cierra el ciclo PR y hereda el conocimiento:
        1. Obtiene información de incidencia
        2. Crea nueva versión
        3. Guarda en RAG
        4. Actualiza estado

        Args:
            incidencia_id: ID de la incidencia a resolver
            solucion: Descripción de la solución aplicada
            causa_raiz: Causa raíz identificada
            acciones_preventivas: Acciones para prevenir recurrencia
            usuario: Usuario que resuelve
            agregar_a_rag: Si True, guarda en base de conocimiento

        Returns:
            Dict con información de la resolución y versión creada
        """
        # Obtener datos de incidencia
        incidencia = await self._get_incidencia(incidencia_id)
        if not incidencia:
            return {"error": "Incidencia no encontrada"}

        reportes = await self._get_reportes(incidencia_id)

        # Crear versión
        version = self.versiones.crear_version(
            area=incidencia["area"] or "GENERAL",
            tipo="caso_resuelto",
            incidencia_id=incidencia_id,
            descripcion=incidencia["titulo"],
            aprendizaje=causa_raiz,
            keywords=self._extraer_keywords(
                f"{incidencia['descripcion']} {solucion} {causa_raiz}"
            )
        )

        # Construir documento de conocimiento
        documento = self._construir_documento_conocimiento(
            incidencia=incidencia,
            reportes=reportes,
            solucion=solucion,
            causa_raiz=causa_raiz,
            acciones_preventivas=acciones_preventivas,
            version=version,
            resuelto_por=usuario
        )

        # Guardar en RAG
        rag_resultado = {"guardado": False}
        if agregar_a_rag:
            rag_resultado = await self.memoria.guardar(
                documento=documento,
                metadata={
                    "tipo": "caso_resuelto_pr",
                    "version": version,
                    "area": incidencia["area"] or "GENERAL",
                    "titulo": incidencia["titulo"],
                    "fecha": datetime.now().isoformat(),
                    "incidencia_id": incidencia_id,
                    "resuelto_por": usuario
                },
                id_override=f"pr_{incidencia_id}"
            )

        # Actualizar incidencia en BD
        await self._actualizar_incidencia_resuelta(
            incidencia_id=incidencia_id,
            solucion=solucion,
            version=version,
            agregar_a_rag=agregar_a_rag
        )

        # Cerrar ciclo PR si hay checkpoint
        if incidencia.get("checkpoint_id"):
            self.ciclo.cerrar_ciclo(
                checkpoint_id=incidencia["checkpoint_id"],
                resultado_final="resuelto",
                aprendizaje=causa_raiz,
                heredar=[version]
            )

        return {
            "fase": "DESPUÉS",
            "pregunta": "¿Qué aprendí?",
            "estado": "conocimiento_heredado",
            "incidencia_id": incidencia_id,
            "version": version,
            "guardado_en_rag": rag_resultado.get("guardado", False),
            "total_en_memoria": self.memoria.count(),
            "mensaje": obtener_mensaje("ciclo_cerrado", version=version),
            "resumen": {
                "problema": incidencia["titulo"],
                "causa_raiz": causa_raiz,
                "solucion": solucion,
                "acciones_preventivas": acciones_preventivas
            }
        }

    # =========================================================
    # CONSULTAS RAG
    # =========================================================

    async def consultar(
        self,
        pregunta: str,
        area: Optional[str] = None,
        n_resultados: int = 5
    ) -> Dict:
        """
        Consulta la base de conocimiento con RAG + LLM.

        Busca casos similares y genera respuesta contextualizada.
        """
        # Buscar casos similares
        casos = await self.memoria.buscar_similares(
            query=pregunta,
            area=area,
            n_resultados=n_resultados
        )

        # Generar respuesta con LLM
        if casos:
            contexto = await self.memoria.obtener_contexto_para_llm(
                pregunta, n_casos=min(3, len(casos))
            )
            prompt = construir_prompt(
                PROMPT_CONSULTA_CON_CONTEXTO,
                contexto=contexto,
                consulta=pregunta
            )
        else:
            prompt = construir_prompt(
                PROMPT_CONSULTA_SIN_CONTEXTO,
                consulta=pregunta
            )

        respuesta = await self.llm(prompt, SYSTEM_PROMPT_PR)

        return {
            "respuesta": respuesta,
            "casos_similares": casos,
            "total_en_rag": self.memoria.count(),
            "tiene_contexto": len(casos) > 0
        }

    async def generar_documento_8d(self, incidencia_id: str) -> Dict:
        """
        Genera un documento 8D para una incidencia resuelta.

        Usa el LLM para generar un documento profesional
        basado en la información de la incidencia.
        """
        incidencia = await self._get_incidencia(incidencia_id)
        if not incidencia:
            return {"error": "Incidencia no encontrada"}

        if incidencia["estado"] != "resuelto":
            return {"error": "La incidencia debe estar resuelta para generar 8D"}

        reportes = await self._get_reportes(incidencia_id)
        reportes_texto = self._formatear_reportes(reportes)

        prompt = construir_prompt(
            PROMPT_DOCUMENTO_8D,
            titulo=incidencia["titulo"],
            area=incidencia["area"] or "No especificada",
            prioridad=incidencia["prioridad"],
            fecha_creacion=incidencia["fecha_creacion"],
            descripcion=incidencia["descripcion"],
            reportes=reportes_texto,
            solucion=incidencia["solucion"] or "No documentada",
            causa_raiz="Por determinar en análisis",
            acciones_preventivas="Por determinar",
            fecha_generacion=datetime.now().strftime("%Y-%m-%d %H:%M")
        )

        documento = await self.llm(prompt, SYSTEM_PROMPT_PR)

        return {
            "documento": documento,
            "incidencia_id": incidencia_id,
            "generado": datetime.now().isoformat()
        }

    # =========================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # =========================================================

    def _hay_caso_relevante(self, casos: List[Dict], umbral: float = 0.6) -> bool:
        """Determina si hay al menos un caso con relevancia suficiente"""
        return any(c.get("relevancia", 0) >= umbral for c in casos)

    def _formatear_casos_para_usuario(self, casos: List[Dict]) -> List[Dict]:
        """Formatea casos para presentación amigable"""
        return [
            {
                "version": c.get("metadata", {}).get("version", "N/A"),
                "titulo": c.get("metadata", {}).get("titulo", "Sin título"),
                "area": c.get("metadata", {}).get("area", "N/A"),
                "fecha": c.get("metadata", {}).get("fecha", "N/A"),
                "relevancia": c.get("relevancia_pct", "N/A"),
                "resumen": c.get("contenido", "")[:500] + "..." if len(c.get("contenido", "")) > 500 else c.get("contenido", "")
            }
            for c in casos[:5]
        ]

    async def _analizar_similitud(
        self,
        descripcion_nueva: str,
        casos: List[Dict]
    ) -> str:
        """Usa LLM para analizar similitud y dar recomendación"""
        casos_texto = formatear_casos_para_prompt(casos[:3])

        prompt = construir_prompt(
            PROMPT_ANALISIS_SIMILITUD,
            problema_nuevo=descripcion_nueva,
            casos_historicos=casos_texto
        )

        return await self.llm(prompt, SYSTEM_PROMPT_PR)

    async def _generar_preguntas_documentacion(
        self,
        descripcion: str,
        area: str
    ) -> List[str]:
        """Genera preguntas guía para documentar un caso nuevo"""
        prompt = construir_prompt(
            PROMPT_PREGUNTAS_DOCUMENTACION,
            descripcion=descripcion,
            area=area
        )

        respuesta = await self.llm(prompt, SYSTEM_PROMPT_PR)
        return self._parsear_lista_numerada(respuesta)

    def _construir_documento_conocimiento(
        self,
        incidencia: Dict,
        reportes: List[Dict],
        solucion: str,
        causa_raiz: str,
        acciones_preventivas: str,
        version: str,
        resuelto_por: str
    ) -> str:
        """Construye el documento estructurado para RAG"""
        reportes_texto = self._formatear_reportes(reportes)

        return f"""
══════════════════════════════════════════════════════════
CASO RESUELTO: {version}
══════════════════════════════════════════════════════════

IDENTIFICACIÓN
─────────────────────────────────────────────────────────
Título: {incidencia['titulo']}
Área: {incidencia.get('area', 'No especificada')}
Prioridad: {incidencia.get('prioridad', 'media')}
Fecha reporte: {incidencia['fecha_creacion']}
Fecha resolución: {datetime.now().isoformat()}
Resuelto por: {resuelto_por}

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
- Keywords: {', '.join(self._extraer_keywords(incidencia['descripcion']))}

══════════════════════════════════════════════════════════
"""

    def _generar_titulo(self, descripcion: str) -> str:
        """Genera un título corto a partir de la descripción"""
        # Tomar primeras palabras significativas
        palabras = descripcion.split()[:8]
        titulo = ' '.join(palabras)
        if len(descripcion) > len(titulo):
            titulo += "..."
        return titulo

    def _extraer_keywords(self, texto: str) -> List[str]:
        """Extrae palabras clave del texto"""
        # Palabras a ignorar
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'a', 'en', 'con', 'por', 'para',
            'es', 'son', 'fue', 'han', 'ha', 'ser', 'estar',
            'que', 'se', 'no', 'si', 'como', 'pero', 'más',
            'este', 'esta', 'estos', 'estas', 'ese', 'esa',
            'y', 'o', 'e', 'u', 'ni'
        }

        # Extraer palabras alfanuméricas de más de 3 caracteres
        palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', texto.lower())

        # Filtrar stopwords y duplicados
        keywords = []
        vistos = set()
        for p in palabras:
            if p not in stopwords and p not in vistos:
                keywords.append(p)
                vistos.add(p)

        return keywords[:10]

    def _parsear_lista_numerada(self, texto: str) -> List[str]:
        """Parsea una lista numerada del texto"""
        lineas = texto.strip().split('\n')
        items = []

        for linea in lineas:
            # Buscar patrones como "1.", "1)", "1-", etc.
            match = re.match(r'^\s*\d+[\.\)\-]\s*(.+)$', linea)
            if match:
                items.append(match.group(1).strip())

        return items if items else [texto]

    def _formatear_reportes(self, reportes: List[Dict]) -> str:
        """Formatea lista de reportes"""
        if not reportes:
            return ""

        return "\n".join([
            f"- {r.get('autor', 'Anónimo')} ({r.get('fecha', 'N/A')}): {r.get('contenido', '')}"
            for r in reportes
        ])

    # =========================================================
    # OPERACIONES DE BASE DE DATOS
    # =========================================================

    async def _crear_incidencia(
        self,
        titulo: str,
        descripcion: str,
        area: str,
        usuario: str,
        prioridad: str,
        checkpoint_id: Optional[str] = None
    ) -> str:
        """Crea una incidencia en la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        incidencia_id = str(uuid.uuid4())
        ahora = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO incidencias
            (id, titulo, descripcion, area, prioridad, creado_por,
             fecha_creacion, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incidencia_id, titulo, descripcion, area, prioridad,
            usuario, ahora, ahora
        ))

        conn.commit()
        conn.close()

        return incidencia_id

    async def _get_incidencia(self, incidencia_id: str) -> Optional[Dict]:
        """Obtiene una incidencia de la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM incidencias WHERE id = ?",
            (incidencia_id,)
        )
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    async def _get_reportes(self, incidencia_id: str) -> List[Dict]:
        """Obtiene reportes de una incidencia"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM reportes WHERE incidencia_id = ? ORDER BY fecha",
            (incidencia_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    async def _actualizar_incidencia_resuelta(
        self,
        incidencia_id: str,
        solucion: str,
        version: str,
        agregar_a_rag: bool
    ):
        """Actualiza incidencia como resuelta"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE incidencias
            SET estado = 'resuelto',
                solucion = ?,
                fecha_actualizacion = ?,
                agregado_a_rag = ?
            WHERE id = ?
        """, (
            solucion,
            datetime.now().isoformat(),
            1 if agregar_a_rag else 0,
            incidencia_id
        ))

        conn.commit()
        conn.close()

    # =========================================================
    # MÉTODOS PÚBLICOS DE UTILIDAD
    # =========================================================

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas del sistema PR"""
        return {
            "memoria": self.memoria.estadisticas(),
            "versiones": self.versiones.obtener_estadisticas(),
            "checkpoints_activos": len([
                c for c in self.ciclo.checkpoints.values()
                if c.estado == EstadoCheckpoint.ACTIVO
            ])
        }

    def obtener_historial_area(self, area: str) -> Dict:
        """Obtiene historial de versiones de un área"""
        return self.versiones.obtener_historial_area(area)

    async def agregar_reporte(
        self,
        incidencia_id: str,
        contenido: str,
        autor: str
    ) -> Dict:
        """Agrega un reporte a una incidencia existente"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        reporte_id = str(uuid.uuid4())
        ahora = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO reportes (id, incidencia_id, autor, contenido, fecha)
            VALUES (?, ?, ?, ?, ?)
        """, (reporte_id, incidencia_id, autor, contenido, ahora))

        cursor.execute(
            "UPDATE incidencias SET fecha_actualizacion = ? WHERE id = ?",
            (ahora, incidencia_id)
        )

        conn.commit()
        conn.close()

        return {
            "id": reporte_id,
            "incidencia_id": incidencia_id,
            "mensaje": "Reporte agregado"
        }
