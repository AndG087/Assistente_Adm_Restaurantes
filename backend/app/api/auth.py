from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status

from app.api.deps import NOME_COOKIE_SESSAO, DbSession, UsuarioAtual
from app.core.config import get_settings
from app.core.limite_tentativas import LimiteTentativas
from app.models import Usuario
from app.schemas.auth import LoginRequest, RegistroRequest, UsuarioResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])

_settings = get_settings()
# Falhas de login por e-mail (protege cada conta) e por IP (quem testa vários e-mails tem limite maior).
falhas_por_email = LimiteTentativas(_settings.login_maximo_falhas, _settings.login_janela_minutos * 60)
falhas_por_ip = LimiteTentativas(_settings.login_maximo_falhas * 4, _settings.login_janela_minutos * 60)
cadastros_por_ip = LimiteTentativas(_settings.registro_maximo_por_ip, _settings.registro_janela_minutos * 60)


def _ip(requisicao: Request) -> str:
    return requisicao.client.host if requisicao.client else "desconhecido"


def _barrar_se_bloqueado(segundos: int) -> None:
    if segundos:
        minutos = (segundos + 59) // 60
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas. Aguarde {minutos} minuto(s) e tente de novo.",
            headers={"Retry-After": str(segundos)},
        )


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
def registrar(dados: RegistroRequest, db: DbSession, resposta: Response, requisicao: Request) -> UsuarioResponse:
    ip = _ip(requisicao)
    _barrar_se_bloqueado(cadastros_por_ip.segundos_bloqueado(ip))
    cadastros_por_ip.registrar(ip)
    try:
        usuario = auth_service.registrar_usuario(db, dados.nome, dados.email, dados.senha)
    except auth_service.EmailJaCadastradoError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Já existe uma conta com este e-mail.") from None
    return _iniciar_sessao(db, resposta, usuario)


@router.post("/login", response_model=UsuarioResponse)
def login(dados: LoginRequest, db: DbSession, resposta: Response, requisicao: Request) -> UsuarioResponse:
    ip = _ip(requisicao)
    # Checado antes da senha: bloqueado, nem a senha certa entra (senão o bloqueio não protegeria nada).
    _barrar_se_bloqueado(max(falhas_por_email.segundos_bloqueado(dados.email), falhas_por_ip.segundos_bloqueado(ip)))
    usuario = auth_service.autenticar(db, dados.email, dados.senha)
    if usuario is None:
        falhas_por_email.registrar(dados.email)
        falhas_por_ip.registrar(ip)
        # Mesma mensagem para e-mail inexistente e senha errada.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    falhas_por_email.limpar(dados.email)
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
