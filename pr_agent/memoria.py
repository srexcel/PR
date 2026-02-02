"""
MemoriaPR: Memoria Inteligente con RAG
======================================

Wrapper inteligente para ChromaDB que implementa
la "memoria en RAM" del concepto PR.

Diferencia con ISO (memoria en papel):
- Siempre accesible (no en carpetas olvidadas)
- Busca patrones automáticamente
- Conecta casos por similitud semántica
- Hereda conocimiento válido
- Depura conocimiento obsoleto

"La memoria no tiene propósito. Solo tiene estímulo.
PR provoca estímulos sistemáticamente."
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class MemoriaPR:
    """
    Memoria de conocimiento vivo para PR-System.

    Usa ChromaDB como backend para búsqueda semántica,
    permitiendo encontrar casos similares por significado,
    no solo por palabras exactas.

    Uso:
        memoria = MemoriaPR(collection)

        # Buscar casos similares
        casos = await memoria.buscar_similares("problema con soldadura")

        # Guardar nuevo conocimiento
        await memoria.guardar(documento, metadata)

        # Depurar conocimiento obsoleto
        await memoria.depurar(["id1", "id2"])
    """

    def __init__(self, collection: Any):
        """
        Inicializa la memoria PR.

        Args:
            collection: Colección de ChromaDB
        """
        self.collection = collection

    async def buscar_similares(
        self,
        query: str,
        area: Optional[str] = None,
        tipo: Optional[str] = None,
        n_resultados: int = 5,
        umbral_relevancia: float = 0.5
    ) -> List[Dict]:
        """
        Busca casos similares en la memoria.

        Implementa: "¿Qué aprendimos la última vez que pasó esto?"

        Args:
            query: Texto de búsqueda (descripción del problema)
            area: Filtrar por área específica
            tipo: Filtrar por tipo de documento
            n_resultados: Número máximo de resultados
            umbral_relevancia: Mínimo de relevancia (0-1)

        Returns:
            Lista de casos similares ordenados por relevancia
        """
        if not self.collection or self.collection.count() == 0:
            return []

        # Enriquecer query con contexto
        query_enriquecida = self._enriquecer_query(query, area)

        # Construir filtro where si hay criterios
        where_filter = self._construir_filtro(area, tipo)

        try:
            resultados = self.collection.query(
                query_texts=[query_enriquecida],
                n_results=n_resultados,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )

            # Procesar resultados
            casos = []
            if resultados and resultados['documents'] and resultados['documents'][0]:
                for i, (doc, meta, dist) in enumerate(zip(
                    resultados['documents'][0],
                    resultados['metadatas'][0],
                    resultados['distances'][0]
                )):
                    # Convertir distancia a relevancia (0-1)
                    # ChromaDB usa distancia L2, menor es mejor
                    relevancia = max(0, 1 - (dist / 2))

                    if relevancia >= umbral_relevancia:
                        casos.append({
                            "contenido": doc,
                            "metadata": meta,
                            "relevancia": round(relevancia, 3),
                            "relevancia_pct": f"{relevancia * 100:.1f}%",
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
        Guarda un documento en la memoria.

        Implementa: Heredar conocimiento válido.

        Args:
            documento: Texto del documento a guardar
            metadata: Metadatos del documento (tipo, area, fecha, etc.)
            id_override: ID específico (opcional)

        Returns:
            Resultado de la operación
        """
        if not self.collection:
            return {
                "guardado": False,
                "error": "Colección no inicializada"
            }

        # Generar ID único si no se proporciona
        doc_id = id_override or f"pr_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Asegurar que metadata tenga timestamp
        if "fecha" not in metadata:
            metadata["fecha"] = datetime.now().isoformat()

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

    async def actualizar(
        self,
        doc_id: str,
        documento: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Actualiza un documento existente.

        Útil para corregir información sin perder el histórico.
        """
        if not self.collection:
            return {"actualizado": False, "error": "Colección no inicializada"}

        try:
            update_args = {"ids": [doc_id]}

            if documento:
                update_args["documents"] = [documento]

            if metadata:
                metadata["fecha_actualizacion"] = datetime.now().isoformat()
                update_args["metadatas"] = [metadata]

            self.collection.update(**update_args)

            return {
                "id": doc_id,
                "actualizado": True,
                "mensaje": "Documento actualizado"
            }

        except Exception as e:
            return {
                "id": doc_id,
                "actualizado": False,
                "error": str(e)
            }

    async def depurar(self, ids_a_eliminar: List[str]) -> Dict:
        """
        Elimina documentos obsoletos o inválidos.

        Implementa: Depurar lo inválido del ciclo PR.

        En filosofía PR, no se elimina conocimiento a la ligera.
        Solo se depura lo que está comprobadamente mal o
        ha sido superado por versiones mejores.
        """
        if not self.collection:
            return {"depurado": False, "error": "Colección no inicializada"}

        if not ids_a_eliminar:
            return {"depurado": False, "error": "No hay IDs para eliminar"}

        try:
            # Obtener documentos antes de eliminar (para log)
            existentes = self.collection.get(ids=ids_a_eliminar)
            docs_eliminados = len(existentes['ids']) if existentes else 0

            self.collection.delete(ids=ids_a_eliminar)

            return {
                "depurado": True,
                "documentos_eliminados": docs_eliminados,
                "ids_eliminados": ids_a_eliminar,
                "total_en_memoria": self.collection.count(),
                "mensaje": f"Depurados {docs_eliminados} documentos inválidos"
            }

        except Exception as e:
            return {
                "depurado": False,
                "error": str(e)
            }

    async def obtener(self, doc_id: str) -> Optional[Dict]:
        """Obtiene un documento específico por ID"""
        if not self.collection:
            return None

        try:
            resultado = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )

            if resultado and resultado['documents']:
                return {
                    "id": doc_id,
                    "contenido": resultado['documents'][0],
                    "metadata": resultado['metadatas'][0] if resultado['metadatas'] else {}
                }

            return None

        except Exception as e:
            print(f"Error obteniendo documento: {e}")
            return None

    def count(self) -> int:
        """Retorna total de documentos en memoria"""
        if not self.collection:
            return 0
        try:
            return self.collection.count()
        except:
            return 0

    def estadisticas(self) -> Dict:
        """
        Obtiene estadísticas de la memoria.

        Útil para monitoreo y dashboard.
        """
        total = self.count()

        if total == 0:
            return {
                "total_documentos": 0,
                "estado": "vacia",
                "por_tipo": {},
                "por_area": {},
                "mensaje": "La memoria está vacía. Comienza a resolver casos."
            }

        # Obtener todos los metadatos para estadísticas
        try:
            todos = self.collection.get(include=["metadatas"])
            metadatas = todos.get('metadatas', [])

            # Contar por tipo
            por_tipo = {}
            por_area = {}

            for meta in metadatas:
                if meta:
                    tipo = meta.get("tipo", "desconocido")
                    area = meta.get("area", "sin_area")

                    por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
                    por_area[area] = por_area.get(area, 0) + 1

            return {
                "total_documentos": total,
                "estado": "activo",
                "por_tipo": por_tipo,
                "por_area": por_area,
                "descripcion": "Memoria PR - Conocimiento vivo accesible"
            }

        except Exception as e:
            return {
                "total_documentos": total,
                "estado": "error_estadisticas",
                "error": str(e)
            }

    async def buscar_por_metadata(
        self,
        filtros: Dict,
        limite: int = 10
    ) -> List[Dict]:
        """
        Busca documentos por metadatos específicos.

        Útil para filtrar por área, tipo, fecha, etc.
        """
        if not self.collection:
            return []

        try:
            where_filter = {}
            for key, value in filtros.items():
                if value is not None:
                    where_filter[key] = value

            if not where_filter:
                return []

            resultados = self.collection.get(
                where=where_filter,
                limit=limite,
                include=["documents", "metadatas"]
            )

            casos = []
            if resultados and resultados['documents']:
                for doc, meta, doc_id in zip(
                    resultados['documents'],
                    resultados['metadatas'],
                    resultados['ids']
                ):
                    casos.append({
                        "id": doc_id,
                        "contenido": doc,
                        "metadata": meta
                    })

            return casos

        except Exception as e:
            print(f"Error buscando por metadata: {e}")
            return []

    def _enriquecer_query(self, query: str, area: Optional[str] = None) -> str:
        """
        Enriquece la query con contexto adicional.

        Mejora la búsqueda semántica agregando contexto.
        """
        partes = [query]

        if area:
            partes.insert(0, f"[Área: {area}]")

        return " ".join(partes)

    def _construir_filtro(
        self,
        area: Optional[str] = None,
        tipo: Optional[str] = None
    ) -> Optional[Dict]:
        """Construye filtro where para ChromaDB"""
        condiciones = []

        if area:
            condiciones.append({"area": area})

        if tipo:
            condiciones.append({"tipo": tipo})

        if not condiciones:
            return None

        if len(condiciones) == 1:
            return condiciones[0]

        return {"$and": condiciones}

    async def obtener_contexto_para_llm(
        self,
        query: str,
        n_casos: int = 3
    ) -> str:
        """
        Obtiene contexto formateado para enviar al LLM.

        Busca casos similares y los formatea para que el LLM
        pueda usar el conocimiento histórico.
        """
        casos = await self.buscar_similares(query, n_resultados=n_casos)

        if not casos:
            return "No se encontraron casos similares en la base de conocimiento."

        contexto = "CASOS SIMILARES EN BASE DE CONOCIMIENTO:\n"
        contexto += "=" * 50 + "\n\n"

        for i, caso in enumerate(casos, 1):
            contexto += f"--- Caso {i} (Relevancia: {caso['relevancia_pct']}) ---\n"

            if caso.get('metadata'):
                meta = caso['metadata']
                if meta.get('version'):
                    contexto += f"Versión: {meta['version']}\n"
                if meta.get('area'):
                    contexto += f"Área: {meta['area']}\n"
                if meta.get('fecha'):
                    contexto += f"Fecha: {meta['fecha']}\n"

            contexto += f"\n{caso['contenido']}\n\n"

        contexto += "=" * 50 + "\n"

        return contexto
