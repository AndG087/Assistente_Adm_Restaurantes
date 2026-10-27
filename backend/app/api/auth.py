from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.api.deps import NOME_COOKIE_SESSAO, DbSession, UsuarioAtual
from app.core.config import get_settings
from app.models import Usuario
from app.schemas.auth import LoginRequest, RegistroRequest, UsuarioResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _gravar_cookie(resposta: Response, token: str) -> None:
    settings = get_settings()
    resposta.set_cookie(
        NOME_COOKIE_SESSAO,
        token,
        max_age=settings.sessao_duracao_horas * 3600,
        httponly=True,  # o JavaScript da página não consegue ler o token
        samesite="lax",  # o navegador não envia o cookie em POSTs vindos de outros sites
        secure=settings.cookie_seguro,
        path="/api",
    )


def _iniciar_sessao(db: DbSession, resposta: Response, usuario: Usuario) -> UsuarioResponse:
    _gravar_cookie(resposta, auth_service.criar_sessao(db, usuario))
    return UsuarioResponse.model_validate(usuario)


@router.post("/registrar", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar(dados: RegistroRequest, db: DbSession, resposta: Response) -> UsuarioResponse:
    try:
        usuario = auth_service.registrar_usuario(db, dados.nome, dados.email, dados.senha)
    except auth_service.EmailJaCadastradoError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Já existe uma conta com este e-mail.") from None
    return _iniciar_sessao(db, resposta, usuario)


@router.post("/login", response_model=UsuarioResponse)
def login(dados: LoginRequest, db: DbSession, resposta: Response) -> UsuarioResponse:
    usuario = auth_service.autenticar(db, dados.email, dados.senha)
    if usuario is None:
        # Mesma mensagem para e-mail inexistente e senha errada.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    return _iniciar_sessao(db, resposta, usuario)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: DbSession,
    resposta: Response,
    sessao: Annotated[str | None, Cookie(alias=NOME_COOKIE_SESSAO, max_length=128)] = None,
) -> None:
    if sessao:
        auth_service.encerrar_sessao(db, sessao)
    resposta.delete_cookie(NOME_COOKIE_SESSAO, path="/api")


@router.get("/eu", response_model=UsuarioResponse)
def eu(usuario: UsuarioAtual) -> Usuario:
    return usuario
