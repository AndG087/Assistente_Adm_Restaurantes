"""Garante que categoria e fornecedor de um lançamento pertencem ao mesmo restaurante.

Sem esta checagem, alguém poderia associar à sua despesa o id de um fornecedor
de outro restaurante e, ao ver a despesa, descobrir o nome dele.
"""

from sqlalchemy.orm import Session

from app.services import categoria_service, fornecedor_service
from app.services.erros import ReferenciaInvalidaError


def validar(
    db: Session,
    restaurante_id: int,
    categoria_id: int | None,
    fornecedor_id: int | None,
    categoria_atual: int | None = None,
    fornecedor_atual: int | None = None,
) -> None:
    """Inativos só são aceitos se já estavam no lançamento (edição sem trocar a referência)."""
    if categoria_id is not None:
        categoria = categoria_service.obter(db, restaurante_id, categoria_id)
        if categoria is None:
            raise ReferenciaInvalidaError("Categoria não encontrada.")
        if not categoria.ativo and categoria_id != categoria_atual:
            raise ReferenciaInvalidaError("A categoria selecionada está inativa.")

    if fornecedor_id is not None:
        fornecedor = fornecedor_service.obter(db, restaurante_id, fornecedor_id)
        if fornecedor is None:
            raise ReferenciaInvalidaError("Fornecedor não encontrado.")
        if not fornecedor.ativo and fornecedor_id != fornecedor_atual:
            raise ReferenciaInvalidaError("O fornecedor selecionado está inativo.")
