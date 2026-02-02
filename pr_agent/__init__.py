"""
PR-Agent: Módulo de Conocimiento Vivo
=====================================

Implementa la metodología PR (Debug-First Design):
- Ciclo de 3 preguntas: Antes, Durante, Después
- Sistema de versionado de conocimiento
- Memoria inteligente con RAG

Axiomas PR:
- Axioma 0: Asume fracaso
- Axioma 1: No hay meta final
- Axioma 2: Todo colapsa
- Axioma 3: Error = dato
"""

from .agent import PRAgent
from .ciclo import CicloPR, Checkpoint
from .versiones import SistemaVersiones
from .memoria import MemoriaPR

__all__ = [
    "PRAgent",
    "CicloPR",
    "Checkpoint",
    "SistemaVersiones",
    "MemoriaPR",
]

__version__ = "1.0.0"
