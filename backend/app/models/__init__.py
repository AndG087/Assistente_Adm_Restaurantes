"""Modelos de persistência.

Importe aqui cada modelo novo para que o Alembic o encontre ao gerar migrações.
"""

from app.models.restaurante import MembroRestaurante, PapelMembro, Restaurante
from app.models.sessao import Sessao
from app.models.usuario import Usuario

__all__ = ["MembroRestaurante", "PapelMembro", "Restaurante", "Sessao", "Usuario"]
