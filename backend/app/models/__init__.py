"""Modelos de persistência.

Importe aqui cada modelo novo para que o Alembic o encontre ao gerar migrações.
"""

from app.models.categoria import CategoriaFinanceira
from app.models.conta_pagar import ContaPagar
from app.models.despesa import Despesa
from app.models.documento import Documento, StatusDocumento
from app.models.fornecedor import Fornecedor
from app.models.restaurante import MembroRestaurante, PapelMembro, Restaurante
from app.models.sessao import Sessao
from app.models.usuario import Usuario

__all__ = [
    "CategoriaFinanceira",
    "ContaPagar",
    "Despesa",
    "Documento",
    "Fornecedor",
    "MembroRestaurante",
    "PapelMembro",
    "Restaurante",
    "Sessao",
    "StatusDocumento",
    "Usuario",
]
