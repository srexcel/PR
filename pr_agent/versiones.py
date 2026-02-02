"""
SistemaVersiones: Versionado de Conocimiento PR
===============================================

Sistema de versionado para conocimiento empresarial.

Formato: {AREA}_v{MAJOR}.{MINOR}
Ejemplo: SOLDADURA_v1.0, SOLDADURA_v1.1, LINEA3_v2.0

- MAJOR: Nuevo tipo de problema/área
- MINOR: Nueva solución/variante del mismo problema

Filosofía PR:
"No hay meta final, solo hay siguiente versión"
Cada caso resuelto incrementa el conocimiento: v1.0 → v1.1 → v1.2 → ...
"""

import sqlite3
import re
from datetime import datetime
from typing import Optional, Dict, List
import os


class SistemaVersiones:
    """
    Sistema de versionado para conocimiento PR.

    Cada vez que se resuelve un caso, se crea una nueva versión
    que hereda y mejora el conocimiento anterior.

    Uso:
        versiones = SistemaVersiones("/path/to/db")

        # Crear versión
        v = versiones.crear_version("Soldadura", "caso_resuelto")
        # Returns: "SOLDADURA_v1.0"

        # Siguiente versión del mismo área
        v2 = versiones.crear_version("Soldadura", "caso_resuelto")
        # Returns: "SOLDADURA_v1.1"
    """

    def __init__(self, db_path: str):
        """
        Inicializa el sistema de versiones.

        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        self._init_tabla()

    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tabla(self):
        """Crea tabla de versiones si no existe"""
        conn = self._get_connection()
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
                aprendizaje TEXT,
                keywords TEXT,
                metadata TEXT,
                UNIQUE(area, major, minor)
            )
        """)

        # Índices para búsquedas rápidas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versiones_area
            ON pr_versiones(area)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_versiones_fecha
            ON pr_versiones(fecha DESC)
        """)

        conn.commit()
        conn.close()

    def crear_version(
        self,
        area: str,
        tipo: str,
        incidencia_id: Optional[str] = None,
        descripcion: Optional[str] = None,
        aprendizaje: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        incrementar_major: bool = False
    ) -> str:
        """
        Crea una nueva versión para un área.

        Args:
            area: Nombre del área (ej: "Soldadura", "Línea 3")
            tipo: Tipo de versión ("caso_resuelto", "documento", etc.)
            incidencia_id: ID de la incidencia relacionada
            descripcion: Descripción breve de la versión
            aprendizaje: Qué se aprendió en esta versión
            keywords: Palabras clave para búsqueda
            incrementar_major: Si True, incrementa versión mayor

        Returns:
            String de versión (ej: "SOLDADURA_v1.2")
        """
        area_normalizada = self._normalizar_area(area)

        # Obtener última versión del área
        ultima = self._get_ultima_version(area_normalizada)

        if ultima is None:
            # Primera versión del área
            major, minor = 1, 0
        elif incrementar_major:
            # Nueva versión mayor
            major = ultima["major"] + 1
            minor = 0
        else:
            # Incrementar minor
            major = ultima["major"]
            minor = ultima["minor"] + 1

        version_str = f"{area_normalizada}_v{major}.{minor}"
        version_id = f"{area_normalizada}_{major}_{minor}"

        # Guardar en BD
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO pr_versiones
                (id, area, major, minor, version_str, tipo, fecha,
                 incidencia_id, descripcion, aprendizaje, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id,
                area_normalizada,
                major,
                minor,
                version_str,
                tipo,
                datetime.now().isoformat(),
                incidencia_id,
                descripcion,
                aprendizaje,
                ",".join(keywords) if keywords else None
            ))
            conn.commit()
        finally:
            conn.close()

        return version_str

    def _get_ultima_version(self, area: str) -> Optional[Dict]:
        """Obtiene la última versión de un área"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT major, minor, version_str, fecha, tipo
            FROM pr_versiones
            WHERE area = ?
            ORDER BY major DESC, minor DESC
            LIMIT 1
        """, (area,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "major": row["major"],
                "minor": row["minor"],
                "version_str": row["version_str"],
                "fecha": row["fecha"],
                "tipo": row["tipo"]
            }
        return None

    def obtener_version(self, version_str: str) -> Optional[Dict]:
        """Obtiene información completa de una versión"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM pr_versiones WHERE version_str = ?
        """, (version_str,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def listar_versiones(
        self,
        area: Optional[str] = None,
        tipo: Optional[str] = None,
        limite: int = 50
    ) -> List[Dict]:
        """
        Lista versiones con filtros opcionales.

        Args:
            area: Filtrar por área
            tipo: Filtrar por tipo
            limite: Máximo de resultados

        Returns:
            Lista de versiones ordenadas por fecha descendente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM pr_versiones WHERE 1=1"
        params = []

        if area:
            query += " AND area = ?"
            params.append(self._normalizar_area(area))

        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)

        query += " ORDER BY fecha DESC LIMIT ?"
        params.append(limite)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def obtener_historial_area(self, area: str) -> Dict:
        """
        Obtiene el historial completo de versiones de un área.

        Muestra la evolución del conocimiento: v1.0 → v1.1 → v1.2 → ...
        """
        area_normalizada = self._normalizar_area(area)
        versiones = self.listar_versiones(area=area_normalizada, limite=1000)

        if not versiones:
            return {
                "area": area_normalizada,
                "total_versiones": 0,
                "version_actual": None,
                "primera_version": None,
                "historial": [],
                "mensaje": "No hay versiones para esta área"
            }

        # Ordenar cronológicamente para mostrar evolución
        historial_cronologico = sorted(versiones, key=lambda x: x["fecha"])

        return {
            "area": area_normalizada,
            "total_versiones": len(versiones),
            "version_actual": versiones[0]["version_str"],
            "primera_version": historial_cronologico[0]["version_str"],
            "fecha_inicio": historial_cronologico[0]["fecha"],
            "fecha_ultima": versiones[0]["fecha"],
            "historial": historial_cronologico,
            "evolucion": " → ".join([v["version_str"] for v in historial_cronologico])
        }

    def buscar_por_keywords(
        self,
        keywords: List[str],
        limite: int = 10
    ) -> List[Dict]:
        """Busca versiones por palabras clave"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Construir query con LIKE para cada keyword
        conditions = []
        params = []
        for kw in keywords:
            conditions.append("(keywords LIKE ? OR descripcion LIKE ? OR aprendizaje LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])

        query = f"""
            SELECT * FROM pr_versiones
            WHERE {" OR ".join(conditions)}
            ORDER BY fecha DESC
            LIMIT ?
        """
        params.append(limite)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas generales del sistema de versiones"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total de versiones
        cursor.execute("SELECT COUNT(*) as total FROM pr_versiones")
        total = cursor.fetchone()["total"]

        # Versiones por área
        cursor.execute("""
            SELECT area, COUNT(*) as count, MAX(version_str) as ultima
            FROM pr_versiones
            GROUP BY area
            ORDER BY count DESC
        """)
        por_area = [dict(row) for row in cursor.fetchall()]

        # Versiones por tipo
        cursor.execute("""
            SELECT tipo, COUNT(*) as count
            FROM pr_versiones
            GROUP BY tipo
        """)
        por_tipo = [dict(row) for row in cursor.fetchall()]

        # Última versión global
        cursor.execute("""
            SELECT version_str, area, fecha
            FROM pr_versiones
            ORDER BY fecha DESC
            LIMIT 1
        """)
        ultima_row = cursor.fetchone()
        ultima = dict(ultima_row) if ultima_row else None

        conn.close()

        return {
            "total_versiones": total,
            "total_areas": len(por_area),
            "por_area": por_area,
            "por_tipo": por_tipo,
            "ultima_version": ultima
        }

    def comparar_versiones(
        self,
        version_a: str,
        version_b: str
    ) -> Dict:
        """Compara dos versiones del mismo área"""
        va = self.obtener_version(version_a)
        vb = self.obtener_version(version_b)

        if not va or not vb:
            return {"error": "Una o ambas versiones no encontradas"}

        if va["area"] != vb["area"]:
            return {"error": "Las versiones son de áreas diferentes"}

        return {
            "version_anterior": version_a,
            "version_posterior": version_b,
            "area": va["area"],
            "diferencia_versiones": f"{va['major']}.{va['minor']} → {vb['major']}.{vb['minor']}",
            "aprendizaje_a": va.get("aprendizaje"),
            "aprendizaje_b": vb.get("aprendizaje"),
            "dias_entre": self._calcular_dias_entre(va["fecha"], vb["fecha"])
        }

    def _normalizar_area(self, area: str) -> str:
        """
        Normaliza nombre de área.

        - Convierte a mayúsculas
        - Reemplaza espacios y caracteres especiales por _
        - Elimina acentos
        """
        # Eliminar acentos
        acentos = {
            'á': 'A', 'é': 'E', 'í': 'I', 'ó': 'O', 'ú': 'U',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'N', 'Ñ': 'N'
        }
        resultado = area.upper()
        for acento, sin_acento in acentos.items():
            resultado = resultado.replace(acento, sin_acento)

        # Reemplazar caracteres no alfanuméricos por _
        resultado = re.sub(r'[^A-Z0-9]', '_', resultado)

        # Eliminar _ múltiples y al inicio/final
        resultado = re.sub(r'_+', '_', resultado).strip('_')

        return resultado

    def _calcular_dias_entre(self, fecha_a: str, fecha_b: str) -> int:
        """Calcula días entre dos fechas ISO"""
        try:
            dt_a = datetime.fromisoformat(fecha_a)
            dt_b = datetime.fromisoformat(fecha_b)
            return abs((dt_b - dt_a).days)
        except:
            return 0

    def eliminar_version(self, version_str: str) -> bool:
        """
        Elimina una versión (usar con precaución).

        Nota: En filosofía PR, es mejor no eliminar sino
        crear nueva versión que "depreca" la anterior.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM pr_versiones WHERE version_str = ?",
            (version_str,)
        )

        eliminado = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return eliminado
