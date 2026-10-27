"""Dependências compartilhadas pelas rotas: usuário logado e acesso a um restaurante."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import MembroRestaurante, Usuario
from app.services import auth_service, restaurante_service

NOME_COOKIE_SESSAO = "sessao"

DbSession = Annotated[Session, Depends(get_db)]


def obter_usuario_atual(
    db: DbSession,
    sessao: Annotated[str | None, Cookie(alias=NOME_COOKIE_SESSAO, max_length=128)] = None,
) -> Usuario:
    usuario = auth_service.usuario_da_sessao(db, sessao) if sessao else None
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar.")
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(obter_usuario_atual)]


def obter_vinculo_restaurante(
    db: DbSession,
    usuario: UsuarioAtual,
    restaurante_id: Annotated[int, Path(gt=0)],
) -> MembroRestaurante:
    """Use em toda rota /restaurantes/{restaurante_id}/...

    Responde 404 (e não 403) quando o usuário não é membro, para não revelar
    se um restaurante de outra pessoa existe.
    """
    vinculo = restaurante_service.obter_vinculo(db, usuario, restaurante_id)
    if vinculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Restaurante não encontrado.")
    return vinculo


VinculoRestaurante = Annotated[MembroRestaurante, Depends(obter_vinculo_restaurante)]
