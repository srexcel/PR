"""
CicloPR: Implementación del ciclo de 3 preguntas
=================================================

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

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import uuid


class EstadoCheckpoint(str, Enum):
    """Estados posibles de un checkpoint"""
    ACTIVO = "activo"
    RESUELTO = "resuelto"
    ROLLBACK = "rollback"
    ABANDONADO = "abandonado"


class FaseCiclo(str, Enum):
    """Fases del ciclo PR"""
    ANTES = "ANTES"
    DURANTE = "DURANTE"
    DESPUES = "DESPUÉS"


@dataclass
class Checkpoint:
    """
    Representa un punto de guardado en el ciclo PR.
    Permite volver atrás si algo falla.
    """
    id: str
    timestamp: str
    descripcion: str
    area: str
    usuario: str
    estado: EstadoCheckpoint = EstadoCheckpoint.ACTIVO
    parent_id: Optional[str] = None
    intentos: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "descripcion": self.descripcion,
            "area": self.area,
            "usuario": self.usuario,
            "estado": self.estado.value,
            "parent_id": self.parent_id,
            "intentos": self.intentos,
            "metadata": self.metadata
        }


class CicloPR:
    """
    Implementa el ciclo PR de 3 preguntas.

    Uso:
        ciclo = CicloPR()

        # ANTES: ¿Dónde estoy?
        checkpoint = ciclo.crear_checkpoint(descripcion, area, usuario)

        # DURANTE: ¿Cómo falla?
        ciclo.registrar_intento(checkpoint_id, accion, resultado)

        # DESPUÉS: ¿Qué aprendí?
        ciclo.cerrar_ciclo(checkpoint_id, resultado, aprendizaje)
    """

    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}
        self._axiomas = {
            0: "Asume fracaso - Diseña desde el error",
            1: "No hay meta final - Solo siguiente iteración",
            2: "Todo colapsa - Prepárate para ello",
            3: "Error = dato - Los fallos son información"
        }

    # =========================================================
    # ANTES: ¿Dónde estoy?
    # =========================================================

    def crear_checkpoint(
        self,
        descripcion: str,
        area: str,
        usuario: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Paso 1: Crear checkpoint del estado actual.

        Guarda el estado antes de intentar cualquier acción,
        permitiendo rollback si algo falla.
        """
        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            descripcion=descripcion,
            area=area,
            usuario=usuario,
            estado=EstadoCheckpoint.ACTIVO,
            parent_id=parent_id,
            metadata=metadata or {}
        )

        self.checkpoints[checkpoint.id] = checkpoint

        return {
            "id": checkpoint.id,
            "timestamp": checkpoint.timestamp,
            "fase": FaseCiclo.ANTES.value,
            "pregunta": "¿Dónde estoy?",
            "puede_rollback": parent_id is not None,
            "axioma": self._axiomas[0],
            "mensaje": "Checkpoint creado. Podemos volver a este punto si algo falla."
        }

    def obtener_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Obtiene un checkpoint por ID"""
        return self.checkpoints.get(checkpoint_id)

    def rollback(self, checkpoint_id: str) -> Dict:
        """
        Paso 2: Volver a un checkpoint anterior.

        Marca el checkpoint actual como rollback y permite
        reintentar desde un punto conocido.
        """
        if checkpoint_id not in self.checkpoints:
            return {
                "error": "Checkpoint no encontrado",
                "checkpoint_id": checkpoint_id
            }

        checkpoint = self.checkpoints[checkpoint_id]
        estado_anterior = checkpoint.estado
        checkpoint.estado = EstadoCheckpoint.ROLLBACK

        return {
            "id": checkpoint_id,
            "fase": FaseCiclo.ANTES.value,
            "pregunta": "¿Dónde estoy?",
            "estado_anterior": estado_anterior.value,
            "estado_nuevo": EstadoCheckpoint.ROLLBACK.value,
            "timestamp_original": checkpoint.timestamp,
            "axioma": self._axiomas[2],
            "mensaje": f"Rollback ejecutado a checkpoint {checkpoint_id[:8]}..."
        }

    def declarar_intento(
        self,
        checkpoint_id: str,
        intento: str,
        expectativa: Optional[str] = None
    ) -> Dict:
        """
        Paso 3: Declarar qué vamos a intentar.

        Documenta la acción a realizar antes de ejecutarla,
        aplicando el Axioma 0: Asume que puede fallar.
        """
        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]

        intento_registro = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "accion_declarada": intento,
            "expectativa": expectativa,
            "resultado": None,
            "exito": None
        }

        checkpoint.intentos.append(intento_registro)

        return {
            "checkpoint_id": checkpoint_id,
            "intento_id": intento_registro["id"],
            "fase": FaseCiclo.ANTES.value,
            "pregunta": "¿Dónde estoy?",
            "intento_declarado": intento,
            "numero_intento": len(checkpoint.intentos),
            "axioma": self._axiomas[0],
            "mensaje": f"Intento #{len(checkpoint.intentos)} registrado: {intento}"
        }

    # =========================================================
    # DURANTE: ¿Cómo falla?
    # =========================================================

    def registrar_resultado(
        self,
        checkpoint_id: str,
        intento_id: str,
        resultado: str,
        exito: bool
    ) -> Dict:
        """
        Paso 4-5: Registrar resultado del intento.

        Documenta si el intento fue exitoso o no,
        aplicando Axioma 3: Error = dato.
        """
        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]

        # Buscar el intento
        intento = None
        for i in checkpoint.intentos:
            if i["id"] == intento_id:
                intento = i
                break

        if not intento:
            return {"error": "Intento no encontrado"}

        intento["resultado"] = resultado
        intento["exito"] = exito
        intento["timestamp_resultado"] = datetime.now().isoformat()

        return {
            "checkpoint_id": checkpoint_id,
            "intento_id": intento_id,
            "fase": FaseCiclo.DURANTE.value,
            "pregunta": "¿Cómo falla?",
            "exito": exito,
            "resultado": resultado,
            "axioma": self._axiomas[3],
            "mensaje": "Éxito registrado" if exito else "Fallo registrado como dato útil",
            "opciones": [] if exito else [
                {"accion": "degradar", "desc": "Reducir alcance y continuar"},
                {"accion": "iterar", "desc": "Nuevo intento con ajuste"},
                {"accion": "rollback", "desc": "Volver al checkpoint anterior"}
            ]
        }

    def registrar_fallo(
        self,
        checkpoint_id: str,
        tipo_fallo: str,
        detalle: str,
        es_recuperable: bool = True
    ) -> Dict:
        """
        Paso 4-6: Registrar un fallo y decidir siguiente paso.

        Cuando algo falla, registra la información y ofrece
        opciones para continuar (degradar, iterar, rollback).
        """
        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]

        fallo_registro = {
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo_fallo,
            "detalle": detalle,
            "es_recuperable": es_recuperable
        }

        if "fallos" not in checkpoint.metadata:
            checkpoint.metadata["fallos"] = []
        checkpoint.metadata["fallos"].append(fallo_registro)

        return {
            "checkpoint_id": checkpoint_id,
            "fase": FaseCiclo.DURANTE.value,
            "pregunta": "¿Cómo falla?",
            "tipo_fallo": tipo_fallo,
            "detalle": detalle,
            "es_recuperable": es_recuperable,
            "total_intentos": len(checkpoint.intentos),
            "axioma": self._axiomas[3],
            "mensaje": "Fallo registrado. Cada error es un dato valioso.",
            "opciones": [
                {"accion": "degradar", "desc": "Reducir alcance y continuar"},
                {"accion": "iterar", "desc": "Nuevo intento con ajuste"},
                {"accion": "rollback", "desc": "Volver al checkpoint"}
            ] if es_recuperable else [
                {"accion": "escalar", "desc": "Escalar a supervisor"},
                {"accion": "documentar", "desc": "Documentar como caso especial"}
            ]
        }

    # =========================================================
    # DESPUÉS: ¿Qué aprendí?
    # =========================================================

    def cerrar_ciclo(
        self,
        checkpoint_id: str,
        resultado_final: str,
        aprendizaje: str,
        depurar: Optional[List[str]] = None,
        heredar: Optional[List[str]] = None
    ) -> Dict:
        """
        Pasos 7-9: Cerrar ciclo y preparar siguiente versión.

        Documenta el resultado final, qué se aprendió,
        qué se depura (elimina) y qué se hereda (conserva).
        """
        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint.estado = EstadoCheckpoint.RESUELTO

        # Calcular estadísticas
        intentos_exitosos = sum(1 for i in checkpoint.intentos if i.get("exito"))
        intentos_fallidos = len(checkpoint.intentos) - intentos_exitosos

        cierre = {
            "timestamp": datetime.now().isoformat(),
            "resultado_final": resultado_final,
            "aprendizaje": aprendizaje,
            "depurado": depurar or [],
            "heredado": heredar or [],
            "estadisticas": {
                "total_intentos": len(checkpoint.intentos),
                "exitosos": intentos_exitosos,
                "fallidos": intentos_fallidos
            }
        }

        checkpoint.metadata["cierre"] = cierre

        return {
            "checkpoint_id": checkpoint_id,
            "fase": FaseCiclo.DESPUES.value,
            "pregunta": "¿Qué aprendí?",
            "estado": EstadoCheckpoint.RESUELTO.value,
            "resultado": resultado_final,
            "aprendizaje": aprendizaje,
            "depurado": depurar or [],
            "heredado": heredar or [],
            "estadisticas": cierre["estadisticas"],
            "axioma": self._axiomas[1],
            "mensaje": "Ciclo cerrado. Conocimiento listo para heredar a siguiente versión."
        }

    def abandonar_checkpoint(
        self,
        checkpoint_id: str,
        razon: str
    ) -> Dict:
        """
        Abandona un checkpoint sin resolver.

        Útil cuando se decide no continuar con un caso,
        pero se documenta la razón para el futuro.
        """
        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint.estado = EstadoCheckpoint.ABANDONADO
        checkpoint.metadata["abandono"] = {
            "timestamp": datetime.now().isoformat(),
            "razon": razon
        }

        return {
            "checkpoint_id": checkpoint_id,
            "estado": EstadoCheckpoint.ABANDONADO.value,
            "razon": razon,
            "mensaje": "Checkpoint abandonado. Razón documentada para futuro análisis."
        }

    # =========================================================
    # Utilidades
    # =========================================================

    def obtener_historial(self, checkpoint_id: str) -> Dict:
        """Obtiene el historial completo de un checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return {"error": "Checkpoint no encontrado"}

        checkpoint = self.checkpoints[checkpoint_id]

        return {
            "checkpoint": checkpoint.to_dict(),
            "resumen": {
                "total_intentos": len(checkpoint.intentos),
                "estado_actual": checkpoint.estado.value,
                "duracion": self._calcular_duracion(checkpoint)
            }
        }

    def listar_checkpoints(
        self,
        estado: Optional[EstadoCheckpoint] = None,
        area: Optional[str] = None
    ) -> List[Dict]:
        """Lista checkpoints con filtros opcionales"""
        resultado = []

        for cp in self.checkpoints.values():
            if estado and cp.estado != estado:
                continue
            if area and cp.area.lower() != area.lower():
                continue
            resultado.append(cp.to_dict())

        return sorted(resultado, key=lambda x: x["timestamp"], reverse=True)

    def _calcular_duracion(self, checkpoint: Checkpoint) -> Optional[str]:
        """Calcula duración desde creación hasta cierre"""
        if "cierre" not in checkpoint.metadata:
            return None

        inicio = datetime.fromisoformat(checkpoint.timestamp)
        fin = datetime.fromisoformat(checkpoint.metadata["cierre"]["timestamp"])
        duracion = fin - inicio

        return str(duracion)

    def obtener_axioma(self, numero: int) -> str:
        """Obtiene el texto de un axioma PR"""
        return self._axiomas.get(numero, "Axioma no encontrado")
