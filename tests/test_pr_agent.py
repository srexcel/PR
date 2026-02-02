"""
Tests para el módulo PR-Agent
=============================

Ejecutar con: pytest tests/test_pr_agent.py -v
"""

import pytest
import tempfile
import os
import sys

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pr_agent import CicloPR, SistemaVersiones, MemoriaPR
from pr_agent.ciclo import EstadoCheckpoint, FaseCiclo


class TestCicloPR:
    """Tests para CicloPR - El ciclo de 3 preguntas"""

    def setup_method(self):
        self.ciclo = CicloPR()

    def test_crear_checkpoint(self):
        """Test: Crear checkpoint guarda estado correctamente"""
        resultado = self.ciclo.crear_checkpoint(
            descripcion="Problema de soldadura en línea 3",
            area="Producción",
            usuario="Juan Pérez"
        )

        assert "id" in resultado
        assert resultado["fase"] == "ANTES"
        assert resultado["pregunta"] == "¿Dónde estoy?"
        assert resultado["puede_rollback"] == False

    def test_checkpoint_con_parent(self):
        """Test: Checkpoint con parent permite rollback"""
        cp1 = self.ciclo.crear_checkpoint("Problema 1", "AREA", "Usuario")
        cp2 = self.ciclo.crear_checkpoint(
            "Problema 2", "AREA", "Usuario",
            parent_id=cp1["id"]
        )

        assert cp2["puede_rollback"] == True

    def test_declarar_intento(self):
        """Test: Declarar intento registra acción"""
        cp = self.ciclo.crear_checkpoint("Problema", "AREA", "Usuario")

        resultado = self.ciclo.declarar_intento(
            checkpoint_id=cp["id"],
            intento="Revisar conexiones eléctricas"
        )

        assert resultado["numero_intento"] == 1
        assert "Asume fracaso" in resultado["axioma"]

    def test_registrar_resultado_exito(self):
        """Test: Registrar éxito actualiza intento"""
        cp = self.ciclo.crear_checkpoint("Problema", "AREA", "Usuario")
        intento = self.ciclo.declarar_intento(cp["id"], "Acción test")

        resultado = self.ciclo.registrar_resultado(
            checkpoint_id=cp["id"],
            intento_id=intento["intento_id"],
            resultado="Problema resuelto",
            exito=True
        )

        assert resultado["exito"] == True
        assert resultado["fase"] == "DURANTE"

    def test_registrar_resultado_fallo(self):
        """Test: Registrar fallo ofrece opciones"""
        cp = self.ciclo.crear_checkpoint("Problema", "AREA", "Usuario")
        intento = self.ciclo.declarar_intento(cp["id"], "Acción test")

        resultado = self.ciclo.registrar_resultado(
            checkpoint_id=cp["id"],
            intento_id=intento["intento_id"],
            resultado="No funcionó",
            exito=False
        )

        assert resultado["exito"] == False
        assert len(resultado["opciones"]) == 3  # degradar, iterar, rollback

    def test_cerrar_ciclo(self):
        """Test: Cerrar ciclo hereda conocimiento"""
        cp = self.ciclo.crear_checkpoint("Problema", "AREA", "Usuario")

        resultado = self.ciclo.cerrar_ciclo(
            checkpoint_id=cp["id"],
            resultado_final="Resuelto",
            aprendizaje="La causa fue X, la solución es Y",
            heredar=["AREA_v1.0"]
        )

        assert resultado["fase"] == "DESPUÉS"
        assert resultado["estado"] == "resuelto"
        assert "AREA_v1.0" in resultado["heredado"]

    def test_rollback(self):
        """Test: Rollback cambia estado"""
        cp = self.ciclo.crear_checkpoint("Problema", "AREA", "Usuario")

        resultado = self.ciclo.rollback(cp["id"])

        assert resultado["estado_nuevo"] == "rollback"

    def test_listar_checkpoints(self):
        """Test: Listar checkpoints filtra correctamente"""
        self.ciclo.crear_checkpoint("P1", "AREA1", "U1")
        self.ciclo.crear_checkpoint("P2", "AREA2", "U2")
        self.ciclo.crear_checkpoint("P3", "AREA1", "U3")

        lista_area1 = self.ciclo.listar_checkpoints(area="AREA1")
        assert len(lista_area1) == 2


class TestSistemaVersiones:
    """Tests para SistemaVersiones - Versionado de conocimiento"""

    def setup_method(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.versiones = SistemaVersiones(self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_crear_primera_version(self):
        """Test: Primera versión es v1.0"""
        version = self.versiones.crear_version("Soldadura", "caso_resuelto")

        assert version == "SOLDADURA_v1.0"

    def test_incrementar_version(self):
        """Test: Versiones incrementan minor"""
        v1 = self.versiones.crear_version("Soldadura", "caso_resuelto")
        v2 = self.versiones.crear_version("Soldadura", "caso_resuelto")
        v3 = self.versiones.crear_version("Soldadura", "caso_resuelto")

        assert v1 == "SOLDADURA_v1.0"
        assert v2 == "SOLDADURA_v1.1"
        assert v3 == "SOLDADURA_v1.2"

    def test_areas_independientes(self):
        """Test: Diferentes áreas tienen versiones independientes"""
        vs = self.versiones.crear_version("Soldadura", "test")
        vp = self.versiones.crear_version("Pintura", "test")
        vs2 = self.versiones.crear_version("Soldadura", "test")

        assert vs == "SOLDADURA_v1.0"
        assert vp == "PINTURA_v1.0"
        assert vs2 == "SOLDADURA_v1.1"

    def test_normalizar_area(self):
        """Test: Áreas se normalizan correctamente"""
        v1 = self.versiones.crear_version("línea 3", "test")
        v2 = self.versiones.crear_version("LÍNEA 3", "test")

        assert v1 == "LINEA_3_v1.0"
        assert v2 == "LINEA_3_v1.1"  # Mismo área normalizada

    def test_incrementar_major(self):
        """Test: Incrementar major reinicia minor"""
        v1 = self.versiones.crear_version("Area", "test")
        v2 = self.versiones.crear_version("Area", "test")
        v3 = self.versiones.crear_version("Area", "test", incrementar_major=True)
        v4 = self.versiones.crear_version("Area", "test")

        assert v1 == "AREA_v1.0"
        assert v2 == "AREA_v1.1"
        assert v3 == "AREA_v2.0"  # Major incrementado
        assert v4 == "AREA_v2.1"

    def test_historial_area(self):
        """Test: Historial muestra evolución"""
        self.versiones.crear_version("Test", "t1")
        self.versiones.crear_version("Test", "t2")
        self.versiones.crear_version("Test", "t3")

        historial = self.versiones.obtener_historial_area("Test")

        assert historial["total_versiones"] == 3
        assert historial["version_actual"] == "TEST_v1.2"
        assert historial["primera_version"] == "TEST_v1.0"
        assert "TEST_v1.0 → TEST_v1.1 → TEST_v1.2" in historial["evolucion"]

    def test_estadisticas(self):
        """Test: Estadísticas cuentan correctamente"""
        self.versiones.crear_version("Area1", "tipo1")
        self.versiones.crear_version("Area1", "tipo1")
        self.versiones.crear_version("Area2", "tipo2")

        stats = self.versiones.obtener_estadisticas()

        assert stats["total_versiones"] == 3
        assert stats["total_areas"] == 2


class TestMemoriaPR:
    """Tests para MemoriaPR - Wrapper de RAG"""

    def test_count_sin_coleccion(self):
        """Test: Count retorna 0 sin colección"""
        memoria = MemoriaPR(None)
        assert memoria.count() == 0

    def test_estadisticas_vacia(self):
        """Test: Estadísticas con memoria vacía"""
        memoria = MemoriaPR(None)
        stats = memoria.estadisticas()

        assert stats["total_documentos"] == 0
        assert stats["estado"] == "vacia"


class TestIntegracion:
    """Tests de integración del módulo completo"""

    def test_flujo_completo_ciclo_versiones(self):
        """Test: Flujo completo ciclo PR + versionado"""
        ciclo = CicloPR()
        db_path = tempfile.mktemp(suffix=".db")
        versiones = SistemaVersiones(db_path)

        # 1. Crear checkpoint (ANTES)
        cp = ciclo.crear_checkpoint(
            "Falla en soldadura",
            "Producción",
            "Operador"
        )
        assert cp["fase"] == "ANTES"

        # 2. Declarar y ejecutar intento (DURANTE)
        intento = ciclo.declarar_intento(cp["id"], "Revisar electrodos")
        ciclo.registrar_resultado(
            cp["id"], intento["intento_id"],
            "Electrodos desgastados", True
        )

        # 3. Cerrar ciclo y crear versión (DESPUÉS)
        version = versiones.crear_version(
            "Soldadura",
            "caso_resuelto",
            aprendizaje="Electrodos deben cambiarse cada 5000 ciclos"
        )

        cierre = ciclo.cerrar_ciclo(
            cp["id"],
            "Resuelto",
            "Electrodos desgastados causan porosidad",
            heredar=[version]
        )

        assert cierre["fase"] == "DESPUÉS"
        assert version in cierre["heredado"]
        assert version == "SOLDADURA_v1.0"

        # Limpiar
        os.remove(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
