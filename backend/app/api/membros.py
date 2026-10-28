from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante
from app.models import MembroRestaurante, PapelMembro
from app.schemas.validadores import normalizar_email
from app.services import membro_service
from app.services.erros import OperacaoNaoPermitidaError, ReferenciaInvalidaError, RegistroDuplicadoError

router = APIRouter(prefix="/restaurantes/{restaurante_id}/membros", tags=["Equipe"])

IdUsuario = Annotated[int, Path(gt=0)]


class NovoMembro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    papel: PapelMembro = PapelMembro.MEMBRO

    @field_validator("email")
    @classmethod
    def _email(cls, valor: str) -> str:
        email = normalizar_email(valor)
        if email is None:
            raise ValueError("Informe o e-mail.")
        return email


class AlteracaoPapel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    papel: PapelMembro


class MembroResponse(BaseModel):
    usuario_id: int
    nome: str
    email: str
    papel: PapelMembro
    voce: bool


def _resposta(membro: MembroRestaurante, usuario_atual_id: int) -> MembroResponse:
    return MembroResponse(
        usuario_id=membro.usuario_id,
        nome=membro.usuario.nome,
        email=membro.usuario.email,
        papel=membro.papel,
        voce=membro.usuario_id == usuario_atual_id,
    )


def _exigir_proprietario(vinculo: MembroRestaurante) -> None:
    # 403 (e não 404): quem pede já é membro e sabe que o restaurante existe.
    if vinculo.papel != PapelMembro.PROPRIETARIO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Apenas proprietários podem gerenciar a equipe.")


def _obter_ou_404(db: DbSession, vinculo: MembroRestaurante, usuario_id: int) -> MembroRestaurante:
    membro = membro_service.obter(db, vinculo.restaurante_id, usuario_id)
    if membro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada na equipe.")
    return membro


@router.get("", response_model=list[MembroResponse])
def listar(db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual) -> list[MembroResponse]:
    return [_resposta(m, usuario.id) for m in membro_service.listar(db, vinculo.restaurante_id)]


@router.post("", response_model=MembroResponse, status_code=status.HTTP_201_CREATED)
def adicionar(dados: NovoMembro, db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual) -> MembroResponse:
    _exigir_proprietario(vinculo)
    try:
        membro = membro_service.adicionar(db, vinculo.restaurante_id, dados.email, dados.papel)
    except ReferenciaInvalidaError as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erro)) from None
    except RegistroDuplicadoError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None
    return _resposta(membro, usuario.id)


@router.put("/{usuario_id}", response_model=MembroResponse)
def alterar_papel(
    dados: AlteracaoPapel,
    db: DbSession,
    vinculo: VinculoRestaurante,
    usuario: UsuarioAtual,
    usuario_id: IdUsuario,
) -> MembroResponse:
    _exigir_proprietario(vinculo)
    membro = _obter_ou_404(db, vinculo, usuario_id)
    try:
        membro = membro_service.alterar_papel(db, membro, dados.papel)
    except OperacaoNaoPermitidaError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None
    return _resposta(membro, usuario.id)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual, usuario_id: IdUsuario) -> None:
    # Qualquer pessoa pode sair; remover outra pessoa é só para proprietários.
    if usuario_id != usuario.id:
        _exigir_proprietario(vinculo)
    membro = _obter_ou_404(db, vinculo, usuario_id)
    try:
        membro_service.remover(db, membro)
    except OperacaoNaoPermitidaError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from None
