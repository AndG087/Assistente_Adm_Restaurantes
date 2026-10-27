"""Cadastro, login e sessões de usuário."""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.seguranca import HASH_FICTICIO, gerar_hash_senha, gerar_token_sessao, hash_token, verificar_senha
from app.core.tempo import agora_utc
from app.models import Sessao, Usuario


class EmailJaCadastradoError(Exception):
    pass


def registrar_usuario(db: Session, nome: str, email: str, senha: str) -> Usuario:
    usuario = Usuario(nome=nome, email=email, senha_hash=gerar_hash_senha(senha))
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # A restrição UNIQUE do banco é quem garante e-mail único, mesmo com cadastros simultâneos.
        db.rollback()
        raise EmailJaCadastradoError from None
    return usuario


def autenticar(db: Session, email: str, senha: str) -> Usuario | None:
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        # Gasta o mesmo tempo de uma verificação real, para não revelar quais e-mails existem.
        verificar_senha(senha, HASH_FICTICIO)
        return None
    if not verificar_senha(senha, usuario.senha_hash) or not usuario.ativo:
        return None
    return usuario


def criar_sessao(db: Session, usuario: Usuario) -> str:
    """Cria a sessão e devolve o token puro, que só existe no cookie do navegador."""
    agora = agora_utc()
    token = gerar_token_sessao()
    db.add(
        Sessao(
            usuario_id=usuario.id,
            token_hash=hash_token(token),
            criada_em=agora,
            expira_em=agora + timedelta(hours=get_settings().sessao_duracao_horas),
        )
    )
    # Aproveita para remover sessões vencidas desse usuário.
    db.execute(delete(Sessao).where(Sessao.usuario_id == usuario.id, Sessao.expira_em <= agora))
    db.commit()
    return token


def usuario_da_sessao(db: Session, token: str) -> Usuario | None:
    sessao = db.scalar(
        select(Sessao).where(Sessao.token_hash == hash_token(token), Sessao.expira_em > agora_utc())
    )
    if sessao is None or not sessao.usuario.ativo:
        return None
    return sessao.usuario


def encerrar_sessao(db: Session, token: str) -> None:
    db.execute(delete(Sessao).where(Sessao.token_hash == hash_token(token)))
    db.commit()
