from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from app.api.deps import DbSession, UsuarioAtual, VinculoRestaurante, ou_404
from app.core.config import get_settings
from app.core.limite_tentativas import LimiteTentativas
from app.models import MembroRestaurante, PapelMembro
from app.schemas.membro import AlteracaoPapel, MembroResponse, NovoMembro
from app.services import membro_service
from app.services.erros import ReferenciaInvalidaError

router = APIRouter(prefix="/restaurantes/{restaurante_id}/membros", tags=["Equipe"])

IdUsuario = Annotated[int, Path(gt=0)]

# A resposta "não existe conta com este e-mail" permitiria testar uma lista de e-mails;
# com poucas tentativas erradas por hora, isso deixa de ser viável.
_settings = get_settings()
emails_nao_encontrados = LimiteTentativas(_settings.equipe_maximo_emails_invalidos, 3600)


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
    return ou_404(membro_service.obter(db, vinculo.restaurante_id, usuario_id), "Pessoa não encontrada na equipe.")


@router.get("", response_model=list[MembroResponse])
def listar(db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual) -> list[MembroResponse]:
    return [_resposta(m, usuario.id) for m in membro_service.listar(db, vinculo.restaurante_id)]


@router.post("", response_model=MembroResponse, status_code=status.HTTP_201_CREATED)
def adicionar(dados: NovoMembro, db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual) -> MembroResponse:
    _exigir_proprietario(vinculo)
    chave = str(usuario.id)
    segundos = emails_nao_encontrados.segundos_bloqueado(chave)
    if segundos:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitos e-mails não encontrados. Confira os endereços e tente mais tarde.",
            headers={"Retry-After": str(segundos)},
        )
    try:
        membro = membro_service.adicionar(db, vinculo.restaurante_id, dados.email, dados.papel)
    except ReferenciaInvalidaError:
        emails_nao_encontrados.registrar(chave)
        raise  # vira 422 no tratador global (app/main.py)
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
    membro = membro_service.alterar_papel(db, membro, dados.papel)
    return _resposta(membro, usuario.id)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(db: DbSession, vinculo: VinculoRestaurante, usuario: UsuarioAtual, usuario_id: IdUsuario) -> None:
    # Qualquer pessoa pode sair; remover outra pessoa é só para proprietários.
    if usuario_id != usuario.id:
        _exigir_proprietario(vinculo)
    membro = _obter_ou_404(db, vinculo, usuario_id)
    membro_service.remover(db, membro)
